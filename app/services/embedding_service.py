# app/services/embedding_service.py
# -*- coding: utf-8 -*-

"""
Servicio para cargar modelos SentenceTransformer y generar embeddings para textos (queries).
MODIFICADO: Usa asyncio.to_thread para la llamada bloqueante a model.encode().
"""

import logging
import asyncio # Para asyncio.to_thread
from typing import List, Optional, Any, Dict, Tuple, TypeAlias # Añadir TypeAlias
from functools import lru_cache

# Importar configuración (con fallback)
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError:
    print("[ERROR embedding_service.py] No se pudo importar 'settings'. Usando defaults dummy.")
    class DummySettings: # Dummy si config no está
        embedding_model_name: str = "all-MiniLM-L6-v2"
        embedding_device: str = "cpu"
        vector_dimension: int = 384
    settings = DummySettings() # type: ignore
    CONFIG_LOADED = False
except Exception as config_err:
     print(f"[ERROR embedding_service.py] Error al importar/validar 'settings': {config_err}.")
     class DummySettings: # Dummy si config falla validación
         embedding_model_name: str = "all-MiniLM-L6-v2"
         embedding_device: str = "cpu"
         vector_dimension: int = 384
     settings = DummySettings() # type: ignore
     CONFIG_LOADED = False

# Importar dependencias de ML (con fallbacks)
try:
    import numpy as np
    # Define un alias de tipo más específico si numpy está disponible
    NumpyArray: TypeAlias = np.ndarray[Any, np.dtype[np.float_]]
    NUMPY_AVAILABLE = True
except ImportError:
    print("[ERROR embedding_service.py] Numpy no instalado. Ejecuta: pip install numpy")
    np = None # type: ignore
    NumpyArray: TypeAlias = Any # Fallback a Any si numpy falta
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("[ERROR embedding_service.py] sentence-transformers no instalado. Ejecuta: pip install sentence-transformers")
    SentenceTransformer = None # type: ignore
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    print("[ADVERTENCIA embedding_service.py] PyTorch no instalado. Detección/uso GPU no funcionará.")
    torch = None # type: ignore
    TORCH_AVAILABLE = False


logger = logging.getLogger(__name__)

# --- Carga Cacheada del Modelo ---

