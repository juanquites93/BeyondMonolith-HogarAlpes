from __future__ import annotations
import uuid
from typing import Optional

import strawberry

from bff.infrastructure.clientes import (
    cliente_cotizacion,
    cliente_marketplace,
    cliente_notificaciones,
    cliente_verificacion,
)
from bff.interfaces.graphql.esquemas import Cotizacion, Notificacion, Proveedor, Trabajo


@strawberry.type
class Query:
    @strawberry.field(description="Consulta un trabajo del marketplace por su id")
    async def trabajo(self, trabajo_id: uuid.UUID) -> Optional[Trabajo]:
        data = await cliente_marketplace.obtener_trabajo(trabajo_id)
        if data is None:
            return None
        return Trabajo(
            trabajo_id=data["trabajo_id"],
            cliente_id=data["cliente_id"],
            estado=data["estado"],
            proveedor_seleccionado_id=data.get("proveedor_seleccionado_id"),
        )

    @strawberry.field(
        description="Consulta el estado de verificación/acreditación de un proveedor"
    )
    async def estado_proveedor(self, proveedor_id: uuid.UUID) -> Optional[Proveedor]:
        data = await cliente_verificacion.obtener_estado_proveedor(proveedor_id)
        if data is None:
            return None
        return Proveedor(
            proveedor_id=data["proveedor_id"],
            estado_verificacion=data["estado_verificacion"],
            estado_acreditacion=data["estado_acreditacion"],
        )

    @strawberry.field(description="Consulta una cotización por su id")
    async def cotizacion(self, cotizacion_id: uuid.UUID) -> Optional[Cotizacion]:
        data = await cliente_cotizacion.obtener_cotizacion(cotizacion_id)
        if data is None:
            return None
        return Cotizacion(
            cotizacion_id=data["cotizacion_id"],
            trabajo_id=data["trabajo_id"],
            proveedor_id=data.get("proveedor_id"),
            monto=data.get("monto"),
            moneda=data["moneda"],
            descripcion=data["descripcion"],
            estado=data["estado"],
        )

    @strawberry.field(description="Consulta una notificación por su id")
    async def notificacion(self, notificacion_id: uuid.UUID) -> Optional[Notificacion]:
        data = await cliente_notificaciones.obtener_notificacion(notificacion_id)
        if data is None:
            return None
        return Notificacion(
            notificacion_id=data["notificacion_id"],
            destinatario_id=data["destinatario_id"],
            tipo=data["tipo"],
            canal=data["canal"],
            estado=data["estado"],
        )
