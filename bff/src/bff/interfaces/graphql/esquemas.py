from __future__ import annotations
import uuid
from typing import Optional

import strawberry


@strawberry.type
class Trabajo:
    trabajo_id: uuid.UUID
    cliente_id: uuid.UUID
    estado: str
    proveedor_seleccionado_id: Optional[uuid.UUID] = None


@strawberry.type
class Proveedor:
    proveedor_id: uuid.UUID
    estado_verificacion: str
    estado_acreditacion: str


@strawberry.type
class Cotizacion:
    cotizacion_id: uuid.UUID
    trabajo_id: uuid.UUID
    proveedor_id: Optional[uuid.UUID]
    monto: Optional[float]
    moneda: str
    descripcion: str
    estado: str


@strawberry.type
class Notificacion:
    notificacion_id: uuid.UUID
    destinatario_id: str
    tipo: str
    canal: str
    estado: str


@strawberry.input
class UbicacionInput:
    direccion: str
    ciudad: str
    pais: str
    codigo_postal: Optional[str] = None


@strawberry.input
class AlcanceInput:
    descripcion: str
    categoria: str
    notas: Optional[str] = None


@strawberry.input
class SolicitarTrabajoInput:
    cliente_id: uuid.UUID
    ubicacion: UbicacionInput
    alcance: AlcanceInput


@strawberry.input
class SolicitarCotizacionInput:
    trabajo_id: uuid.UUID
    proveedor_id: uuid.UUID
    monto: float
    descripcion: str
    moneda: str = "COP"
