# app/services/history_service.py
# -*- coding: utf-8 -*-

"""
Servicio para gestionar el historial de conversaciones utilizando MongoDB.
Usa la integración con Langchain y asyncio.to_thread para operaciones potencialmente bloqueantes.
"""

import logging
import asyncio # NUEVO: Para asyncio.to_thread
from typing import List, Optional, Any

# Importar configuración (con fallback)
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError:
    print("[ERROR history_service.py] No se pudo importar 'settings'. Usando defaults.")
    class DummySettings:
        MONGO_URI: Optional[Any] = None; MONGO_DATABASE_NAME: str = "dummy_db"; MONGO_COLLECTION_NAME: str = "dummy_coll"
    settings = DummySettings(); CONFIG_LOADED = False
except Exception as config_err:
     print(f"[ERROR history_service.py] Error al importar/validar 'settings': {config_err}.")
     class DummySettings:
          MONGO_URI: Optional[Any]=None; MONGO_DATABASE_NAME: str="dummy_db"; MONGO_COLLECTION_NAME: str="dummy_coll"
     settings = DummySettings(); CONFIG_LOADED = False

# Importar excepciones personalizadas (opcional pero recomendado)
try:
     from app.core.exceptions import HistoryServiceError
except ImportError:
     print("[WARN history_service.py] No se pudo importar HistoryServiceError.")
     HistoryServiceError = Exception # Fallback a Exception genérica

# Importar dependencias de Langchain y MongoDB
try:
    from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    # Importar excepciones de Pymongo si quieres capturarlas específicamente
    # from pymongo.errors import ConnectionFailure, OperationFailure
    LANGCHAIN_MONGO_AVAILABLE = True
except ImportError:
    print("[ERROR history_service.py] Dependencias Langchain/Mongo no instaladas.")
    BaseMessage=Any; HumanMessage=Any; AIMessage=Any; MongoDBChatMessageHistory=None; LANGCHAIN_MONGO_AVAILABLE = False
    # ConnectionFailure = ConnectionError; OperationFailure = Exception # Dummies para except

logger = logging.getLogger(__name__)

# --- Funciones del Servicio ---

def _get_mongo_history_sync(session_id: str) -> Optional[MongoDBChatMessageHistory]:
    """
    Función SÍNCRONA interna para obtener una instancia de MongoDBChatMessageHistory.
    Separada para facilitar el uso con asyncio.to_thread si la creación es bloqueante.
    """
    if not LANGCHAIN_MONGO_AVAILABLE: return None
    if not CONFIG_LOADED: return None

    mongo_uri_secret = getattr(settings, 'MONGO_URI', None)
    connection_string = mongo_uri_secret.get_secret_value() if mongo_uri_secret and hasattr(mongo_uri_secret, 'get_secret_value') else None
    db_name = getattr(settings, 'MONGO_DATABASE_NAME', 'kellybot_chat')
    collection_name = getattr(settings, 'MONGO_COLLECTION_NAME', 'chat_histories')

    if not connection_string:
        # No loguear error aquí, solo debug. La función que llama decidirá si es un problema.
        logger.debug("MONGO_URI no configurada. Instancia de historial no creada.")
        return None

    try:
        # La creación de la instancia puede implicar conexión inicial
        history = MongoDBChatMessageHistory(
            connection_string=connection_string,
            session_id=session_id,
            database_name=db_name,
            collection_name=collection_name
        )
        return history
    except Exception as e:
        # Loguear excepción pero devolver None para indicar fallo
        logger.exception(f"Error SÍNCRONO al inicializar MongoDBChatMessageHistory para session {session_id}: {e}")
        return None

# Funciones auxiliares síncronas para pasar a to_thread
def _get_messages_sync(history: MongoDBChatMessageHistory, max_messages: Optional[int]) -> List[BaseMessage]:
     """Obtiene mensajes de forma síncrona."""
     messages = history.messages # Acceso a propiedad puede ser bloqueante
     if max_messages is not None and max_messages > 0:
          return messages[-max_messages:]
     elif max_messages == 0:
          return []
     else:
          return messages

def _add_messages_sync(history: MongoDBChatMessageHistory, human_message: str, ai_message: str) -> None:
     """Añade mensajes de forma síncrona."""
     history.add_user_message(human_message) # Puede ser bloqueante
     history.add_ai_message(ai_message) # Puede ser bloqueante


async def get_chat_history(session_id: str, max_messages: Optional[int] = 6) -> List[BaseMessage]:
    """
    Recupera los últimos mensajes del historial de chat para una sesión dada.
    Usa asyncio.to_thread para operaciones potencialmente bloqueantes.
    """
    logger.debug(f"Intentando obtener instancia de historial para session {session_id}")
    # La obtención de la instancia también podría ser bloqueante, la ejecutamos en thread
    history = await asyncio.to_thread(_get_mongo_history_sync, session_id)

    if history is None:
        # Si _get_mongo_history_sync devolvió None, es porque MONGO_URI no está
        # configurado o hubo un error grave en la inicialización. Ya se logueó.
        return []

    try:
        logger.debug(f"Recuperando mensajes de MongoDB (en thread) para session {session_id}...")
        # Ejecutar la obtención de mensajes en un hilo separado
        messages = await asyncio.to_thread(_get_messages_sync, history, max_messages)
        logger.debug(f"Recuperados {len(messages)} mensajes.")
        return messages
    # Capturar excepciones específicas de DB si es necesario y lanzar HistoryServiceError
    # except (ConnectionFailure, OperationFailure) as db_err:
    #      logger.error(f"Error de DB recuperando historial para {session_id}: {db_err}")
    #      raise HistoryServiceError(f"Error de base de datos al obtener historial: {db_err}") from db_err
    except Exception as e:
        logger.exception(f"Error inesperado recuperando historial para session {session_id}: {e}")
        # Lanzar excepción personalizada para que el pipeline la maneje si se desea
        # raise HistoryServiceError(f"Error inesperado obteniendo historial: {e}") from e
        return [] # O simplemente devolver lista vacía


