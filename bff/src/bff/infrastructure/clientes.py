from __future__ import annotations
import uuid
from typing import Any, Optional

import httpx

from bff.infrastructure.config import settings


class ClienteMarketplace:
    def __init__(self):
        self._base_url = settings.MARKETPLACE_URL

    async def obtener_trabajo(self, trabajo_id: uuid.UUID) -> Optional[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get(f"/trabajos/{trabajo_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def solicitar_trabajo(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post("/trabajos/solicitar", json=payload)
            resp.raise_for_status()
            return resp.json()


class ClienteVerificacion:
    def __init__(self):
        self._base_url = settings.VERIFICACION_URL

    async def obtener_estado_proveedor(
        self, proveedor_id: uuid.UUID
    ) -> Optional[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get(f"/proveedores/{proveedor_id}/estado")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def iniciar_verificacion(self, proveedor_id: uuid.UUID) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post(
                "/verificaciones", json={"proveedor_id": str(proveedor_id)}
            )
            resp.raise_for_status()
            return resp.json()


class ClienteCotizacion:
    def __init__(self):
        self._base_url = settings.COTIZACION_URL

    async def obtener_cotizacion(
        self, cotizacion_id: uuid.UUID
    ) -> Optional[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get(f"/cotizaciones/{cotizacion_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def solicitar_cotizacion(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.post("/cotizaciones/solicitar", json=payload)
            resp.raise_for_status()
            return resp.json()


class ClienteNotificaciones:

    def __init__(self):
        self._base_url = settings.NOTIFICACIONES_URL

    async def obtener_notificacion(
        self, notificacion_id: uuid.UUID
    ) -> Optional[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            resp = await client.get(f"/notificaciones/{notificacion_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()


cliente_marketplace = ClienteMarketplace()
cliente_verificacion = ClienteVerificacion()
cliente_cotizacion = ClienteCotizacion()
cliente_notificaciones = ClienteNotificaciones()
