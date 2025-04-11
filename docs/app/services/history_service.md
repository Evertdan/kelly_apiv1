# app/services/history_service.py

## Descripción General
Servicio central para la gestión del historial de conversaciones en MongoDB. Proporciona:

- Almacenamiento persistente de diálogos
- Recuperación eficiente del contexto histórico
- Integración con el ecosistema LangChain
- Operaciones asíncronas no bloqueantes

**Responsabilidad Principal:**  
Mantener el estado conversacional entre interacciones para permitir continuidad en los diálogos.

**Arquitectura:**  
Se ubica en la capa de servicios, interactuando con:
- API endpoints (para recuperación/almacenamiento)
- Configuración central (para conexión a MongoDB)
- Servicios de LLM (para proporcionar contexto histórico)

## Funciones Principales

### `_get_mongo_history_sync(session_id: str) -> Optional[MongoDBChatMessageHistory]`
```python
def _get_mongo_history_sync(session_id: str)
```
Función interna síncrona para obtener instancia de historial MongoDB.

**Parámetros:**
- `session_id`: Identificador único de conversación (UUID)

**Comportamiento:**
1. Verifica disponibilidad de dependencias
2. Obtiene configuración de conexión
3. Crea instancia de MongoDBChatMessageHistory
4. Maneja errores de conexión

**Retorna:**  
Instancia configurada o None en caso de error

---

### `get_chat_history(session_id: str, max_messages: Optional[int] = 6) -> List[BaseMessage]`
```python
async def get_chat_history(session_id: str, max_messages: int = 6)
```
Recupera mensajes históricos de forma asíncrona.

**Parámetros:**
- `session_id`: ID de sesión existente
- `max_messages`: Límite de mensajes (default=6)

**Flujo:**
1. Obtiene instancia de historial (en thread separado)
2. Recupera mensajes (en thread separado)
3. Aplica filtro por cantidad
4. Retorna mensajes formateados

**Retorna:**  
Lista de objetos BaseMessage ordenados cronológicamente

---

### `add_chat_messages(session_id: str, human_message: str, ai_message: str) -> None`
```python
async def add_chat_messages(session_id: str, human_message: str, ai_message: str)
```
Almacena nuevo turno conversacional.

**Parámetros:**
- `session_id`: ID de sesión (existente o nueva)
- `human_message`: Texto de entrada del usuario
- `ai_message`: Respuesta generada por el sistema

**Consideraciones:**
- Ejecución no bloqueante
- Atomicidad en el almacenamiento
- Manejo silencioso de errores

## Dependencias Clave

### Internas
- `app.core.config`: Para parámetros de conexión
- `app.core.exceptions`: Para errores personalizados

### Externas
- `langchain-mongodb`: Integración con MongoDB
- `pymongo`: Controlador de base de datos
- `asyncio`: Para operaciones no bloqueantes

## Configuración Requerida

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| MONGO_URI | Cadena de conexión | `mongodb+srv://user:pass@cluster.mongodb.net/db` |
| MONGO_DATABASE_NAME | Nombre de BD | `kelly_chat` |
| MONGO_COLLECTION_NAME | Colección para historiales | `conversations` |

## Notas Técnicas

### Patrones de Diseño
- **Singleton implícito:** Conexión a MongoDB manejada por LangChain
- **Async Wrapper:** Adaptador para operaciones síncronas

### Consideraciones de Seguridad
- Validación de session_id
- Cifrado en tránsito (TLS)
- Rotación de credenciales

### Puntos de Extensión
1. Adición de metadatos a mensajes
2. Soporte para múltiples backends de almacenamiento
3. Compresión de historiales largos

## Archivos Relacionados
- `tests/api/endpoints/test_chat.py`: Pruebas de integración
- `app/api/v1/endpoints/chat.py`: Consumidor principal
- `app/core/config.py`: Configuración de conexión