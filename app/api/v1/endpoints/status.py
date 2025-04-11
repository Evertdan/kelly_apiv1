# app/api/v1/endpoints/status.py
# -*- coding: utf-8 -*-

"""
Endpoints para verificar el estado y la salud de la API KellyBot.
"""

import logging # Añadir import de logging
from fastapi import APIRouter

# Importar el schema de respuesta
# Asume que app/schemas/status.py existe y define StatusResponse correctamente
try:
    from app.schemas.status import StatusResponse
    SCHEMA_AVAILABLE = True
except ImportError:
    print("[ERROR status.py] No se pudo importar 'StatusResponse'. Usando dummy.")
    # Fallback si el schema no existe aún
    class StatusResponse: # type: ignore
         def __init__(self, status: str = "error", message: str = "Schema no encontrado"):
              self.status = status
              self.message = message
    SCHEMA_AVAILABLE = False

# Crear un router específico para estos endpoints
router = APIRouter()
logger = logging.getLogger(__name__) # Crear logger para este módulo


@router.get(
    "/", # Montado en la raíz de la API (definido en main.py)
    response_model=StatusResponse if SCHEMA_AVAILABLE else None, # Usar schema si está disponible
    summary="Verificar Estado General de la API",
    description="Endpoint simple para verificar que la API está en línea y respondiendo.",
    tags=["Status"] # Agrupado bajo 'Status' en la documentación
)
async def get_root_status():
    """Devuelve un estado 'ok' si la API está operativa."""
    logger.info("Request recibido a endpoint raíz GET /")
    # Crear instancia del schema si está disponible, si no, un dict simple
    if SCHEMA_AVAILABLE:
         return StatusResponse(status="ok", message="KellyBot API (v1) está operativa.")
    else:
         return {"status": "ok", "message": "KellyBot API (v1) está operativa."}


@router.get(
    "/health", # Ruta específica para health check
    response_model=StatusResponse if SCHEMA_AVAILABLE else None, # Usar schema si está disponible
    summary="Verificar Salud de la API (para Monitoreo)",
    description="Endpoint de verificación de salud, usualmente usado por sistemas de monitoreo.",
    tags=["Status"],
    include_in_schema=False # Ocultar de la documentación pública
)
async def get_health_status():
    """
    Devuelve un estado 'ok' simple indicando que la API responde.
    """
    logger.info("Request recibido a endpoint de salud GET /health")
    # En el futuro, aquí podrían añadirse chequeos de conexión a DBs, etc.
    if SCHEMA_AVAILABLE:
        return StatusResponse(status="ok", message="API healthy.")
    else:
         return {"status": "ok", "message": "API healthy."}