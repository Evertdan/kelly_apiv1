# app/api/v1/api.py
# -*- coding: utf-8 -*-

"""
Router principal que agrupa todos los endpoints de la versión 1 de la API KellyBot.
"""

import logging # Añadir logging para errores de importación
from fastapi import APIRouter

# Importar los routers específicos de los endpoints de v1
# Asume que app/api/v1/endpoints/chat.py existe y define 'router'.
try:
    from app.api.v1.endpoints import chat
    # from app.api.v1.endpoints import users # Ejemplo futuro
    ENDPOINTS_AVAILABLE = True
except ImportError as e:
    # Usar un logger si este módulo se importa después de la config de logging
    try:
        logger = logging.getLogger(__name__)
        logger.error(f"[ERROR api_v1/api.py] No se pudieron importar routers: {e}")
    except NameError:
        print(f"[ERROR api_v1/api.py] No se pudieron importar routers: {e}")
    ENDPOINTS_AVAILABLE = False
    # Considera relanzar el error
    # raise e

# Crear el router principal para la versión 1 de la API
router = APIRouter()

# Incluir los routers de los endpoints específicos en este router principal
if ENDPOINTS_AVAILABLE:
    # Incluir el router de chat
    if 'chat' in locals() and hasattr(chat, 'router'):
        # Esta línea toma las rutas de chat.py y las añade aquí.
        router.include_router(chat.router, tags=["Chat"])
    else:
         # Loguear error si no se pudo importar chat
         try: logging.getLogger(__name__).error("No se pudo incluir chat.router.")
         except NameError: print("[ERROR api_v1/api.py] No se pudo incluir chat.router.")

    # Ejemplo: Incluir otros routers v1 en el futuro
    # if 'users' in locals() and hasattr(users, 'router'):
    #     router.include_router(users.router, prefix="/users", tags=["Usuarios"])

else:
     # Loguear advertencia si no se cargaron endpoints
     try: logging.getLogger(__name__).warning("No se incluyeron routers v1 por errores previos.")
     except NameError: print("[WARN api_v1/api.py] No se incluyeron routers v1 por errores previos.")


# Nota: El router de 'status' (para / y /health) se incluye
# directamente en app/main.py sin este prefijo /api/v1.