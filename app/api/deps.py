# app/api/deps.py
# -*- coding: utf-8 -*-

"""
Dependencias reutilizables para los endpoints de FastAPI (Dependency Injection).

Define funciones que FastAPI puede 'inyectar' en las funciones de los endpoints
para realizar tareas comunes como autenticación, obtener configuración, etc.
"""

import logging
import os # Necesario para el fallback de settings
from typing import Optional

from fastapi import Depends, HTTPException, status # Asegurar status importado
from fastapi.security import APIKeyHeader

# Importar el esquema de seguridad y la función de verificación desde core.security
try:
    from app.core.security import API_KEY_HEADER, verify_api_key
    from app.core.config import settings # Importar también settings por si se necesita en otras deps
    SECURITY_AVAILABLE = True
except ImportError:
    print("[ERROR deps.py] No se pudo importar desde 'app.core.security' o 'app.core.config'.")
    # Definir dummies para que el archivo sea sintácticamente válido
    async def verify_api_key(token: Optional[str]) -> str:
        print("ADVERTENCIA: Usando verify_api_key dummy!")
        if token: return token
        raise HTTPException(status_code=500, detail="Security module not loaded")
    API_KEY_HEADER = None # type: ignore
    SECURITY_AVAILABLE = False
    # Dummy settings si config falla
    class DummySettings: pass
    settings = DummySettings() # type: ignore

logger = logging.getLogger(__name__)

# --- Dependencia para Validar API Key ---

async def get_api_key(
    # Usa el esquema definido en security.py para extraer el valor de la cabecera.
    # FastAPI inyecta el resultado de API_KEY_HEADER() aquí.
    # Si falta la cabecera (y auto_error=False), api_key_header será None.
    api_key_header: Optional[str] = Depends(API_KEY_HEADER)
) -> str:
    """
    Dependencia de FastAPI para verificar la API Key (Bearer Token).

    Utiliza la lógica definida en app.core.security.verify_api_key.
    Lanza HTTPException si la clave es inválida, falta, o si los módulos
    de seguridad/configuración no se cargaron correctamente.

    Returns:
        str: La clave API validada si la autenticación es exitosa.
    """
    if not SECURITY_AVAILABLE or API_KEY_HEADER is None:
         logger.critical("Intento de usar get_api_key pero security.py no cargó bien.")
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail="Error interno de configuración de seguridad [DEP01]"
         )

    # Delegar la validación real a la función en core.security
    # verify_api_key ya maneja las HTTPException 401 en caso de error de validación.
    try:
        # La función verify_api_key es async, así que usamos await
        validated_key = await verify_api_key(api_key_header)
        return validated_key
    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP que vienen de verify_api_key (ej. 401, 500)
        raise http_exc
    except Exception as e:
        # Capturar cualquier otro error inesperado durante la verificación
        logger.exception(f"Error inesperado en la dependencia get_api_key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno durante la validación de credenciales [DEP02]"
        )


# --- Aquí podrías añadir otras dependencias reutilizables ---

# Ejemplo: Dependencia para obtener la configuración (si no quieres importar 'settings' directamente)
# def get_settings() -> Settings:
#     """Devuelve la instancia global de configuración."""
#     # from app.core.config import settings # Mover import aquí
#     return settings

# Ejemplo: Dependencia para obtener el cliente Qdrant (requiere inicialización)
# async def get_qdrant_client() -> AsyncQdrantClient:
#     """Obtiene una instancia del cliente Qdrant."""
#     client = _get_qdrant_client() # Usando el helper cacheado de qdrant_service
#     if client is None:
#         raise HTTPException(status_code=503, detail="Servicio Qdrant no disponible")
#     return client