# app/services/rag_pipeline.py
# -*- coding: utf-8 -*-

"""
Módulo que orquesta el pipeline de Retrieval-Augmented Generation (RAG).
Combina contexto prioritario, historial, resultados de Qdrant y un LLM
para generar respuestas contextualizadas, con postprocesado.
"""

import logging
import re # Para el postprocesado con regex
import time # Podría usarse para medir tiempos internos
import asyncio # Para llamadas asíncronas y to_thread (si se usa en servicios)
from typing import Dict, Any, List, Optional, Tuple

# --- Importar configuración (o usar Dummy) ---
try:
    from app.core.config import settings
    CONFIG_LOADED = True
except ImportError:
    print("[ERROR rag_pipeline.py] No se pudo importar 'settings'. Usando defaults dummy.")
    class DummySettings:
        RAG_TOP_K: int = 3
        RAG_MAX_CONTEXT_TOKENS: int = 3000
        vector_dimension: int = 768
        embedding_model_name: str = "dummy-model"
        MONGO_URI: Optional[str] = None
        RAG_HISTORY_MESSAGES: int = 6 # Añadir si se usa getattr abajo
    settings = DummySettings() # type: ignore
    CONFIG_LOADED = False
except Exception as config_err:
     print(f"[ERROR rag_pipeline.py] Error al importar/validar 'settings': {config_err}. Usando defaults dummy.")
     # ... (Definir DummySettings como antes) ...
     settings = DummySettings() # type: ignore
     CONFIG_LOADED = False

# --- Importar schemas (o usar Dummy) ---
try:
    from app.schemas.chat import SourceInfo
    SCHEMA_AVAILABLE = True
except ImportError:
    print("[ERROR rag_pipeline.py] No se pudo importar 'SourceInfo'. Usando dummy.")
    SourceInfo = Dict # type: ignore
    SCHEMA_AVAILABLE = False

# --- Importar servicios (o usar Dummy) ---
try:
    from app.services import (
        embedding_service,
        qdrant_service,
        llm_service,
        priority_context_service,
        history_service
    )
    # Importar tipos de mensajes de Langchain si history_service los devuelve
    from langchain_core.messages import BaseMessage
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR rag_pipeline.py] Fallo al importar servicios: {e}. Usando dummies.")
    SERVICES_AVAILABLE = False
    # Definir dummies
    class DummyService:
        async def embed_query(self, text: str) -> List[float]: return [0.1] * settings.vector_dimension
        async def search_documents(self, vector: List[float], top_k: int) -> List[Dict]: return []
        async def call_llm(self, messages: List[Dict]) -> Optional[str]: return "Respuesta dummy: LLM no implementado."
        async def find_priority_answer(self, query: str) -> Optional[str]: return None
        async def get_chat_history(self, session_id: str, max_messages: int) -> List: return []
        async def add_chat_messages(self, session_id: str, human_msg: str, ai_msg: str) -> None: pass
    embedding_service = DummyService(); qdrant_service = DummyService(); llm_service = DummyService()
    priority_context_service = DummyService(); history_service = DummyService()
    BaseMessage = Dict # type: ignore


logger = logging.getLogger(__name__)

