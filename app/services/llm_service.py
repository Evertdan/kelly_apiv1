# app/services/llm_service.py
# -*- coding: utf-8 -*-

"""
Servicio para interactuar con el LLM Generativo (ej. DeepSeek)
usando la librería 'openai'.
"""

import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache

# Importar configuración (con fallback)
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError:
    print("[ERROR llm_service.py] No se pudo importar 'settings'. Usando defaults dummy.")
    class DummySettings: # Dummy si config no está
        DEEPSEEK_API_KEY: Optional[Any] = None
        DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/"
        DEEPSEEK_MODEL_NAME: str = "deepseek-chat"
        LLM_REQUEST_TIMEOUT: float = 120.0
    settings = DummySettings() # type: ignore
    CONFIG_LOADED = False
except Exception as config_err:
     print(f"[ERROR llm_service.py] Error al importar/validar 'settings': {config_err}.")
     class DummySettings: # Dummy si config falla validación
         DEEPSEEK_API_KEY: Optional[Any]=None; DEEPSEEK_BASE_URL: str="https://api.deepseek.com/"; DEEPSEEK_MODEL_NAME:str="deepseek-chat"; LLM_REQUEST_TIMEOUT:float=120.0
     settings = DummySettings(); CONFIG_LOADED = False

# Importar cliente OpenAI y sus excepciones
try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING: from openai import AsyncOpenAI

    from openai import AsyncOpenAI as OpenAIClient
    from openai import RateLimitError, APIError, AuthenticationError, APIConnectionError, APITimeoutError, BadRequestError
    OPENAI_AVAILABLE = True
except ImportError:
    print("[ERROR llm_service.py] Librería 'openai' no instalada. Ejecuta: pip install openai")
    OpenAIClient = None; RateLimitError = ConnectionError; APIError = ConnectionError; AuthenticationError = ConnectionError; APIConnectionError = ConnectionError; APITimeoutError = TimeoutError; BadRequestError = ValueError; OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# --- Cliente LLM Cacheado ---

@lru_cache(maxsize=1) # Cachear una única instancia del cliente
def _get_llm_client() -> Optional[OpenAIClient]:
    """Inicializa y devuelve una instancia cacheada del cliente OpenAI/DeepSeek Async."""
    if not OPENAI_AVAILABLE:
        logger.critical("Librería 'openai' no disponible. Servicio LLM desactivado.")
        return None
    if not CONFIG_LOADED:
        logger.critical("Configuración no cargada. No se puede inicializar LLM.")
        return None

    # Usar getattr para acceso seguro
    api_key_secret = getattr(settings, 'DEEPSEEK_API_KEY', None)
    api_key = api_key_secret.get_secret_value() if api_key_secret and hasattr(api_key_secret, 'get_secret_value') else None
    base_url = str(getattr(settings, 'DEEPSEEK_BASE_URL', None))
    timeout = getattr(settings, 'LLM_REQUEST_TIMEOUT', 120.0)

    if not api_key:
        logger.error("DEEPSEEK_API_KEY no configurada. Servicio LLM desactivado.")
        return None
    if not base_url:
        logger.error("DEEPSEEK_BASE_URL no configurada. Servicio LLM desactivado.")
        return None

    try:
        logger.info(f"Inicializando cliente LLM Async para: {base_url}")
        client = OpenAIClient(api_key=api_key, base_url=base_url, timeout=timeout)
        return client
    except Exception as e:
        logger.exception(f"Error inesperado al inicializar el cliente LLM: {e}")
        return None

# --- Función Pública del Servicio ---

