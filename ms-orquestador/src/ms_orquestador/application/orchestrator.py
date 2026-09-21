"""Orquestador centralizado de la Saga de asignación de proveedor."""

from __future__ import annotations
import logging
import time
import uuid
from datetime import datetime
from typing import Optional

import requests

from ms_orquestador.application.idempotency import IdempotencyService
from ms_orquestador.application.saga import Saga, SagaTransitionError
from ms_orquestador.application.saga_state import SagaState
from ms_orquestador.infrastructure.config import settings
from ms_orquestador.infrastructure.pulsar_producer import PulsarCommandProducer
from ms_orquestador.infrastructure.saga_repository import SagaRepository

logger = logging.getLogger(__name__)


class SagaOrchestrator:
    """Coordina el flujo de la Saga mediante comandos y eventos Pulsar.

    - Escucha eventos de los microservicios participantes.
    - Mantiene el estado de cada Saga en base de datos.
    - Publica comandos hacia los participantes.
    - Registra cada paso en el log de Saga.
    - Soporta reintentos configurables ante verificación pendiente.
    """

    def __init__(
        self,
        session_factory,
        producer: Optional[PulsarCommandProducer] = None,
        max_retries: Optional[int] = None,
        retry_delay_seconds: Optional[int] = None,
    ):
        self._session_factory = session_factory
        self._producer = producer or PulsarCommandProducer()
        self._max_retries = (
            max_retries if max_retries is not None else settings.SAGA_MAX_RETRIES
        )
        self._retry_delay_seconds = (
            retry_delay_seconds
            if retry_delay_seconds is not None
            else settings.SAGA_RETRY_DELAY_SECONDS
        )

    def handle_event(self, event: dict) -> None:
        """Punto de entrada para procesar un evento Pulsar."""
        message_type = event.get("messageType")
        message_id = event.get("messageId") or event.get("idempotencyKey")
        correlation_id = event.get("correlationId")
        saga_id = event.get("sagaId")
        producer = event.get("producer", "desconocido")
        payload = event.get("payload") or {}

        session = self._session_factory()
        try:
            idempotency = IdempotencyService(session)
            key = message_id or IdempotencyService.compute_key(
                message_type, payload, correlation_id
            )

            def _run():
                self._dispatch_event(session, event)

            idempotency.check_or_run(key, message_type or "desconocido", _run)
            session.commit()
        except Exception as exc:
            session.rollback()
            # Si el evento no trae sagaId, intentar resolverlo para el log.
            resolved_saga_id = saga_id
            if not resolved_saga_id:
                try:
                    resolved = self._resolve_saga(session, event)
                    if resolved:
                        resolved_saga_id = resolved.saga_id
                except Exception:
                    pass
            self._log_safe(
                session,
                saga_id=resolved_saga_id or "NO_SAGA",
                correlation_id=correlation_id,
                message_id=message_id,
                causation_id=event.get("causationId"),
                message_type=message_type or "desconocido",
                producer=producer,
                status="ERROR",
                payload=payload,
                error_message=str(exc),
            )
            session.commit()
            raise
        finally:
            session.close()

    def _dispatch_event(self, session, event: dict) -> None:
        message_type = event.get("messageType")

        if message_type == "ProveedorSeleccionado":
            self._handle_proveedor_seleccionado(session, event)
        elif message_type == "ProveedorAcreditado":
            self._handle_proveedor_acreditado(session, event)
        elif message_type == "VerificacionPendiente":
            self._handle_verificacion_pendiente(session, event)
        elif message_type == "CotizacionSolicitada":
            # En el sistema actual el MS de cotización emite CotizacionSolicitada.
            # Se considera equivalente a CotizacionGenerada para esta Saga.
            self._handle_cotizacion_generada(session, event)
        elif message_type == "NotificacionEnviada":
            self._handle_notificacion_enviada(session, event)
        elif message_type == "NotificacionFallida":
            self._handle_notificacion_fallida(session, event)
        elif message_type == "CotizacionCancelada":
            self._handle_cotizacion_cancelada(session, event)
        elif message_type == "AcreditacionRevocada":
            self._handle_acreditacion_revocada(session, event)
        elif message_type == "SeleccionProveedorRevertida":
            self._handle_seleccion_revertida(session, event)
        elif message_type == "ProveedorNoAcreditado":
            self._handle_proveedor_no_acreditado(session, event)
        else:
            logger.warning(
                "Evento no manejado por el orquestador",
                extra={"message_type": message_type},
            )

    def _handle_proveedor_seleccionado(self, session, event: dict) -> None:
        payload = event.get("payload") or {}
        correlation_id = event.get("correlationId") or str(uuid.uuid4())
        trabajo_id = payload.get("trabajo_id")
        proveedor_id = payload.get("proveedor_id")

        if not trabajo_id or not proveedor_id:
            raise ValueError("ProveedorSeleccionado requiere trabajo_id y proveedor_id")

        repo = SagaRepository(session)

        # Si ya existe una saga activa para este trabajo, no crear otra.
        existing = repo.get_by_trabajo(trabajo_id)
        if existing and existing.current_state not in {
            SagaState.COMPLETADA.value,
            SagaState.FALLIDA.value,
        }:
            logger.info(
                "Saga activa ya existe para el trabajo",
                extra={"trabajo_id": trabajo_id, "saga_id": existing.saga_id},
            )
            return

        saga = Saga()
        payload_context = {
            "trabajo_id": trabajo_id,
            "proveedor_id": proveedor_id,
            "cliente_id": payload.get("cliente_id"),
            "alcance": payload.get("alcance"),
            "ubicacion": payload.get("ubicacion"),
        }
        saga.start(
            correlation_id=correlation_id,
            trabajo_id=trabajo_id,
            proveedor_id=proveedor_id,
            payload_context=payload_context,
        )
        repo.save(saga)

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=correlation_id,
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="ProveedorSeleccionado",
            producer=event.get("producer", "marketplace-asignacion"),
            status="RECIBIDO",
            payload=payload,
        )

        self._enviar_iniciar_verificacion(session, saga, event)

    def _enviar_iniciar_verificacion(
        self, session, saga: Saga, causation_event: dict
    ) -> None:
        saga.start_verification()
        SagaRepository(session).save(saga)

        payload = {
            "proveedor_id": saga.proveedor_id,
            "trabajo_id": saga.trabajo_id,
        }
        message_id = self._producer.send_command(
            topic=settings.PULSAR_VERIFICACION_COMANDOS,
            message_type="ProveedorSeleccionadoParaValidacion",
            payload=payload,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            causation_id=causation_event.get("messageId"),
            idempotency_key=f"{saga.saga_id}-iniciar-verificacion-{saga.retry_count}",
        )

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            message_id=message_id,
            causation_id=causation_event.get("messageId"),
            message_type="ProveedorSeleccionadoParaValidacion",
            producer=settings.APP_NAME,
            status="ENVIADO",
            payload=payload,
        )

    def _handle_proveedor_acreditado(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para ProveedorAcreditado",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="ProveedorAcreditado",
            producer=event.get("producer", "verificacion-acreditacion"),
            status="RECIBIDO",
            payload=event.get("payload") or {},
        )

        payload = event.get("payload") or {}
        acreditacion_id = payload.get("acreditacion_id")
        if acreditacion_id:
            saga.payload_context["acreditacion_id"] = acreditacion_id

        saga.mark_provider_accredited()
        SagaRepository(session).save(saga)

        self._enviar_generar_cotizacion(session, saga, event)

    def _enviar_generar_cotizacion(
        self, session, saga: Saga, causation_event: dict
    ) -> None:
        saga.start_quotation()
        SagaRepository(session).save(saga)

        ctx = saga.payload_context or {}
        alcance = ctx.get("alcance") or {}
        payload = {
            "trabajo_id": saga.trabajo_id,
            "cliente_id": ctx.get("cliente_id"),
            "proveedor_id": saga.proveedor_id,
            "descripcion": alcance.get("descripcion", ""),
            "alcance": alcance,
            "ubicacion": ctx.get("ubicacion"),
        }
        message_id = self._producer.send_command(
            topic=settings.PULSAR_COTIZACION_COMANDOS,
            message_type="GenerarCotizacionCommand",
            payload=payload,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            causation_id=causation_event.get("messageId"),
            idempotency_key=f"{saga.saga_id}-generar-cotizacion",
        )

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            message_id=message_id,
            causation_id=causation_event.get("messageId"),
            message_type="GenerarCotizacionCommand",
            producer=settings.APP_NAME,
            status="ENVIADO",
            payload=payload,
        )

    def _handle_cotizacion_generada(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para CotizacionSolicitada",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="CotizacionSolicitada",
            producer=event.get("producer", "generador-cotizacion"),
            status="RECIBIDO",
            payload=event.get("payload") or {},
        )

        payload = event.get("payload") or {}
        cotizacion_id = payload.get("cotizacion_id")
        if cotizacion_id:
            saga.payload_context["cotizacion_id"] = cotizacion_id

        saga.mark_quotation_generated()
        SagaRepository(session).save(saga)

        self._enviar_notificacion(session, saga, event)

    def _enviar_notificacion(self, session, saga: Saga, causation_event: dict) -> None:
        saga.start_notification()
        SagaRepository(session).save(saga)

        ctx = saga.payload_context or {}
        alcance = ctx.get("alcance") or {}
        ubicacion = ctx.get("ubicacion") or {}
        payload = {
            "proveedor_id": saga.proveedor_id,
            "trabajo_id": saga.trabajo_id,
            "cliente_id": ctx.get("cliente_id"),
            "detalles_trabajo": {
                "descripcion": alcance.get("descripcion", ""),
                "categoria": alcance.get("categoria", ""),
                "ubicacion": {
                    "direccion": ubicacion.get("direccion", ""),
                    "ciudad": ubicacion.get("ciudad", ""),
                },
            },
        }
        message_id = self._producer.send_command(
            topic=settings.PULSAR_NOTIFICACION_COMANDOS,
            message_type="NotificarProveedorAsignadoCommand",
            payload=payload,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            causation_id=causation_event.get("messageId"),
            idempotency_key=f"{saga.saga_id}-notificar-proveedor",
        )

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            message_id=message_id,
            causation_id=causation_event.get("messageId"),
            message_type="NotificarProveedorAsignadoCommand",
            producer=settings.APP_NAME,
            status="ENVIADO",
            payload=payload,
        )

    def _handle_notificacion_enviada(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para NotificacionEnviada",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        payload = event.get("payload") or {}
        notificacion_id = payload.get("notificacion_id")
        if notificacion_id:
            saga.payload_context["notificacion_id"] = notificacion_id

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="NotificacionEnviada",
            producer=event.get("producer", "ms-notificaciones"),
            status="RECIBIDO",
            payload=event.get("payload") or {},
        )

        saga.mark_completed()
        SagaRepository(session).save(saga)

    def _handle_notificacion_fallida(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para NotificacionFallida",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        payload = event.get("payload") or {}
        motivo = payload.get("motivo", "notificación fallida")

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="NotificacionFallida",
            producer=event.get("producer", "ms-notificaciones"),
            status="RECIBIDO",
            payload=payload,
            error_message=motivo,
        )

        saga.start_compensation(motivo)
        SagaRepository(session).save(saga)
        self._enviar_cancelar_cotizacion(session, saga, event)

    def _enviar_cancelar_cotizacion(
        self, session, saga: Saga, causation_event: dict
    ) -> None:
        cotizacion_id = saga.payload_context.get("cotizacion_id")
        if not cotizacion_id:
            logger.error(
                "No hay cotizacion_id en el contexto de la saga; no se puede compensar",
                extra={"saga_id": saga.saga_id},
            )
            saga.mark_failed("No hay cotizacion_id para compensar")
            SagaRepository(session).save(saga)
            return

        payload = {"cotizacion_id": cotizacion_id}
        message_id = self._producer.send_command(
            topic=settings.PULSAR_COTIZACION_COMANDOS,
            message_type="CancelarCotizacionCommand",
            payload=payload,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            causation_id=causation_event.get("messageId"),
            idempotency_key=f"{saga.saga_id}-cancelar-cotizacion",
        )

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            message_id=message_id,
            causation_id=causation_event.get("messageId"),
            message_type="CancelarCotizacionCommand",
            producer=settings.APP_NAME,
            status="ENVIADO",
            payload=payload,
        )

    def _handle_cotizacion_cancelada(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para CotizacionCancelada",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="CotizacionCancelada",
            producer=event.get("producer", "generador-cotizacion"),
            status="RECIBIDO",
            payload=event.get("payload") or {},
        )

        saga.mark_step_compensated("CotizacionCancelada")
        SagaRepository(session).save(saga)
        self._enviar_revocar_acreditacion(session, saga, event)

    def _enviar_revocar_acreditacion(
        self, session, saga: Saga, causation_event: dict
    ) -> None:
        acreditacion_id = saga.payload_context.get("acreditacion_id")
        if not acreditacion_id:
            logger.warning(
                "No hay acreditacion_id en el contexto de la saga; se revoca por proveedor_id",
                extra={"saga_id": saga.saga_id},
            )

        payload = {
            "proveedor_id": saga.proveedor_id,
            "acreditacion_id": acreditacion_id,
        }
        message_id = self._producer.send_command(
            topic=settings.PULSAR_VERIFICACION_COMANDOS,
            message_type="RevocarAcreditacionProveedorCommand",
            payload=payload,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            causation_id=causation_event.get("messageId"),
            idempotency_key=f"{saga.saga_id}-revocar-acreditacion",
        )

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=saga.correlation_id,
            message_id=message_id,
            causation_id=causation_event.get("messageId"),
            message_type="RevocarAcreditacionProveedorCommand",
            producer=settings.APP_NAME,
            status="ENVIADO",
            payload=payload,
        )

    def _handle_acreditacion_revocada(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para AcreditacionRevocada",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="AcreditacionRevocada",
            producer=event.get("producer", "verificacion-acreditacion"),
            status="RECIBIDO",
            payload=event.get("payload") or {},
        )

        saga.mark_step_compensated("AcreditacionRevocada")
        SagaRepository(session).save(saga)
        self._enviar_revertir_seleccion(session, saga, event)

    def _enviar_revertir_seleccion(
        self, session, saga: Saga, causation_event: dict
    ) -> None:
        payload = {"trabajo_id": saga.trabajo_id}
        url = f"{settings.MARKETPLACE_URL}/trabajos/{saga.trabajo_id}/revertir-seleccion-proveedor"
        try:
            response = requests.post(
                url,
                json={"correlation_id": saga.correlation_id},
                timeout=10,
            )
            response.raise_for_status()
            self._log_safe(
                session,
                saga_id=saga.saga_id,
                correlation_id=saga.correlation_id,
                message_type="RevertirSeleccionProveedorCommand",
                producer=settings.APP_NAME,
                status="ENVIADO",
                payload=payload,
            )
            # Marketplace no publica evento Pulsar de compensación; consideramos la respuesta HTTP como confirmación.
            saga.mark_step_compensated("SeleccionProveedorRevertida")
            saga.mark_compensated()
            SagaRepository(session).save(saga)
        except Exception as exc:
            logger.exception("Error compensando selección de proveedor vía HTTP")
            self._log_safe(
                session,
                saga_id=saga.saga_id,
                correlation_id=saga.correlation_id,
                message_type="RevertirSeleccionProveedorCommand",
                producer=settings.APP_NAME,
                status="ERROR",
                payload=payload,
                error_message=str(exc),
            )
            raise

    def _handle_seleccion_revertida(self, session, event: dict) -> None:
        # Método de resguardo: si en el futuro marketplace publica el evento Pulsar,
        # este handler lo procesa y marca la saga como compensada.
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para SeleccionProveedorRevertida",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="SeleccionProveedorRevertida",
            producer=event.get("producer", "marketplace-asignacion"),
            status="RECIBIDO",
            payload=event.get("payload") or {},
        )

        saga.mark_step_compensated("SeleccionProveedorRevertida")
        if saga.current_state == SagaState.COMPENSANDO.value:
            saga.mark_compensated()
        SagaRepository(session).save(saga)

    def _handle_verificacion_pendiente(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para VerificacionPendiente",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        payload = event.get("payload") or {}
        motivo = payload.get("motivo", "verificación pendiente")

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="VerificacionPendiente",
            producer=event.get("producer", "verificacion-acreditacion"),
            status="RECIBIDO",
            payload=payload,
            error_message=motivo,
        )

        saga.mark_verification_pending(motivo)
        saga.wait_for_retry()
        SagaRepository(session).save(saga)

    def _handle_proveedor_no_acreditado(self, session, event: dict) -> None:
        saga = self._resolve_saga(session, event)
        if saga is None:
            logger.warning(
                "No se encontró saga para ProveedorNoAcreditado",
                extra={"saga_id": event.get("sagaId"), "payload": event.get("payload")},
            )
            return

        payload = event.get("payload") or {}
        motivo = payload.get("motivo", "proveedor no acreditado")

        self._log_safe(
            session,
            saga_id=saga.saga_id,
            correlation_id=event.get("correlationId"),
            message_id=event.get("messageId"),
            causation_id=event.get("causationId"),
            message_type="ProveedorNoAcreditado",
            producer=event.get("producer", "verificacion-acreditacion"),
            status="RECIBIDO",
            payload=payload,
            error_message=motivo,
        )

        saga.mark_failed(motivo)
        SagaRepository(session).save(saga)

    def _resolve_saga(self, session, event: dict) -> Optional[Saga]:
        saga_id = event.get("sagaId")
        repo = SagaRepository(session)
        if saga_id:
            saga = repo.get(saga_id)
            if saga:
                return saga

        payload = event.get("payload") or {}
        proveedor_id = payload.get("proveedor_id")
        trabajo_id = payload.get("trabajo_id")

        # Fallback: buscar por trabajo_id
        if trabajo_id:
            saga = repo.get_by_trabajo(trabajo_id)
            if saga:
                return saga

        # Fallback: buscar saga activa por proveedor_id (menos preciso)
        if proveedor_id:
            from ms_orquestador.infrastructure.orm import SagaORM

            orm = (
                session.query(SagaORM)
                .filter(
                    SagaORM.proveedor_id == proveedor_id,
                    SagaORM.current_state.notin_(
                        [SagaState.COMPLETADA.value, SagaState.FALLIDA.value]
                    ),
                )
                .order_by(SagaORM.created_at.desc())
                .first()
            )
            if orm:
                return repo._to_domain(orm)

        return None

    def process_retries(self) -> None:
        """Worker callable: reintenta sagas en ESPERANDO_REINTENTO."""
        session = self._session_factory()
        try:
            from ms_orquestador.infrastructure.orm import SagaORM

            rows = (
                session.query(SagaORM)
                .filter(SagaORM.current_state == SagaState.ESPERANDO_REINTENTO.value)
                .all()
            )
            repo = SagaRepository(session)
            for orm in rows:
                saga = repo._to_domain(orm)
                if saga.retry_count >= self._max_retries:
                    saga.mark_failed(
                        f"Se superaron los {self._max_retries} reintentos de verificación"
                    )
                    repo.save(saga)
                    self._log_safe(
                        session,
                        saga_id=saga.saga_id,
                        correlation_id=saga.correlation_id,
                        message_type="SagaRetry",
                        producer=settings.APP_NAME,
                        status="FALLIDA",
                        payload={"retry_count": saga.retry_count},
                        error_message=saga.last_error,
                    )
                    continue

                saga.retry()
                repo.save(saga)
                self._log_safe(
                    session,
                    saga_id=saga.saga_id,
                    correlation_id=saga.correlation_id,
                    message_type="SagaRetry",
                    producer=settings.APP_NAME,
                    status="REINTENTO",
                    payload={"retry_count": saga.retry_count},
                )
                self._producer.send_command(
                    topic=settings.PULSAR_VERIFICACION_COMANDOS,
                    message_type="ProveedorSeleccionadoParaValidacion",
                    payload={
                        "proveedor_id": saga.proveedor_id,
                        "trabajo_id": saga.trabajo_id,
                    },
                    saga_id=saga.saga_id,
                    correlation_id=saga.correlation_id,
                    causation_id=None,
                    idempotency_key=f"{saga.saga_id}-iniciar-verificacion-{saga.retry_count}",
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _log_safe(
        self,
        session,
        saga_id: str,
        message_type: str,
        producer: str,
        status: str,
        payload: dict,
        correlation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        try:
            repo = SagaRepository(session)
            repo.log_event(
                saga_id=saga_id,
                correlation_id=correlation_id,
                message_id=message_id,
                causation_id=causation_id,
                message_type=message_type,
                producer=producer,
                status=status,
                payload=payload,
                error_message=error_message,
            )
        except Exception as exc:
            logger.warning(
                "No se pudo registrar log de saga",
                extra={"saga_id": saga_id, "error": str(exc)},
            )

    def close(self) -> None:
        self._producer.close()
