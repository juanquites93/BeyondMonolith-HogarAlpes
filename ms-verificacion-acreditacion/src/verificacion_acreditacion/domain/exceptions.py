"""Excepciones de dominio."""


class VerificacionError(Exception):
    """Error base de verificación."""


class EstadoInvalidoError(VerificacionError):
    """Operación no permitida por el estado actual."""


class ProveedorNoVerificadoError(VerificacionError):
    """No se puede acreditar un proveedor sin verificación aprobada."""


class VerificacionYaResueltaError(VerificacionError):
    """La verificación ya fue aprobada o rechazada."""
