from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificarProveedorAsignado:
    """Avisar al proveedor que le asignaron un trabajo nuevo."""

    proveedor_id: str
    trabajo_id: str
    cliente_id: str
    descripcion: str = ""
    categoria: str = ""
    direccion: str = ""
    ciudad: str = ""
    correlation_id: Optional[str] = None


@dataclass
class NotificarClienteProveedorAsignado:
    """Avisar al cliente que ya tiene proveedor asignado."""

    cliente_id: str
    trabajo_id: str
    proveedor_id: str
    correlation_id: Optional[str] = None