@lru_cache(maxsize=1) # Cachear solo una instancia del modelo
def get_embedding_model() -> Optional[SentenceTransformer]:
    """
    Carga y devuelve la instancia del modelo SentenceTransformer configurado.
    Utiliza caché y maneja la selección de dispositivo (auto/cpu/cuda).
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE or not NUMPY_AVAILABLE or not CONFIG_LOADED:
        logger.critical("Dependencias (numpy/sentence-transformers) o Configuración no disponibles.")
        return None

    # Usar nombres en MAYUSCULAS de settings
    model_name = settings.EMBEDDING_MODEL_NAME
    device_setting = settings.EMBEDDING_DEVICE.lower()
    expected_dim = settings.VECTOR_DIMENSION

    # Determinar dispositivo final
    final_device = "cpu" # Default
    if device_setting == "cuda":
        if TORCH_AVAILABLE and torch.cuda.is_available():
            final_device = "cuda"
            logger.info("Configurado para usar CUDA y está disponible.")
        else:
            logger.warning("Configurado para usar CUDA pero no disponible/PyTorch no instalado. Usando CPU.")
            final_device = "cpu"
    elif device_setting == "auto":
        if TORCH_AVAILABLE and torch.cuda.is_available():
            final_device = "cuda"
            logger.info("Modo 'auto': CUDA detectado, usando GPU.")
        else:
            final_device = "cpu"
            logger.info("Modo 'auto': CUDA no disponible, usando CPU.")
    elif device_setting == "cpu":
         final_device = "cpu"
         logger.info(f"Usando dispositivo CPU (config: {device_setting}).")
    else:
         logger.warning(f"Valor de EMBEDDING_DEVICE ('{settings.EMBEDDING_DEVICE}') no reconocido. Usando CPU.")
         final_device = "cpu"

    try:
        logger.info(f"Cargando modelo SentenceTransformer: '{model_name}' en dispositivo '{final_device}'...")
        model = SentenceTransformer(model_name_or_path=model_name, device=final_device)

        # Verificar dimensión cargada vs esperada
        try:
            loaded_dim = model.get_sentence_embedding_dimension()
            if loaded_dim != expected_dim:
                 logger.critical(f"¡DISCREPANCIA DE DIMENSIÓN! Modelo '{model_name}'={loaded_dim}, Config={expected_dim}.")
                 return None # Fallar si no coincide
            logger.info(f"Modelo '{model_name}' (Dim: {loaded_dim}) cargado en {final_device.upper()}.")
            if isinstance(model, SentenceTransformer): return model
            else: logger.error("Objeto cargado no es SentenceTransformer."); return None
        except Exception as e_dim:
             logger.error(f"No se pudo verificar dimensión del modelo '{model_name}': {e_dim}")
             return None # Fallar si no podemos verificar

    except OSError as e:
        logger.error(f"Error OS cargando modelo '{model_name}': {e}.")
        return None
    except Exception as e:
        logger.exception(f"Error inesperado al cargar modelo '{model_name}': {e}")
        return None

# --- Función Pública del Servicio ---

async def embed_query(query: str) -> List[float]:
    """
    Genera el embedding vectorial para una única consulta (string).
    Ejecuta model.encode en un hilo separado para no bloquear asyncio.
    """
    if not query or not isinstance(query, str):
        logger.error("Se recibió una query inválida para generar embedding.")
        raise ValueError("Query inválida proporcionada.")

    model = get_embedding_model() # Obtener modelo cacheado

    if model is None:
        logger.critical("El modelo de embeddings no está disponible o no pudo cargarse.")
        raise ValueError("Servicio de Embeddings no disponible.")

    logger.debug(f"Generando embedding para query (en thread): '{query[:80]}...'")
    try:
        # Ejecutar la función síncrona model.encode en el thread pool por defecto
        embeddings_result: Optional[NumpyArray] = await asyncio.to_thread(
            model.encode, # La función síncrona
            [query],      # Argumentos posicionales
            # Argumentos keyword:
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True
        )

        # Validar el resultado
        if embeddings_result is not None and isinstance(embeddings_result, np.ndarray) and embeddings_result.shape[0] == 1:
             # Extraer, asegurar float32, y convertir a lista Python
             vector: List[float] = embeddings_result[0].astype(np.float32).tolist()
             logger.debug(f"Embedding generado (dim: {len(vector)})")
             return vector
        else:
             shape_info = getattr(embeddings_result, 'shape', 'N/A')
             type_info = type(embeddings_result).__name__
             logger.error(f"Resultado inesperado de model.encode. Tipo: {type_info}, Shape: {shape_info}")
             raise ValueError("Fallo al generar embedding: resultado inesperado.")

    except Exception as e:
        logger.exception(f"Error inesperado generando embedding para query '{query[:80]}...': {e}")
        raise ValueError(f"Error interno al generar embedding.") from e

# --- Bloque para pruebas rápidas ---
if __name__ == "__main__":
    import asyncio

    async def test_embedding():
        logging.basicConfig(level=logging.INFO)
        print("--- Probando Servicio de Embeddings (Async) ---")
        try:
            from app.core.config import settings
            # Necesita que .env tenga las variables requeridas por Settings (QDRANT_URL, etc.)
            print(f"Usando modelo: {settings.EMBEDDING_MODEL_NAME} en device: {settings.EMBEDDING_DEVICE}")
            print(f"Dimensión esperada: {settings.VECTOR_DIMENSION}")

            test_query = "Esta es una consulta de prueba para el servicio de embeddings."
            vector = await embed_query(test_query)
            if vector:
                print(f"\nQuery: {test_query}")
                print(f"Vector generado (Primeros 5 / Últimos 5 de {len(vector)} dims):")
                print(f"  Inicio: {[f'{x:.4f}' for x in vector[:5]]}") # Formatear floats
                print(f"  Fin:    {[f'{x:.4f}' for x in vector[-5:]]}")
                assert len(vector) == settings.VECTOR_DIMENSION, "¡Dimensión incorrecta!"
                print("\nPrueba de embedding completada exitosamente.")
            else:
                print("\nFallo al generar embedding (vector es None/vacío).")
        except ImportError:
             print("\nError importando Settings. Ejecuta desde la raíz.")
        except ValidationError as val_err:
             print(f"\nError de configuración en .env: {val_err}")
        except ValueError as e:
             print(f"\nError de Valor durante la prueba (ej. modelo no cargado?): {e}")
        except Exception as e:
            print(f"\nError inesperado durante la prueba: {e}")

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_embedding())
    except RuntimeError:
         print("Podría necesitarse un loop diferente si ya hay uno corriendo.")
    except Exception as e_main:
         print(f"Error ejecutando la prueba: {e_main}")