async def call_llm(
    messages: List[Dict[str, str]],
    temperature: float = 0.5, # Podría leerse de settings si se quiere configurable
    max_tokens: int = 1500 # Podría leerse de settings
    ) -> Optional[str]:
    """
    Realiza una llamada al LLM configurado (DeepSeek) con los mensajes proporcionados.

    Args:
        messages: Lista de diccionarios de mensajes [{"role": ..., "content": ...}].
        temperature: Temperatura para la generación.
        max_tokens: Límite máximo de tokens a generar.

    Returns:
        La respuesta de texto generada por el LLM como string, o None si ocurre un error.
    """
    client = _get_llm_client()
    if client is None:
        logger.error("Intento de llamar al LLM sin cliente inicializado.")
        # Considerar lanzar una excepción aquí si este es un estado irrecuperable
        # raise LLMServiceError("Cliente LLM no disponible")
        return None # Devolver None por ahora

    if not messages:
        logger.warning("Se llamó a call_llm sin mensajes.")
        return None

    model_name = settings.DEEPSEEK_MODEL_NAME
    logger.debug(f"Llamando a LLM '{model_name}' con {len(messages)} mensajes...")
    if messages: logger.debug(f"  Último mensaje ({messages[-1].get('role', '?')}): '{messages[-1].get('content', '')[:100]}...'")

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages, # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
            # Otros parámetros como 'stop' pueden añadirse aquí
        )

        if response.choices and response.choices[0].message:
            llm_answer = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            logger.debug(f"Respuesta LLM recibida (finish_reason: {finish_reason}). Inicio: '{llm_answer[:100] if llm_answer else 'VACÍO'}...'")

            if llm_answer: return llm_answer.strip()
            else: logger.warning(f"LLM devolvió respuesta sin contenido (finish_reason: {finish_reason})."); return None
        else:
            logger.warning(f"Respuesta inesperada de API LLM (sin choices/message): {str(response)[:500]}...")
            return None

    # Manejo de Errores Específicos (usando los importados de openai)
    except AuthenticationError as e:
        logger.error(f"Error de autenticación con API LLM: {e}. Verifica DEEPSEEK_API_KEY.")
        # raise LLMServiceError("Error de autenticación LLM", status_code=500) from e # Ejemplo con excepción custom
        return None
    except RateLimitError as e:
        logger.error(f"Límite de tasa alcanzado con API LLM: {e}.")
        # raise LLMServiceError("Límite de tasa LLM excedido", status_code=429) from e
        return None
    except APIConnectionError as e:
        logger.error(f"Error de conexión con API LLM en {settings.DEEPSEEK_BASE_URL}: {e}")
        # raise LLMServiceError("Error de conexión con LLM", status_code=504) from e
        return None
    except APITimeoutError as e:
        logger.error(f"Timeout esperando respuesta de API LLM (límite: {settings.LLM_REQUEST_TIMEOUT}s): {e}")
        # raise LLMServiceError("Timeout esperando LLM", status_code=504) from e
        return None
    except BadRequestError as e: # Ej: Prompt muy largo
         logger.error(f"Error 'Bad Request' (400) de API LLM: {e}. ¿Prompt demasiado largo?")
         # raise LLMServiceError(f"Error 400 del LLM: {e}", status_code=400) from e
         return None
    except APIError as e: # Otros errores 4xx/5xx
        logger.error(f"Error en API LLM: Status={getattr(e, 'status_code', 'N/A')}, Respuesta={getattr(e, 'body', 'N/A')}")
        # raise LLMServiceError(f"Error API LLM {getattr(e, 'status_code', 'N/A')}", status_code=502) from e
        return None
    except Exception as e: # Capturar cualquier otro error inesperado
        logger.exception(f"Error inesperado durante llamada a API LLM: {e}")
        # raise LLMServiceError("Error inesperado en servicio LLM") from e
        return None



# --- Bloque para pruebas rápidas ---
if __name__ == "__main__":
    import asyncio

    async def test_llm_service_call():
        logging.basicConfig(level=logging.INFO) # Cambiar a DEBUG para ver más
        print("--- Probando LLM Service (Async - Requiere .env válido) ---")
        try:
            from app.core.config import settings
            # ¡Asegúrate de tener DEEPSEEK_API_KEY y QDRANT_URL (requerido por Settings) en .env!
            print(f"Usando modelo LLM: {settings.DEEPSEEK_MODEL_NAME} en {settings.DEEPSEEK_BASE_URL}")

            test_messages: List[Dict[str, str]] = [
                {"role": "system", "content": "Eres un asistente conciso."},
                {"role": "user", "content": "Explica qué es una API REST en una frase."}
            ]
            response = await call_llm(test_messages)

            if response:
                print("\nRespuesta del LLM:")
                print(response)
            else:
                print("\nFallo al obtener respuesta del LLM (revisa logs y API Key).")

        except ImportError:
             print("Error importando Settings. Ejecuta desde la raíz del proyecto.")
        except ValidationError as val_err: # Capturar error si faltan settings
             print(f"Error de configuración en .env: {val_err}")
        except Exception as e:
            print(f"\nError durante la prueba: {e}")

    try:
        asyncio.run(test_llm_service_call())
    except RuntimeError:
         print("Podría necesitarse un loop diferente si ya hay uno corriendo.")
    except Exception as e_main:
         print(f"Error ejecutando la prueba: {e_main}")