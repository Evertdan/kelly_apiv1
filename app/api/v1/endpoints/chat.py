# app/api/v1/endpoints/chat.py
# -*- coding: utf-8 -*-

"""
Endpoint para procesar mensajes de chat usando el pipeline RAG.
Versión final consistente con la estructura y servicios definidos.
"""

import logging
from typing import Dict, Any, List # Importar tipos necesarios

from fastapi import APIRouter, Depends, HTTPException, status

# Importar Schemas (Modelos Pydantic)
# Asegúrate de que estos archivos existan en app/schemas/
try:
    from app.schemas.chat import ChatRequest, ChatResponse, SourceInfo
    SCHEMAS_AVAILABLE = True
except ImportError:
     print("[ERROR chat.py] No se pudieron importar schemas ChatRequest/ChatResponse/SourceInfo.")
     # Definir dummies si faltan para que FastAPI pueda al menos cargar el archivo
     class ChatRequest: pass # type: ignore
     class ChatResponse: pass # type: ignore
     class SourceInfo: pass # type: ignore
     SCHEMAS_AVAILABLE = False

# Importar Dependencia de Seguridad
# Asegúrate de que app/api/deps.py exista y defina get_api_key
try:
    from app.api.deps import get_api_key
    DEPS_AVAILABLE = True
except ImportError:
     print("[ERROR chat.py] No se pudo importar dependencia 'get_api_key'. Seguridad desactivada.")
     async def get_api_key() -> str: return "dummy_key_deps_not_found" # Dummy
     DEPS_AVAILABLE = False

# Importar el Servicio RAG
# Asegúrate de que app/services/rag_pipeline.py exista y defina generate_response
try:
    from app.services import rag_pipeline # Importar el módulo
    RAG_SERVICE_AVAILABLE = True
except ImportError:
    print("[ERROR CRÍTICO chat.py] No se pudo importar el módulo 'app.services.rag_pipeline'. El endpoint /chat no funcionará.")
    RAG_SERVICE_AVAILABLE = False
    # No definir dummy aquí, fallará limpiamente si se llama


# Crear un router específico para este endpoint
router = APIRouter()

# Obtener logger
logger = logging.getLogger(__name__)


@router.post(
    "/chat", # La ruta relativa al prefijo /api/v1
    response_model=ChatResponse if SCHEMAS_AVAILABLE else None, # Usar schema si está disponible
    summary="Procesar un mensaje de chat",
    description="Recibe mensaje y session_id, ejecuta pipeline RAG y devuelve respuesta + fuentes.",
    tags=["Chat"] # Tag para documentación OpenAPI
)
async def handle_chat_message(
    request: ChatRequest, # Validación automática del cuerpo
    # Activar seguridad si está disponible
    api_key: str = Depends(get_api_key) if DEPS_AVAILABLE else "dummy_key_deps_off"
) -> ChatResponse: # El tipo de retorno debe coincidir con response_model
    """
    Maneja las peticiones POST a /api/v1/chat.
    """
    # Loguear recepción
    logger.info(f"Recibida petición para session_id: {request.session_id}")
    logger.debug(f"Mensaje recibido: {request.message}")

    # Verificar si el servicio RAG está disponible
    if not RAG_SERVICE_AVAILABLE or not hasattr(rag_pipeline, 'generate_response'):
         logger.critical(f"Intento de llamada a RAG para session {request.session_id} pero el servicio no está disponible.")
         raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Error interno del servidor: Servicio principal no disponible [RAG-IMP]."
         )

    try:
        # 1. Llamar al servicio RAG principal
        response_data = await rag_pipeline.generate_response(
            question=request.message,
            session_id=request.session_id
        )

        # 2. Validar respuesta del servicio (debe ser dict con 'answer')
        if not response_data or not isinstance(response_data, dict) or not response_data.get("answer"):
            logger.error(f"Servicio RAG devolvió respuesta inválida/vacía para session_id: {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El asistente no pudo generar una respuesta en este momento [RAG-RESP].",
            )

        # 3. Construir respuesta final usando schema Pydantic (si está disponible)
        formatted_sources = []
        raw_sources = response_data.get("sources", [])
        if isinstance(raw_sources, list) and SCHEMAS_AVAILABLE and SourceInfo is not Dict:
             for src in raw_sources:
                  if isinstance(src, dict):
                       try: formatted_sources.append(SourceInfo(**src)) # Validar/Convertir
                       except Exception as e_schema: logger.warning(f"Fuente incompatible con SourceInfo: {src}. Error: {e_schema}")
                  elif isinstance(src, SourceInfo): formatted_sources.append(src) # Ya es el tipo correcto
                  else: logger.warning(f"Fuente con tipo inesperado: {type(src)}")
        elif isinstance(raw_sources, list): # Si no hay schema, pasar la lista como viene
            formatted_sources = raw_sources

        # Crear la respuesta final
        # Si el schema ChatResponse no está disponible, no podemos validarla formalmente aquí,
        # pero devolvemos la estructura esperada como diccionario.
        # FastAPI intentará validarla al salir si response_model se definió.
        final_response_data = {
             "answer": response_data["answer"],
             "sources": formatted_sources,
             "session_id": request.session_id
        }

        if not SCHEMAS_AVAILABLE:
             # Si no tenemos el schema, devolvemos el diccionario directamente
             logger.warning("Devolviendo respuesta como Dict porque ChatResponse no se importó.")
             return final_response_data # type: ignore

        # Si tenemos el schema, lo usamos para validar/serializar
        final_response = ChatResponse(**final_response_data)
        logger.info(f"Respuesta generada exitosamente para session_id: {request.session_id}")
        return final_response

    except HTTPException:
         raise # Re-lanzar excepciones HTTP conocidas
    except Exception as e:
        logger.exception(f"Error inesperado procesando chat para session_id {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error interno al procesar tu mensaje.",
        )