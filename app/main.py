# app/main.py
# -*- coding: utf-8 -*-

"""
Punto de entrada principal para la aplicación API KellyBot con FastAPI.
Versión final con lifespan, favicon y routers incluidos.
"""

import logging
import time
import sys
from pathlib import Path
import random
import string
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse # Necesario para favicon
from fastapi.middleware.cors import CORSMiddleware

# --- Importar configuración y routers ---
# Asume que estos archivos existen y están correctos
try:
    from app.core.config import settings
    from app.api.v1.api import router as api_v1_router
    from app.api.v1.endpoints.status import router as status_router
    CONFIG_LOADED = True
except ImportError as e:
     print(f"[ERROR CRÍTICO main.py] Fallo al importar módulos: {e}")
     CONFIG_LOADED = False
     raise e # Detener si falta algo esencial
except Exception as e: # Captura errores de validación de Settings aquí
     print(f"[ERROR CRÍTICO main.py] Error durante importación inicial (config?): {e}")
     CONFIG_LOADED = False
     # config.py ya debería haber llamado a sys.exit si la validación falló
     raise e


# Configurar logger
logger = logging.getLogger(__name__)

# --- Lifespan Context Manager (Corregido) ---
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Maneja los eventos de inicio y apagado de la aplicación.
    """
    logger.info("--- Iniciando KellyBot API (Lifespan) ---")
    if CONFIG_LOADED:
        # Acceder a settings usando nombres en MAYÚSCULAS
        logger.info(f"Host: {settings.API_HOST}, Puerto: {settings.API_PORT}, LogLevel: {settings.LOG_LEVEL}")
        logger.info(f"Modelo LLM: {settings.DEEPSEEK_MODEL_NAME}")
        logger.info(f"Modelo Embeddings: {settings.EMBEDDING_MODEL_NAME} (Dim: {settings.VECTOR_DIMENSION}) en {settings.EMBEDDING_DEVICE}")
        logger.info(f"Qdrant URL: {settings.QDRANT_URL}")
        logger.info(f"Qdrant Collection: {settings.QDRANT_COLLECTION_NAME}")
        if settings.MONGO_URI: logger.info("Configuración de MongoDB detectada.")
        else: logger.info("Historial MongoDB no configurado.")
        priority_path = settings.PRIORITY_CONTEXT_FILE_PATH
        if priority_path and isinstance(priority_path, Path) and priority_path.is_file(): logger.info(f"Contexto prioritario activo: {priority_path}")
        else: logger.info(f"Contexto prioritario no configurado o archivo '{priority_path}' no encontrado.")
        logger.info("Verificando componentes necesarios...")
        # Aquí podrías añadir verificaciones o precarga de modelos/clientes
    else:
        logger.error("La configuración no se cargó correctamente. La API puede no funcionar.")

    logger.info("--- KellyBot API Lista (Lifespan) ---")

    yield # La aplicación se ejecuta aquí

    logger.info("--- Deteniendo KellyBot API (Lifespan) ---")
    # Lógica de limpieza
    logger.info("--- KellyBot API Detenida (Lifespan) ---")


# --- Crear Aplicación FastAPI ---
app = FastAPI(
    title=getattr(settings, 'PROJECT_NAME', "KellyBot API") if CONFIG_LOADED else "KellyBot API",
    description="API para procesar solicitudes de chat usando RAG con Qdrant y LLMs.",
    version=getattr(settings, 'PROJECT_VERSION', "0.1.0") if CONFIG_LOADED else "0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan # Usar el context manager lifespan
)

# --- Endpoint para Favicon ---
favicon_path = Path(__file__).parent / "static" / "favicon.ico"
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    """Sirve el archivo favicon.ico."""
    if favicon_path.is_file():
        return FileResponse(favicon_path, media_type='image/vnd.microsoft.icon')
    else:
        # Devolver 204 No Content para evitar 404 en logs si no existe
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)


# --- Middlewares (Opcional) ---
# Ejemplo: CORS Middleware (Descomentar y ajustar si es necesario)
# origins = ["http://localhost:3000", "https://tu-frontend.com"]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# --- Incluir Routers ---
# Router de Estado (/, /health) montado en la raíz
if 'status_router' in locals() and status_router:
     app.include_router(status_router, tags=["Status"])
else:
     logger.error("No se pudo incluir status_router (error importación).")

# Router V1 (/api/v1/chat, etc.) montado bajo prefijo
if 'api_v1_router' in locals() and api_v1_router:
    app.include_router(api_v1_router, prefix="/api/v1")
else:
     logger.error("No se pudo incluir api_v1_router (error importación).")


# --- Manejador de Excepciones Global (Opcional) ---
# @app.exception_handler(Exception)
# async def generic_exception_handler(request: Request, exc: Exception):
#     logger.exception(f"Error no manejado procesando request {request.url.path}: {exc}")
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={"detail": "Ocurrió un error interno inesperado en el servidor."},
#     )

# Nota: No es necesario un @app.get("/") aquí porque el status_router ya maneja esa ruta.