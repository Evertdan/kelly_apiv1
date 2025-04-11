# app/services/priority_context_service.py
# -*- coding: utf-8 -*-

"""
Servicio para buscar respuestas predefinidas o prioritarias
en un archivo JSON local antes de ejecutar el pipeline RAG principal.
"""

import json
import logging
import difflib # Para la búsqueda por similitud
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from functools import lru_cache

# Importar configuración (con fallback)
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError:
    print("[ERROR priority_context_service.py] No se pudo importar 'settings'. Usando defaults.")
    class DummySettings: # Dummy si config no está
        priority_context_file_path: Optional[Path] = Path("data/priority_context.json")
        PRIORITY_SIMILARITY_THRESHOLD: float = 0.85
    settings = DummySettings() # type: ignore
    CONFIG_LOADED = False
except Exception as config_err:
     print(f"[ERROR priority_context_service.py] Error al importar/validar 'settings': {config_err}.")
     class DummySettings: # Dummy si config falla validación
         priority_context_file_path: Optional[Path]=Path("data/priority_context.json"); PRIORITY_SIMILARITY_THRESHOLD:float=0.85
     settings = DummySettings(); CONFIG_LOADED = False

# Importar excepciones personalizadas (opcional, para lanzar errores específicos)
try:
     from app.core.exceptions import PriorityContextError
except ImportError:
     print("[WARN priority_context_service.py] No se pudo importar PriorityContextError.")
     PriorityContextError = Exception # Usar Exception como fallback


logger = logging.getLogger(__name__)

# --- Carga Cacheada de Datos Prioritarios ---