# --- Ajustes de personalidad y respuestas ---
# Prompt del Sistema con Personalidad Mejorada
RAG_SYSTEM_PROMPT_TEMPLATE = """
Eres Kely, la asistente virtual de Computo Contable Soft. Tu misión es **ayudar a contadores, personal administrativo y usuarios con conocimientos tecnológicos básicos** a resolver dudas sobre los productos MiAdminXML y MiExpedienteContable.

**Estilo de comunicación**:
1. Habla con calidez y cercanía. Usa saludos como “¡Hola!” o “Buen día”.
2. Sé muy paciente y comprensiva. Asume que el usuario puede tener poca experiencia técnica.
3. Ofrece la información más relevante al inicio, evitando rodeos.
4. Mantén un estilo de marca coherente: formalidad media con un toque cercano. Evita jerga innecesaria, pero sé precisa.
5. Emplea sencillez en tus explicaciones. Cuando uses términos técnicos (CFDI, SAT, etc.), define brevemente si es pertinente.
6. Si no puedes responder con la información disponible, no te excuses; di lo que sí sabes y sugiere llamar a Soporte (7712850074).
7. Mantén la calidez sin frases robóticas repetitivas. Varía tus expresiones.
8. Cuando sea útil, brinda pequeños ejemplos para ilustrar la idea (por ejemplo, cómo subir un XML).
9. Busca un flujo natural: si detectas que el usuario está atascado, sugiere preguntas de aclaración (sin obligar).
10. Estructura las respuestas con pasos enumerados o viñetas si explicas un procedimiento.

**EVITA:**
- Decir que es “un recurso que muestra un icono” o “indica el total de XML”.
- Usar formato Markdown (negritas, asteriscos), emoticones o líneas sobre “iconos en el escritorio”.
- Pedir disculpas (e.g., “lo siento”, “lamentablemente”) a menos que sea estrictamente necesario por un fallo.

**Reglas de Contenido**:
- Basa tu respuesta ESTRICTA y **ÚNICAMENTE** en la información del contexto (historial y documentos).
- NO inventes nada. No añadas información que no aparezca en el contexto.
- Si el contexto no contiene la respuesta, usa la respuesta predefinida para ese caso y redirige a soporte (teléfono: 7712850074).

{history_section}
Contexto Recuperado de Documentos:
---
{context}
---

**Pregunta del Usuario**: {question}

Por favor, formula tu **respuesta final** de manera cordial, clara y amigable, usando solamente la información anterior y siguiendo las pautas de estilo y contenido. Si no encuentras algo en el contexto, usa la respuesta predefinida.
"""

# Mensaje genérico en caso de error grave
DEFAULT_ERROR_MESSAGE = (
    "Estoy teniendo dificultades para procesar tu solicitud en este momento. "
    "Por favor, intenta de nuevo más tarde o comunícate al 7712850074."
)

# Mensaje si NO hay contexto relevante
NO_CONTEXT_ANSWER = (
    "Para más detalles o ayuda específica sobre eso, te recomiendo comunicarte "
    "a Atención a Clientes al 7712850074, donde un especialista podrá asistirte."
)

# --- Funciones Auxiliares ---

def _format_context_from_qdrant(search_results: List[Dict], max_length: int) -> Tuple[str, List[SourceInfo]]:
    """
    Formatea los resultados de Qdrant en un string de contexto y una lista de SourceInfo.
    """
    # (Sin cambios respecto a la versión anterior)
    context_parts = []
    sources_info = []
    current_length = 0
    seen_ids = set()
    if not search_results: return "", []
    logger.debug(f"Formateando contexto Qdrant ({len(search_results)} resultados, max_len={max_length})...")
    for result in search_results:
        try:
            payload = result.get("payload", {})
            score = result.get("score")
            source_id = payload.get("original_faq_id")
            if not source_id or source_id in seen_ids: continue
            content_to_add = payload.get("answer_full") or "\n".join(payload.get("answer_chunks", [])) or payload.get("question")
            if not content_to_add or not isinstance(content_to_add, str) or not content_to_add.strip(): continue
            content_to_add = content_to_add.strip()
            formatted_part = f"Fuente ID: {source_id}\nContenido: {content_to_add}\n---\n"
            part_length = len(formatted_part)
            if current_length + part_length <= max_length:
                context_parts.append(formatted_part)
                current_length += part_length
                if SCHEMA_AVAILABLE: # Crear objeto Pydantic si es posible
                     sources_info.append(SourceInfo(source_id=source_id, score=score))
                else: # Usar diccionario como fallback
                     sources_info.append({"source_id": source_id, "score": score}) # type: ignore
                seen_ids.add(source_id)
                logger.debug(f"Añadido contexto Qdrant ID {source_id} (Score: {score:.4f}).")
            else: break
        except Exception as e: logger.warning(f"Error procesando resultado Qdrant {result.get('id', 'N/A')}: {e}", exc_info=False); continue
    if not context_parts: logger.warning("No se pudo construir contexto desde Qdrant."); return "", []
    return "".join(context_parts).strip(), sources_info

def _format_history_for_prompt(history_messages: List[BaseMessage]) -> str:
    """Formatea la lista de mensajes del historial en un string para el prompt."""
    # (Sin cambios respecto a la versión anterior)
    if not history_messages: return ""
    formatted = []
    for msg in history_messages:
        # Usar getattr para acceso seguro a atributos
        role = getattr(msg, 'type', 'unknown').replace('human', 'Usuario').replace('ai', 'Asistente').capitalize()
        content = getattr(msg, 'content', '')
        if role != 'Unknown' and content: formatted.append(f"{role}: {content}")
    if not formatted: return ""
    return "Historial Reciente de la Conversación:\n---\n" + "\n".join(formatted) + "\n---"

