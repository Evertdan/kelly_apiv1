# app/schemas/chat.py
# -*- coding: utf-8 -*-

"""
Schemas Pydantic para las peticiones y respuestas del endpoint de chat.
"""

from pydantic import BaseModel, Field, HttpUrl # Importar HttpUrl por si se usa en SourceInfo
from typing import List, Optional, Dict, Any

# --- Schema para la Petición ---

class ChatRequest(BaseModel):
    """Modelo para la petición entrante al endpoint /chat."""
    message: str = Field(
        ..., # Campo obligatorio
        min_length=1,
        max_length=5000, # Límite máximo razonable
        description="Mensaje o pregunta enviada por el usuario."
    )
    session_id: str = Field(
        ..., # Campo obligatorio
        description="Identificador único para la sesión de chat o el usuario."
    )
    # Opcional: Podrías añadir aquí más campos si el cliente necesita enviar contexto adicional
    # context_override: Optional[Dict[str, Any]] = Field(None, description="Contexto adicional proporcionado por el cliente.")

    # Configuración del modelo Pydantic (ejemplo para documentación)
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "¿Cómo puedo configurar mi correo en Outlook?",
                    "session_id": "user123-abc"
                }
            ]
        }
    }


# --- Schemas para la Respuesta ---

class SourceInfo(BaseModel):
    """Información detallada sobre una fuente de conocimiento consultada."""
    source_id: str = Field(
        ...,
        description="Identificador único de la fuente recuperada (ej. el faq_id original o el UUID usado en Qdrant)."
    )
    score: Optional[float] = Field(
        None, # La puntuación puede no estar siempre disponible
        description="Puntuación de similitud/relevancia devuelta por la base de datos vectorial (ej. Qdrant). Más alto es más relevante."
    )
    # Opcional: Añadir otros metadatos del payload de Qdrant si quieres devolverlos
    # question: Optional[str] = Field(None, description="Pregunta original de la fuente (si aplica).")
    # product: Optional[str] = Field(None, description="Producto asociado a la fuente.")
    # categoria: Optional[str] = Field(None, description="Categoría asociada a la fuente.")
    # source_url: Optional[HttpUrl] = Field(None, description="URL a la fuente original si aplica.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source_id": "A-20-01-09-03-01_q0", # Usando el faq_id original
                    "score": 0.895123
                },
                {
                    "source_id": "priority_context", # Ejemplo si viene de contexto prioritario
                    "score": 1.0
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Modelo para la respuesta del endpoint /chat."""
    answer: str = Field(
        ...,
        description="La respuesta generada por el asistente KellyBot."
    )
    sources: List[SourceInfo] = Field(
        default_factory=list, # Devuelve lista vacía si no hay fuentes
        description="Lista de fuentes de información consultadas para generar la respuesta."
    )
    session_id: str = Field(
        ...,
        description="Identificador único de la sesión de chat (el mismo que se recibió en la petición)."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "Para configurar tu correo, necesitas seguir estos pasos...",
                    "sources": [
                        {"source_id": "CONFIG-EMAIL-01_q0", "score": 0.9123},
                        {"source_id": "GENERAL-SETUP-05_q2", "score": 0.8511}
                    ],
                    "session_id": "user123-abc"
                }
            ]
        }
    }