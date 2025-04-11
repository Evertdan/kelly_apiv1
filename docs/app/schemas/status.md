# app/schemas/status.py

## Descripción General
Módulo que define el esquema Pydantic para:

- Respuestas de endpoints de estado/salud
- Monitoreo del servicio KellyBot API
- Verificación de disponibilidad

## Esquema Principal

### StatusResponse
```python
class StatusResponse(BaseModel)
```
Modelo estándar para respuestas de estado del sistema.

**Campos:**
- `status`: str (default: "ok")
  - Estado del servicio (ok/error)
- `message`: str (default: "Servicio operativo")
  - Mensaje descriptivo del estado

**Ejemplos JSON:**
```json
{
  "status": "ok",
  "message": "KellyBot API está operativa"
}
```

```json
{
  "status": "ok", 
  "message": "API healthy"
}
```

## Uso en Endpoints

### Endpoints Relacionados
- `GET /`: Estado general
- `GET /health`: Salud del servicio

**Flujo:**
1. Endpoint verifica estado interno
2. Construye respuesta con StatusResponse
3. Personaliza mensaje según contexto

## Configuraciones

### Documentación Automática
- Ejemplos embebidos en `model_config`
- Compatible con OpenAPI/Swagger

## Dependencias
- `pydantic.BaseModel`: Base para el esquema
- `pydantic.Field`: Para definición de campos

## Consideraciones

### Extensión
- Añadir campos como:
  - `version`: Versión de la API
  - `uptime`: Tiempo de actividad
  - `dependencies`: Estado de dependencias

### Pruebas
- Verificar respuestas con diferentes estados
- Validar serialización/deserialización