def _post_process_llm_answer(llm_answer: str) -> str:
    """
    Limpia la respuesta del LLM quitando formatos y frases no deseadas.
    """
    if not llm_answer: return ""
    text = llm_answer
    # 1. Eliminar Markdown básico (simplificado)
    text = re.sub(r"[*_`#]+", "", text) # Quita *, _, `, #
    # 2. Eliminar emoticonos (usando un rango Unicode más amplio)
    try:
        # Python 3.7+
        emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F" # emoticons
                               u"\U0001F300-\U0001F5FF" # symbols & pictographs
                               u"\U0001F680-\U0001F6FF" # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF" # flags (iOS)
                               u"\U00002702-\U000027B0" # Dingbats
                               u"\U000024C2-\U0001F251"
                               "]+", flags=re.UNICODE)
        text = emoji_pattern.sub(r'', text)
    except re.error: # En caso de error con regex Unicode
        text = text.replace("😊", "").replace("💙", "") # Fallback simple
    # 3. Eliminar líneas con contenido no deseado (más específico)
    lines = text.splitlines()
    filtered_lines = []
    phrases_to_avoid = ["recurso que muestra", "indica el total", "icono en el escritorio", "lo siento", "lamentablemente", "disculpa"]
    for line in lines:
        lower_line = line.lower().strip()
        # Evitar líneas si contienen frases completas no deseadas O si son solo la disculpa
        should_avoid = False
        for phrase in phrases_to_avoid:
             # Evitar si la línea ES la frase de disculpa o EMPIEZA con ella de forma común
             if lower_line == phrase or lower_line.startswith(phrase + ",") or lower_line.startswith(phrase + "."):
                  should_avoid = True
                  break
             # Evitar frases más específicas (ajustar según necesidad)
             if phrase in ["recurso que muestra", "indica el total", "icono en el escritorio"] and phrase in lower_line:
                  should_avoid = True
                  break
        if not should_avoid and line.strip(): # Añadir solo si no se evita y no está vacía
             filtered_lines.append(line.strip())
    cleaned_text = "\n".join(filtered_lines)
    # 4. Quitar espacios/saltos de línea excesivos
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text) # Máximo 2 saltos seguidos
    cleaned_text = re.sub(r' {2,}', ' ', cleaned_text) # Máximo 1 espacio seguido
    return cleaned_text.strip()

# --- Función Principal del Pipeline RAG ---

