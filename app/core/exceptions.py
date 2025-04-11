# app/core/exceptions.py
# -*- coding: utf-8 -*-

"""
Excepciones personalizadas para la aplicación Kelly API.

Definir excepciones específicas permite un manejo de errores más granular
y respuestas HTTP más informativas en los endpoints.
"""

# --- Excepción Base ---

class KellyApiException(Exception):
    """Excepción base para errores específicos de la aplicación Kelly API."""
    def __init__(self, message: str = "Error interno en Kelly API", status_code: int = 500):
        self.message = message
        self.status_code = status_code # Código HTTP sugerido
        super().__init__(self.message)

# --- Excepciones de Servicios Específicos ---

class EmbeddingServiceError(KellyApiException):
    """Errores relacionados con la carga o generación de embeddings."""
    def __init__(self, message: str = "Error en el servicio de embeddings", status_code: int = 500):
        super().__init__(message, status_code)

class QdrantServiceError(KellyApiException):
    """Errores relacionados con la interacción con Qdrant."""
    def __init__(self, message: str = "Error en el servicio de Qdrant", status_code: int = 503): # 503 Service Unavailable
        super().__init__(message, status_code)

class LLMServiceError(KellyApiException):
    """Errores relacionados con la interacción con el LLM generativo."""
    def __init__(self, message: str = "Error en el servicio LLM", status_code: int = 502): # 502 Bad Gateway
        super().__init__(message, status_code)

class HistoryServiceError(KellyApiException):
    """Errores relacionados con el servicio de historial (MongoDB)."""
    def __init__(self, message: str = "Error en el servicio de historial", status_code: int = 500):
        super().__init__(message, status_code)

class PriorityContextError(KellyApiException):
    """Errores relacionados con el servicio de contexto prioritario (archivo JSON)."""
    def __init__(self, message: str = "Error en el servicio de contexto prioritario", status_code: int = 500):
        super().__init__(message, status_code)

# --- Otras Excepciones Potenciales ---

class ConfigurationError(KellyApiException):
     """Errores relacionados con la carga o validación de configuración."""
     def __init__(self, message: str = "Error de configuración", status_code: int = 500):
         super().__init__(message, status_code)

class RAGPipelineError(KellyApiException):
     """Errores específicos originados en la orquestación del pipeline RAG."""
     def __init__(self, message: str = "Error en el pipeline RAG", status_code: int = 500):
         super().__init__(message, status_code)


# Puedes añadir más excepciones específicas si es necesario,
# por ejemplo, heredar de QdrantServiceError para crear QdrantConnectionError, etc.