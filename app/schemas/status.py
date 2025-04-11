## app/schemas/status.py
# -*- coding: utf-8 -*-

"""
Schemas Pydantic para las respuestas de los endpoints de estado/salud.
"""

from pydantic import BaseModel, Field

class StatusResponse(BaseModel):
    """Modelo de respuesta estándar para endpoints de estado."""
    status: str = Field(
        default="ok",
        description="Indica el estado general del servicio ('ok' si funciona correctamente)."
    )
    message: str = Field(
        # Default genérico, el endpoint puede sobrescribirlo
        default="Servicio operativo.",
        description="Mensaje descriptivo del estado actual."
    )

    # Configuración opcional con ejemplo para documentación automática
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "ok",
                    "message": "KellyBot API está operativa." # Ejemplo usado en GET /
                },
                 {
                    "status": "ok",
                    "message": "API healthy." # Ejemplo usado en GET /health
                }
            ]
        }
    }