@lru_cache(maxsize=1) # Cachear el resultado de la carga del archivo
def _load_priority_data() -> List[Dict[str, Any]]:
    """
    Carga los datos desde el archivo JSON definido en la configuración.
    Cachea el resultado en memoria.

    Returns:
        Una lista de diccionarios FAQ procesados, o una lista vacía si hay errores.
    """
    if not CONFIG_LOADED:
         logger.error("Configuración no disponible para Priority Context.")
         return []

    # Usar getattr para acceso seguro
    file_path = getattr(settings, 'priority_context_file_path', None)
    if not file_path:
        logger.info("Ruta de archivo de contexto prioritario no configurada. Servicio desactivado.")
        return []

    # Asegurar que sea Path (config.py debería haberlo resuelto, pero doble check)
    if isinstance(file_path, str): file_path = Path(file_path)
    if not isinstance(file_path, Path):
        logger.error(f"priority_context_file_path ({file_path}) no es ruta válida.")
        return []

    if not file_path.is_file():
        # Loguear como warning si el archivo configurado no existe
        logger.warning(f"Archivo de contexto prioritario no encontrado en: {file_path}. Servicio desactivado.")
        return []

    logger.info(f"Cargando contexto prioritario desde: {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict) or "faqs" not in data or not isinstance(data["faqs"], list):
            logger.error(f"Estructura JSON inválida en {file_path}. Se esperaba {{'faqs': [...]}}.")
            return [] # Devolver vacío si el formato es incorrecto

        # Filtrar y preprocesar FAQs válidas
        valid_faqs = []
        for i, faq in enumerate(data["faqs"]):
            question = faq.get('q')
            answer = faq.get('a')
            if isinstance(question, str) and question.strip() and isinstance(answer, str) and answer.strip():
                valid_faqs.append({
                    "q_lower": question.strip().lower(), # Guardar en minúsculas para comparar
                    "a": answer.strip(),
                    "keywords": [kw.lower() for kw in faq.get('keywords', []) if isinstance(kw, str)]
                })
            else:
                logger.warning(f"FAQ inválida (q/a vacíos o tipo incorrecto) en {file_path} (índice {i}). Ignorada.")

        logger.info(f"Contexto prioritario cargado y cacheado: {len(valid_faqs)} FAQs válidas encontradas.")
        return valid_faqs

    except json.JSONDecodeError as e:
        logger.error(f"Error decodificando JSON en {file_path}: {e}. Servicio desactivado.")
        return [] # Devolver vacío
    except PermissionError:
        logger.error(f"Permiso denegado al leer {file_path}. Servicio desactivado.")
        return []
    except Exception as e:
        logger.exception(f"Error inesperado cargando {file_path}: {e}. Servicio desactivado.")
        # Podríamos lanzar PriorityContextError aquí si queremos que el pipeline falle
        # raise PriorityContextError(f"Fallo al cargar contexto prioritario: {e}") from e
        return [] # Devolver vacío por ahora

# --- Función Pública del Servicio ---

async def find_priority_answer(query: str) -> Optional[str]:
    """
    Busca una respuesta para la query en los datos de contexto prioritario (FAQs locales).
    Implementa búsqueda exacta y por similitud.

    Args:
        query: La pregunta del usuario.

    Returns:
        La respuesta predefinida (str) si hay coincidencia, o None si no.
    """
    if not query or not isinstance(query, str):
        return None

    priority_faqs = _load_priority_data() # Obtener datos cacheados
    if not priority_faqs:
        # logger.debug("Contexto prioritario vacío o no disponible.")
        return None # No buscar si no hay datos

    query_lower = query.strip().lower()
    if not query_lower: return None # No buscar si la query queda vacía

    logger.debug(f"Buscando query en {len(priority_faqs)} FAQs prioritarias: '{query_lower[:80]}...'")

    # 1. Búsqueda por Coincidencia Exacta
    for faq in priority_faqs:
        if query_lower == faq["q_lower"]:
            logger.info(f"Coincidencia exacta encontrada en contexto prioritario.")
            return faq["a"]

    # 2. Búsqueda por Similitud
    best_match_score = 0.0
    best_match_answer = None
    # Crear matcher una vez
    matcher = difflib.SequenceMatcher(None, query_lower, autojunk=False) # autojunk=False puede ser mejor para frases

    for faq in priority_faqs:
        matcher.set_seq2(faq["q_lower"])
        # ratio() es relativamente rápido para comparar similitud general
        similarity = matcher.ratio()

        if similarity > best_match_score:
            best_match_score = similarity
            best_match_answer = faq["a"]
            # Loguear solo si es una similitud potencialmente interesante
            if similarity > 0.6: # Umbral arbitrario para logging
                 logger.debug(f"  -> Similitud {similarity:.3f} con Q: '{faq['q_lower'][:50]}...'")

    # 3. Decidir si la mejor similitud supera el umbral
    threshold = getattr(settings, 'PRIORITY_SIMILARITY_THRESHOLD', 0.85)
    # Validar umbral por si viene mal de config
    if not isinstance(threshold, (float, int)) or not (0 <= threshold <= 1): threshold = 0.85

    if best_match_score >= threshold:
        logger.info(f"Coincidencia por similitud encontrada (Score: {best_match_score:.3f} >= {threshold}).")
        return best_match_answer
    else:
        logger.debug(f"No se encontró coincidencia prioritaria suficiente (Mejor score: {best_match_score:.3f}).")
        return None # No se encontró
# --- Bloque para pruebas rápidas ---
if __name__ == "__main__":
    import asyncio

    async def test_priority_search():
        logging.basicConfig(level=logging.INFO) # Cambiar a DEBUG para ver más detalles
        print("--- Probando Priority Context Service ---")

        test_file = Path("./_test_priority.json")
        test_data = {
            "faqs": [
                {"q": "Hola", "a": "¡Hola! ¿En qué puedo ayudarte?", "keywords": ["saludo"]},
                {"q": "¿Cuál es el horario?", "a": "Nuestro horario es de 9 AM a 5 PM.", "keywords": ["horario", "atencion"]},
                {"q": "Quiero cancelar mi cuenta", "a": "Para cancelar, por favor contacta a soporte.", "keywords": ["cancelar", "baja", "cuenta"]},
                {"q": "  pregunta con espacios  ", "a": "Respuesta sin espacios extra.", "keywords":[]}
            ]
        }
        try:
            test_file.write_text(json.dumps(test_data, ensure_ascii=False, indent=2), encoding='utf-8')

            # Simular settings
            class MockSettings:
                priority_context_file_path: Optional[Path] = test_file
                PRIORITY_SIMILARITY_THRESHOLD: float = 0.85
            global settings
            original_settings = settings
            settings = MockSettings() # type: ignore

            _load_priority_data.cache_clear() # Limpiar caché para prueba
            print("Primera carga (forzada):")
            faqs = _load_priority_data()
            print(f"FAQs cargadas: {len(faqs)}")

            # Probar búsquedas
            tests = {
                "Hola": "¡Hola! ¿En qué puedo ayudarte?",
                "cual es el horario": "Nuestro horario es de 9 AM a 3 PM.",
                "quiero dar de baja mi cuenta": "Para cancelar, por favor contacta a soporte.",
                "  pregunta con espacios  ": "Respuesta sin espacios extra.",
                "algo no relacionado": None,
            }
            for query, expected in tests.items():
                print(f"\nBuscando '{query}':")
                answer = await find_priority_answer(query)
                print(f" -> Respuesta: {answer}")
                assert answer == expected

            settings = original_settings # Restaurar

        finally:
            if test_file.exists():
                test_file.unlink()
                print(f"\nArchivo de prueba {test_file} eliminado.")

    try:
        import asyncio
        asyncio.run(test_priority_search())
    except RuntimeError:
         print("Podría necesitarse un loop diferente si ya hay uno corriendo.")
    except Exception as e_main:
         print(f"Error ejecutando la prueba: {e_main}")