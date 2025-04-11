# app/api/deps.py

## Descripción General
Archivo de dependencias reutilizables para inyección en endpoints FastAPI. Proporciona funciones que pueden ser inyectadas automáticamente por FastAPI para manejar tareas comunes como:

- Autenticación mediante API keys
- Obtención de configuración
- Manejo de clientes externos

## Funciones Principales

### get_api_key
```python
async def get_api_key(api_key_header: Optional[str] = Depends(API_KEY_HEADER)) -> str
```
**Propósito**:  
Valida API keys para autenticación en endpoints protegidos.

**Flujo de trabajo**:
1. Obtiene el token del header (API_KEY_HEADER)
2. Delega validación a `verify_api_key` en core.security
3. Maneja posibles errores:
   - 401 si la clave es inválida
   - 500 si hay errores internos

**Parámetros**:
- `api_key_header`: Token extraído del header Authorization

**Retorna**:
- Clave API validada (str)

**Excepciones**:
- HTTPException(401): Autenticación fallida
- HTTPException(500): Error interno

## Dependencias y Configuración

### Dependencias Externas
- `app.core.security`: Proporciona:
  - `API_KEY_HEADER`: Esquema de autenticación
  - `verify_api_key`: Función de validación
- `app.core.config`: Configuración global

### Mecanismos de Fallback
Si falla la importación de módulos de seguridad:
1. Crea funciones dummy
2. Registra error crítico en logs
3. Devuelve 500 en validaciones

## Ejemplos de Uso
```python
from app.api.deps import get_api_key

@app.get("/protected")
async def protected_endpoint(
    api_key: str = Depends(get_api_key)  # Inyección automática
):
    # Lógica del endpoint
```

## Notas para Desarrolladores

### Seguridad
- Siempre usar `get_api_key` en endpoints protegidos
- Las claves se validan contra el módulo security.py
- Errores se registran con nivel CRITICAL

### Extensibilidad
Para añadir nuevas dependencias:
1. Definir función con parámetro `= Depends()`
2. Manejar errores adecuadamente
3. Documentar con docstring detallado

### Dependencias Sugeridas
Ejemplos comentados en el código:
- `get_settings`: Para acceso a configuración
- `get_qdrant_client`: Para clientes externos

## Relación con Otros Componentes
- **app/core/security.py**: Lógica de autenticación
- **app/core/config.py**: Configuración global
- **app/api/v1/**: Endpoints que usan estas dependencias
- **tests/api/**: Pruebas de integración