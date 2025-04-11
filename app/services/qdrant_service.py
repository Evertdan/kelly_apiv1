# app/services/qdrant_service.py
# -*- coding: utf-8 -*-

"""
Servicio para interactuar con Qdrant: inicializar cliente y buscar documentos.
CORREGIDO: Eliminado argumento 'with_vector' de client.search().
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union # Añadido Union
from functools import lru_cache
import numpy as np # Para el bloque de prueba
import asyncio # Para el bloque de prueba

# Importar configuración (con fallback)
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError:
    print("[ERROR qdrant_service.py] No se pudo importar 'settings'. Usando defaults dummy.")
    class DummySettings: # Dummy si config no está
        QDRANT_URL: str = "http://localhost:6333"
        QDRANT_API_KEY: Optional[Any] = None # Usar Any para SecretStr dummy
        QDRANT_COLLECTION_NAME: str = "default_collection"
        RAG_TOP_K: int = 3
        vector_dimension: int = 384 # Default genérico
    settings = DummySettings() # type: ignore
    CONFIG_LOADED = False
except Exception as config_err:
     print(f"[ERROR qdrant_service.py] Error al importar/validar 'settings': {config_err}.")
     class DummySettings: # Dummy si config falla validación
         QDRANT_URL: str = "http://localhost:6333"; QDRANT_API_KEY: Optional[Any]=None; QDRANT_COLLECTION_NAME: str="default"; RAG_TOP_K:int=3; vector_dimension:int=384
     settings = DummySettings(); CONFIG_LOADED = False

# Importar cliente Qdrant y modelos/excepciones
try:
    from qdrant_client import AsyncQdrantClient, models
    from qdrant_client.http.models import PointStruct, Distance, VectorParams, ScoredPoint, Filter
    from qdrant_client.http.exceptions import UnexpectedResponse
    QDRANT_AVAILABLE = True
except ImportError:
    print("[ERROR qdrant_service.py] 'qdrant-client' no instalado. Ejecuta: pip install qdrant-client")
    AsyncQdrantClient = None; models = None; ScoredPoint = Any; Filter = Any; UnexpectedResponse = ConnectionError; QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- Helper para Decodificar Errores ---
def _decode_qdrant_error_content(content: Optional[bytes]) -> str:
    """Intenta decodificar el contenido de un error de Qdrant (bytes) a string."""
    if isinstance(content, bytes):
        try: return content.decode('utf-8', errors='replace')
        except Exception: return repr(content)
    return str(content)

# --- Cliente Qdrant Cacheado ---
@lru_cache(maxsize=1)
def _get_qdrant_client() -> Optional[AsyncQdrantClient]:
    """Inicializa y devuelve una instancia cacheada del cliente AsyncQdrantClient."""
    if not QDRANT_AVAILABLE:
        logger.critical("Librería 'qdrant-client' no disponible.")
        return None
    if not CONFIG_LOADED:
        logger.critical("Configuración no cargada. No se puede inicializar Qdrant.")
        return None

    # Usar getattr para acceso seguro
    qdrant_url = str(getattr(settings, 'QDRANT_URL', None))
    api_key_secret = getattr(settings, 'QDRANT_API_KEY', None)
    api_key = api_key_secret.get_secret_value() if api_key_secret and hasattr(api_key_secret, 'get_secret_value') else None

    if not qdrant_url:
        logger.error("QDRANT_URL no configurada. Servicio Qdrant desactivado.")
        return None

    logger.info(f"Inicializando cliente AsyncQdrantClient para URL: {qdrant_url}...")
    try:
        client = AsyncQdrantClient(url=qdrant_url, api_key=api_key)
        logger.info("Instancia de AsyncQdrantClient creada.")
        # Podríamos añadir una verificación de conexión aquí si fuera crítico al inicio
        # ej. await client.health_check() dentro de una función async separada
        return client
    except Exception as e:
        logger.exception(f"Error inesperado al inicializar AsyncQdrantClient: {e}")
        return None

# --- Función Pública del Servicio ---
async def search_documents(
    vector: List[float],
    top_k: Optional[int] = None,
    query_filter: Optional[models.Filter] = None # Permitir filtros
) -> List[Dict[str, Any]]:
    """
    Busca en Qdrant los puntos más similares a un vector de consulta dado.

    Args:
        vector: El vector embedding de la consulta del usuario.
        top_k: El número máximo de resultados a devolver. Usa RAG_TOP_K de settings si es None.
        query_filter: (Opcional) Un filtro de Qdrant.

    Returns:
        Lista de diccionarios con 'id', 'score', 'payload', o lista vacía en error/sin resultados.
    """
    client = _get_qdrant_client()
    if client is None:
        logger.error("Intento de búsqueda en Qdrant sin cliente inicializado.")
        return []

    # Usar getattr para acceso seguro a settings
    collection_name = getattr(settings, 'QDRANT_COLLECTION_NAME', 'default_collection')
    limit = top_k if top_k is not None else getattr(settings, 'RAG_TOP_K', 3)

    if not vector or not isinstance(vector, list):
         logger.error("Intento de búsqueda con vector inválido.")
         return []

    logger.debug(f"Buscando {limit} documentos en '{collection_name}'...")
    try:
        # La llamada a search ya fue corregida (sin with_vector=False)
        search_result: List[ScoredPoint] = await client.search(
            collection_name=collection_name,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True  # Esencial para obtener los metadatos
        )

        # Procesar resultados
        results_list = []
        if search_result:
            for point in search_result:
                 payload_content = point.payload if point.payload is not None else {}
                 results_list.append({
                     "id": point.id, # El UUID del punto
                     "score": point.score,
                     "payload": payload_content
                 })
            logger.info(f"Búsqueda Qdrant completada. Encontrados {len(results_list)} resultados.")
        else:
            logger.info("Búsqueda Qdrant completada. No se encontraron resultados.")
        return results_list

    except UnexpectedResponse as e:
        content_str = _decode_qdrant_error_content(e.content)
        logger.error(f"Error de Qdrant durante búsqueda en '{collection_name}': Status={e.status_code}, Contenido={content_str}")
        # Aquí podríamos lanzar QdrantServiceError si lo definimos en exceptions.py
        # raise QdrantServiceError(f"Error Qdrant {e.status_code}", status_code=503) from e
        return [] # Devolver vacío por ahora
    except Exception as e:
        logger.exception(f"Error inesperado durante búsqueda en Qdrant en '{collection_name}': {e}")
        # raise QdrantServiceError("Error inesperado en búsqueda Qdrant") from e
        return []
    # No es necesario cerrar el cliente aquí explícitamente si se maneja globalmente o al apagar la app.

# --- Bloque para pruebas rápidas (sin cambios funcionales) ---
if __name__ == "__main__":
    # ... (código del bloque de prueba sin cambios)...
    # ... (requiere instancia Qdrant y .env configurado para funcionar)...
    pass # Añadir pass para que el bloque sea sintácticamente válido si comentas el resto