async def generate_response(question: str, session_id: str) -> Dict[str, Any]:
    """
    Orquesta el pipeline RAG completo y aplica postprocesado a la respuesta.
    """
    if not SERVICES_AVAILABLE:
        logger.critical("Servicios RAG no disponibles (importación falló).")
        return {"answer": DEFAULT_ERROR_MESSAGE, "sources": []}

    logger.info(f"Pipeline RAG iniciado para session_id: {session_id}")
    final_answer: str = DEFAULT_ERROR_MESSAGE # Default en caso de error total
    final_sources: List[SourceInfo] = []

    try: # Envolver todo el flujo en un try por si acaso
        # 1. Contexto Prioritario
        logger.debug("Buscando en contexto prioritario...")
        priority_answer = await priority_context_service.find_priority_answer(question)
        if priority_answer:
            logger.info("Respuesta encontrada en contexto prioritario.")
            clean_priority_answer = _post_process_llm_answer(priority_answer) # Limpiar también
            await history_service.add_chat_messages(session_id, question, clean_priority_answer)
            return {
                "answer": clean_priority_answer,
                "sources": [SourceInfo(source_id="priority_context", score=1.0)] if SCHEMA_AVAILABLE else [{"source_id":"priority_context", "score":1.0}]
            }
        logger.debug("No se encontró respuesta prioritaria.")

        # 2. Historial
        formatted_history = ""
        if settings.MONGO_URI:
            logger.debug("Recuperando historial de chat...")
            try:
                max_hist = getattr(settings, 'RAG_HISTORY_MESSAGES', 6)
                history_messages = await history_service.get_chat_history(session_id, max_messages=max_hist)
                formatted_history = _format_history_for_prompt(history_messages)
            except Exception as e_hist: logger.error(f"Error recuperando historial: {e_hist}", exc_info=False)
        else: logger.debug("Historial no configurado.")

        # 3. Embedding
        logger.debug(f"Generando embedding para query...")
        query_vector = await embedding_service.embed_query(question)
        logger.debug("Embedding generado.")

        # 4. Búsqueda Qdrant
        logger.debug(f"Buscando en Qdrant (top_k={settings.RAG_TOP_K})...")
        search_results = await qdrant_service.search_documents(vector=query_vector, top_k=settings.RAG_TOP_K)
        logger.debug(f"Qdrant devolvió {len(search_results)} resultados.")

        # 5. Formatear Contexto Qdrant
        approx_prompt_overhead = len(RAG_SYSTEM_PROMPT_TEMPLATE) + len(question) + len(formatted_history) + 500
        max_context_len_chars = settings.RAG_MAX_CONTEXT_TOKENS * 3
        available_qdrant_context_len = max(0, max_context_len_chars - approx_prompt_overhead)
        qdrant_context_str, sources_list = _format_context_from_qdrant(search_results, max_length=available_qdrant_context_len)
        final_sources = sources_list

        # 6. Fallback si no hay contexto
        if not qdrant_context_str and not formatted_history:
             logger.warning("Sin contexto Qdrant ni historial. Usando NO_CONTEXT_ANSWER.")
             final_answer = NO_CONTEXT_ANSWER
             await history_service.add_chat_messages(session_id, question, final_answer)
             return {"answer": final_answer, "sources": []}

        # 7. Llamada al LLM
        logger.debug("Construyendo prompt y llamando al LLM generativo...")
        final_llm_context = qdrant_context_str if qdrant_context_str else "No se encontró información específica en documentos."
        history_section_for_prompt = formatted_history if formatted_history else "# No hay historial relevante"
        system_prompt_content = RAG_SYSTEM_PROMPT_TEMPLATE.format(
             history_section=history_section_for_prompt,
             context=final_llm_context,
             question=question
        )
        messages_for_llm = [{"role": "system", "content": system_prompt_content}]

        llm_raw_answer = await llm_service.call_llm(messages=messages_for_llm)

        if not llm_raw_answer:
             logger.error("LLM devolvió respuesta vacía o None.")
             final_answer = DEFAULT_ERROR_MESSAGE
        else:
             # 8. Postprocesar respuesta LLM
             logger.debug("Postprocesando respuesta LLM...")
             final_answer = _post_process_llm_answer(llm_raw_answer)
             logger.info(f"Respuesta RAG generada y limpiada para session_id: {session_id}")

    except Exception as e:
        # Capturar cualquier error inesperado durante el pipeline principal
        logger.exception(f"Error fatal inesperado en RAG pipeline para session {session_id}: {e}")
        final_answer = DEFAULT_ERROR_MESSAGE # Usar error genérico
        # Las fuentes podrían haberse recuperado antes del error, las mantenemos si existen
        final_sources = locals().get("final_sources", []) # Intentar mantener fuentes si ya se obtuvieron

    # 9. Guardar en historial (incluso si la respuesta es un error manejado)
    try:
         # Usar final_answer que contiene la respuesta limpia o el mensaje de error
         await history_service.add_chat_messages(session_id, question, final_answer)
    except Exception as e_hist_save:
         logger.error(f"Error guardando en historial para session {session_id} tras RAG: {e_hist_save}", exc_info=False)


    # 10. Retornar
    return {
        "answer": final_answer,
        "sources": final_sources
    }

# --- Bloque de pruebas rápidas ---
if __name__ == "__main__":
    import asyncio

    async def test_rag_pipeline():
        logging.basicConfig(level=logging.DEBUG)
        print("--- Prueba de RAG Pipeline con personalidad y postprocesado ---")
        # Podrías simular llamadas de prueba a generate_response
        print("Usa pruebas más formales con pytest.")

    try:
        asyncio.run(test_rag_pipeline())
    except RuntimeError:
        print("Podrías necesitar un loop diferente si ya hay uno corriendo.")
    except Exception as e_main:
        print(f"Error ejecutando la prueba: {e_main}")
    print("Script RAG Pipeline listo.")
