# app/core/security.py
# -*- coding: utf-8 -*-

"""
Módulo para funciones y esquemas de seguridad, como validación de API Keys.
"""

import secrets # Para comparación segura de claves
import logging
import os # Necesario para el fallback de settings
from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import APIKeyHeader # Esquema de seguridad para API Keys

# Importar la instancia de configuración para acceder a la clave API esperada
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError:
    # Fallback si config no existe aún (para que el archivo sea importable)
    print("[ERROR security.py] No se pudo importar 'settings'. La validación fallará si no hay variables de entorno.")
    class DummySettings:
        API_ACCESS_KEY: Optional[str] = os.environ.get("API_ACCESS_KEY") # Intentar leer de entorno
    settings = DummySettings() # type: ignore
    CONFIG_LOADED = False
except Exception as config_err: # Capturar otros errores como ValidationError
     print(f"[ERROR CRÍTICO security.py] Error al importar/validar settings: {config_err}. La validación fallará.")
     class DummySettings: API_ACCESS_KEY: Optional[str] = None
     settings = DummySettings() # type: ignore
     CONFIG_LOADED = False


logger = logging.getLogger(__name__)

# --- Esquema de Seguridad ---
# Busca la clave en la cabecera "Authorization".
# auto_error=False permite manejar el error nosotros mismos.
API_KEY_HEADER = APIKeyHeader(name="Authorization", auto_error=False)


# --- Función de Verificación (usada por la dependencia en deps.py) ---
async def verify_api_key(api_key_header: Optional[str]) -> str:
    """
    Verifica si la API Key proporcionada en la cabecera 'Authorization: Bearer <key>'
    es válida comparándola con la configurada en 'settings.API_ACCESS_KEY'.

    Args:
        api_key_header: El valor completo de la cabecera 'Authorization' recibido,
                        o None si la cabecera no se envió.

    Raises:
        HTTPException(500): Si la API Key no está configurada en el servidor.
        HTTPException(401): Si la cabecera falta, tiene formato incorrecto,
                           o la clave proporcionada no coincide.

    Returns:
        La clave API (el token) si es válida.
    """

    # 1. Validar configuración del servidor
    if not CONFIG_LOADED:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno crítico de configuración [SEC01].",
         )

    expected_api_key: Optional[str] = None
    # Usar getattr y hasattr para acceso seguro, especialmente si settings es Dummy
    api_key_setting = getattr(settings, 'API_ACCESS_KEY', None)
    if api_key_setting:
        if hasattr(api_key_setting, 'get_secret_value'): # Si es SecretStr
            expected_api_key = api_key_setting.get_secret_value()
        else: # Si es str (fallback)
            expected_api_key = str(api_key_setting)

    if not expected_api_key:
        logger.critical("CONFIGURACIÓN INCORRECTA: API_ACCESS_KEY no definida en el servidor.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno de configuración del servidor [SEC02].",
        )

    # 2. Validar cabecera recibida
    if not api_key_header:
        logger.warning("Acceso denegado: Falta cabecera 'Authorization'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta la cabecera 'Authorization'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Validar formato "Bearer <token>"
    parts = api_key_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Acceso denegado: Formato inválido de 'Authorization'.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de cabecera 'Authorization' inválido. Usar 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_key = parts[1] # El token/clave proporcionado

    # 4. Comparación segura de la clave
    if not secrets.compare_digest(provided_key, expected_api_key):
        logger.warning(f"Acceso denegado: API Key inválida proporcionada.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Si todo es correcto, la clave es válida
    logger.debug("API Key validada correctamente.")
    return provided_key


# --- Otras funciones de seguridad podrían ir aquí ---