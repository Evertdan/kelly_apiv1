# app/main.py

## Descripción General
Punto de entrada principal de la aplicación FastAPI para KellyBot. Responsable de:
- Inicialización y configuración de la aplicación
- Manejo del ciclo de vida (startup/shutdown)
- Montaje de routers principales
- Configuración de middlewares
- Servicio de favicon

## Componentes Principales

### Lifespan Manager
```python
@asynccontextmanager
async def lifespan(app_instance: FastAPI)
```
Maneja eventos de inicio/apagado de la aplicación:
1. **Startup**:
   - Registra configuración cargada
   - Verifica componentes esenciales
   - Muestra información de configuración
2. **Shutdown**:
   - Ejecuta limpieza antes de terminar

### Aplicación FastAPI
```python
app = FastAPI(...)
```
Configuración principal:
- **Título**: "KellyBot API"
- **Descripción**: API para procesar solicitudes de chat usando RAG con Qdrant y LLMs
- **Endpoints de documentación**:
  - `/api/v1/docs` - Interfaz Swagger
  - `/api/v1/redoc` - Documentación Redoc
- **Lifespan**: Usa el manager definido

### Endpoints Especiales

#### Favicon
```python
@app.get('/favicon.ico', include_in_schema=False)
async def favicon()
```
- Sirve el favicon desde `app/static/favicon.ico`
- Retorna 204 si no existe el archivo

## Routers Incluidos

### Status Router
- Path base: `/`
- Endpoints:
  - `/health` - Verificación de salud
  - `/` - Endpoint raíz

### API V1 Router
- Path base: `/api/v1`
- Contiene:
  - Endpoints de chat
  - Lógica principal de RAG

## Dependencias Clave

### Internas
- `app.core.config.settings` - Configuración central
- `app.api.v1.api.router` - Router principal API v1
- `app.api.v1.endpoints.status.router` - Router de estado

### Externas
- `fastapi` - Framework principal
- `logging` - Sistema de logs
- `pathlib.Path` - Manejo de rutas

## Flujo de Inicialización
1. Carga configuración desde `app.core.config`
2. Verifica imports esenciales
3. Configura logger
4. Crea aplicación FastAPI con lifespan
5. Monta routers:
   - Status en `/`
   - API v1 en `/api/v1`
6. Configura endpoint de favicon

## Notas para Desarrolladores

### Configuración Requerida
- Archivo `.env` con variables de entorno
- Archivo `app/core/config.py` válido
- Favicon en `app/static/favicon.ico`

### Middlewares Opcionales
Ejemplo CORS (descomentar en código):
```python
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Manejo de Errores
- Excepción global opcional (descomentar)
- Logs detallados durante inicialización

## Relación con Otros Componentes
- **app/core/config.py**: Provee configuración
- **app/api/v1/**: Contiene lógica de endpoints
- **app/static/**: Archivos estáticos
- **tests/**: Pruebas de integración