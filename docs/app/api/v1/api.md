# app/api/v1/api.py

## Descripción General
Router principal que agrupa todos los endpoints de la versión 1 de la API KellyBot. Funciona como:

- Punto central de montaje para routers específicos
- Gestor de prefijos comunes (/api/v1)
- Coordinador de tags para documentación OpenAPI

## Componentes Principales

### Router Principal
```python
router = APIRouter()
```
Configuración base:
- Sin prefijo global (se define al incluir en app/main.py)
- Tags agrupados por funcionalidad
- Manejo robusto de errores de importación

### Endpoints Incluidos

#### Chat Router
- **Path**: `/chat`
- **Tags**: ["Chat"]
- **Origen**: `app.api.v1.endpoints.chat`
- **Manejo de errores**:
  - Verifica disponibilidad antes de incluir
  - Registra errores críticos

## Flujo de Montaje
1. Intenta importar routers específicos
2. Verifica disponibilidad de módulos
3. Incluye routers disponibles:
   ```python
   router.include_router(chat.router, tags=["Chat"])
   ```
4. Maneja fallos de importación con logging

## Dependencias Clave

### Internas
- `app.api.v1.endpoints.chat`: Router de endpoints de chat
- `logging`: Sistema de registro de errores

### Externas
- `fastapi.APIRouter`: Clase base para creación de routers

## Diagrama de Routers
```
main.py (APIRouter)
└── /api/v1 (api.py router)
    └── /chat (chat.py router)
```

## Notas para Desarrolladores

### Para Añadir Nuevos Endpoints
1. Crear router en `app/api/v1/endpoints/`
2. Importar en api.py:
   ```python
   from app.api.v1.endpoints import nuevo_modulo
   ```
3. Incluir router principal:
   ```python
   router.include_router(nuevo_modulo.router, tags=["Nuevo"])
   ```

### Manejo de Errores
- Errores de importación se registran en logs
- El sistema continúa con routers disponibles

### Buenas Prácticas
- Usar tags consistentes
- Mantener prefijos en main.py
- Agrupar endpoints relacionados

## Relación con Otros Componentes
- **app/main.py**: Monta este router bajo /api/v1
- **app/api/v1/endpoints/**: Contiene routers específicos
- **app/core/config.py**: Configuración compartida