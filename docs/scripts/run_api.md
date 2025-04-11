# scripts/run_api.py

## Descripción General
Punto de entrada principal para iniciar el servidor FastAPI usando Uvicorn. Este script maneja la configuración inicial, validaciones y el lanzamiento del servidor web.

**Responsabilidad Principal:**  
Iniciar el servidor API con la configuración adecuada y manejar errores críticos durante el arranque.

**Arquitectura:**  
Componente clave del sistema que interactúa con:
- `app.core.config.settings`: Para obtener configuración
- `app.main:app`: Aplicación FastAPI principal
- Uvicorn: Servidor ASGI

## Funciones Principales

### `start_server()`
```python
def start_server():
    """Inicia el servidor Uvicorn con la configuración cargada."""
```

**Flujo de Ejecución:**
1. Verifica que la configuración se cargó correctamente
2. Obtiene parámetros de configuración:
   - Host y puerto
   - Nivel de logging  
   - Modo recarga automática
3. Inicia Uvicorn con la configuración

**Parámetros:**  
No recibe parámetros directos, usa configuración desde `settings`.

**Manejo de Errores:**
- Configuración faltante
- Errores de importación
- Fallos al iniciar Uvicorn

## Configuración Requerida

| Variable | Tipo | Descripción | Valor por Defecto |
|----------|------|-------------|-------------------|
| `API_HOST` | str | Host para bind | `localhost` |
| `API_PORT` | int | Puerto HTTP | `8000` |
| `LOG_LEVEL` | str | Nivel de logging | `info` |
| `API_RELOAD` | bool | Recarga automática | `False` |

## Dependencias Clave

### Internas
- `app.core.config.settings`: Configuración centralizada
- `app.main:app`: Aplicación FastAPI

### Externas  
- `uvicorn`: Servidor ASGI
- `pydantic`: Validación de configuración

## Ejemplo de Uso

```bash
# Desde la raíz del proyecto
python scripts/run_api.py

# Con variables de entorno personalizadas
API_HOST=0.0.0.0 API_PORT=8080 python scripts/run_api.py
```

## Diagrama de Flujo

```mermaid
sequenceDiagram
    Usuario->>+run_api.py: Ejecuta script
    run_api.py->>+settings: Carga configuración
    alt Configuración válida
        settings-->>-run_api.py: Parámetros
        run_api.py->>+uvicorn: Inicia servidor
        uvicorn->>+FastAPI: Monta aplicación
    else Error configuración
        settings--x-run_api.py: Error
        run_api.py->>Usuario: Mensaje error
    end
```

## Consideraciones Importantes

### Seguridad
- No exponer en `0.0.0.0` en producción sin firewall
- Validar variables de entorno sensibles

### Rendimiento
- Modo recarga solo para desarrollo
- Ajustar nivel de log en producción

### Mantenimiento
- Actualizar según cambios en:
  - Estructura de la app FastAPI
  - Configuración de Uvicorn
  - Variables de entorno requeridas

## Posibles Mejoras
1. Soporte para SSL/TLS
2. Opciones avanzadas de Uvicorn
3. Health checks iniciales
4. Validación de dependencias