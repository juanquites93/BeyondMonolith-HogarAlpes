from __future__ import annotations
import uuid

import strawberry

from bff.infrastructure.clientes import cliente_cotizacion, cliente_marketplace, cliente_verificacion
from bff.interfaces.graphql.esquemas import (
    Cotizacion,
    Proveedor,
    SolicitarCotizacionInput,
    SolicitarTrabajoInput,
    Trabajo,
)


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Solicita un nuevo trabajo en el marketplace")
    async def solicitar_trabajo(self, input: SolicitarTrabajoInput) -> Trabajo:
        payload = {
            "cliente_id": str(input.cliente_id),
            "ubicacion": {
                "direccion": input.ubicacion.direccion,
                "ciudad": input.ubicacion.ciudad,
                "pais": input.ubicacion.pais,
                "codigo_postal": input.ubicacion.codigo_postal,
            },
            "alcance": {
                "descripcion": input.alcance.descripcion,
                "categoria": input.alcance.categoria,
                "notas": input.alcance.notas,
            },
        }
        data = await cliente_marketplace.solicitar_trabajo(payload)
        return Trabajo(
            trabajo_id=data["trabajo_id"],
            cliente_id=data["cliente_id"],
            estado=data["estado"],
            proveedor_seleccionado_id=data.get("proveedor_seleccionado_id"),
        )

    @strawberry.mutation(description="Inicia el proceso de verificación de un proveedor")
    async def iniciar_verificacion(self, proveedor_id: uuid.UUID) -> Proveedor:
        data = await cliente_verificacion.iniciar_verificacion(proveedor_id)
        return Proveedor(
            proveedor_id=data["proveedor_id"],
            estado_verificacion=data["estado_verificacion"],
            estado_acreditacion=data["estado_acreditacion"],
        )

    @strawberry.mutation(description="Solicita una nueva cotización para un trabajo")
    async def solicitar_cotizacion(self, input: SolicitarCotizacionInput) -> Cotizacion:
        payload = {
            "trabajo_id": str(input.trabajo_id),
            "proveedor_id": str(input.proveedor_id),
            "monto": input.monto,
            "descripcion": input.descripcion,
            "moneda": input.moneda,
        }
        data = await cliente_cotizacion.solicitar_cotizacion(payload)
        return Cotizacion(
            cotizacion_id=data["cotizacion_id"],
            trabajo_id=data["trabajo_id"],
            proveedor_id=data.get("proveedor_id"),
            monto=data.get("monto"),
            moneda=data["moneda"],
            descripcion=data["descripcion"],
            estado=data["estado"],
        )
