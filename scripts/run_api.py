# scripts/run_api.py
# -*- coding: utf-8 -*-

"""
Punto de entrada para iniciar el servidor FastAPI de Kelly API usando Uvicorn.

Lee la configuración de host, puerto, nivel de log y recarga desde
la configuración centralizada (app.core.config.settings).
"""

import logging
import sys
from pathlib import Path
import os # Añadir import os para el fallback de settings

# --- Configuración Inicial de Logging (Básico) ---
logging.basicConfig(level='INFO', format='%(asctime)s - %(name)s [%(levelname)s] - %(message)s')
logger = logging.getLogger("run_api")

# --- Importar Uvicorn y Settings ---
try:
    import uvicorn
except ImportError:
    logger.critical("¡Error CRÍTICO! Uvicorn no está instalado.")
    logger.critical("Ejecuta: pip install uvicorn[standard]")
    sys.exit(1)

try:
    # Ajustar PYTHONPATH si es necesario
    project_root = Path(__file__).parent.parent.resolve()
    # Añadir la raíz al path si no está
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        logger.debug(f"Añadido {project_root} a sys.path")

    # Importar la instancia de settings (que ya maneja errores de carga críticos)
    from app.core.config import settings
    # Importar pydantic ValidationError por si acaso
    from pydantic import ValidationError

    # Opcional: Verificar que app.main:app es importable
    # from app.main import app
    CONFIG_LOADED = True

except ImportError as e:
    logger.critical(f"Error importando configuración o aplicación: {e}")
    logger.critical("Asegúrate de ejecutar desde la raíz del proyecto 'kelly_api/'")
    logger.critical("y que la estructura 'app/core/config.py' y 'app/main.py' existen.")
    logger.critical("Verifica dependencias instaladas ('pip install -e .').")
    CONFIG_LOADED = False # Marcar que la configuración no cargó
    # No salir aquí necesariamente, start_server lo manejará
except ValidationError as e_val:
     # Capturar error si falta config esencial al importar settings
     logger.critical(f"Error CRÍTICO de Validación al importar settings: {e_val}")
     logger.critical(f"Revisa tu archivo .env en {project_root} (o donde esté).")
     CONFIG_LOADED = False
     sys.exit("Fallo de configuración inicial.") # Salir si la config es inválida
except Exception as e:
     logger.critical(f"Error inesperado durante importación inicial: {e}")
     CONFIG_LOADED = False
     sys.exit("Fallo inesperado en importaciones.")


# --- Función Principal ---
def start_server():
    """Inicia el servidor Uvicorn con la configuración cargada."""

    # Salir si la configuración no se cargó correctamente
    if not CONFIG_LOADED:
         logger.critical("No se puede iniciar el servidor debido a errores previos de configuración/importación.")
         sys.exit("Fallo en carga inicial.")

    # Leer configuración desde el objeto settings importado
    try:
        host = settings.API_HOST
        port = settings.API_PORT
        log_level = settings.LOG_LEVEL.lower() # Uvicorn usa minúsculas

        # Leer flag de reload (asegurarse de que existe en Settings)
        use_reload = getattr(settings, 'API_RELOAD', False) # Default False si no existe

    except AttributeError as e:
        logger.critical(f"Error accediendo a un atributo de configuración: {e}")
        logger.critical("Verifica que todas las variables esperadas estén definidas en app/core/config.py")
        sys.exit("Fallo al leer configuración.")

    # Loguear configuración de inicio
    if use_reload:
        logger.warning("¡Modo de Recarga Automática ACTIVADO! Solo para desarrollo.")
    logger.info(f"Iniciando servidor Uvicorn en http://{host}:{port}")
    logger.info(f"Nivel de Log Uvicorn: {log_level}")
    logger.info(f"Recarga automática (reload): {'Activada' if use_reload else 'Desactivada'}")

    # Iniciar Uvicorn
    try:
        uvicorn.run(
            "app.main:app",      # Ruta al objeto FastAPI: 'directorio.archivo:objeto_app'
            host=host,
            port=port,
            log_level=log_level,
            reload=use_reload,   # Activa/desactiva recarga automática
            # Vigilar solo la carpeta 'app' para recargar
            reload_dirs=[str(project_root / "app")] if use_reload else None,
        )
    except Exception as e:
        logger.critical(f"Error fatal al intentar iniciar Uvicorn: {e}", exc_info=True)
        sys.exit("Fallo al iniciar el servidor API.")

# --- Punto de Entrada ---
if __name__ == "__main__":
    # Este bloque se ejecuta cuando corres 'python scripts/run_api.py'
    start_server()