async def add_chat_messages(session_id: str, human_message: str, ai_message: str) -> None:
    """
    Añade un par de mensajes al historial de chat de una sesión.
    Usa asyncio.to_thread y no propaga errores para no detener la respuesta al usuario.
    """
    logger.debug(f"Intentando obtener instancia de historial para añadir mensajes (session {session_id})...")
    # La obtención de la instancia podría ser bloqueante
    history = await asyncio.to_thread(_get_mongo_history_sync, session_id)

    if history is None:
        # MONGO_URI no configurado o error grave de inicialización. Ya se logueó.
        return

    try:
        logger.debug(f"Añadiendo mensajes a MongoDB (en thread) para session {session_id}...")
        # Ejecutar la adición de mensajes en un hilo separado
        await asyncio.to_thread(_add_messages_sync, history, human_message, ai_message)
        logger.debug(f"Mensajes añadidos a historial para session {session_id}.")
    # Capturar excepciones específicas de DB si es necesario
    # except (ConnectionFailure, OperationFailure) as db_err:
    #      logger.error(f"Error de DB añadiendo historial para {session_id}: {db_err}")
    except Exception as e:
        # Loguear el error pero NO relanzarlo para no interrumpir la respuesta al usuario
        logger.exception(f"Error inesperado añadiendo mensajes al historial para session {session_id}: {e}")
# --- Bloque para pruebas rápidas ---
if __name__ == "__main__":
    import asyncio

    async def test_history_service_main():
        logging.basicConfig(level=logging.DEBUG) # Usar DEBUG para ver detalles
        print("--- Probando History Service (Requiere .env con MONGO_URI válido) ---")

        # Intentar importar settings reales
        try:
            from app.core.config import settings
            if not settings.MONGO_URI:
                 print("MONGO_URI no configurado en .env. Saltando prueba.")
                 return
            if not LANGCHAIN_MONGO_AVAILABLE:
                 print("Dependencias Langchain/Mongo no disponibles. Saltando prueba.")
                 return
        except (ImportError, ValidationError):
             print("No se pudo cargar config real o faltan dependencias. Saltando prueba.")
             return

        test_session_id = f"test-session-main-{int(time.time())}" # Sesión única por prueba
        print(f"\nUsando session_id: {test_session_id}")

        # Limpiar historial previo (opcional)
        # ... (código de limpieza si es necesario) ...

        # Añadir mensajes
        print("\nAñadiendo mensajes...")
        start_add = time.perf_counter()
        await add_chat_messages(test_session_id, "Pregunta Usuario 1", "Respuesta AI 1")
        await add_chat_messages(test_session_id, "Pregunta Usuario 2", "Respuesta AI 2")
        add_time = time.perf_counter() - start_add
        print(f"Mensajes añadidos (Tiempo: {add_time:.4f}s)")


        # Recuperar historial (últimos 2 mensajes = 1 turno)
        print("\nRecuperando últimos 2 mensajes:")
        start_get = time.perf_counter()
        messages_short = await get_chat_history(test_session_id, max_messages=2)
        get_time_short = time.perf_counter() - start_get
        print(f"(Tiempo: {get_time_short:.4f}s)")
        if messages_short:
            for msg in messages_short:
                role = getattr(msg, 'type', 'unknown')
                content = getattr(msg, 'content', '')
                print(f"  [{role.upper()}]: {content}")
            assert len(messages_short) == 2
            # Verificar el orden y contenido (últimos 2)
            assert getattr(messages_short[0],'content', '') == "Pregunta Usuario 2"
            assert getattr(messages_short[1],'content', '') == "Respuesta AI 2"
        else:
            print("  No se recuperaron mensajes.")

        # Recuperar historial completo
        print("\nRecuperando historial completo:")
        start_get_all = time.perf_counter()
        all_messages = await get_chat_history(test_session_id, max_messages=None)
        get_time_all = time.perf_counter() - start_get_all
        print(f"(Tiempo: {get_time_all:.4f}s)")
        print(f"  Total mensajes recuperados: {len(all_messages)}")
        assert len(all_messages) >= 4 # Deberían ser 4 si la limpieza funcionó

        print("\nPrueba de History Service completada.")

    try:
        asyncio.run(test_history_service_main())
    except RuntimeError:
         print("Podría necesitarse un loop diferente si ya hay uno corriendo.")
    except Exception as e_main:
         print(f"Error ejecutando la prueba: {e_main}")