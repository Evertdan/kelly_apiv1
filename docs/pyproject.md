# kelly_api/pyproject.toml

## Descripción General
Archivo de configuración principal del proyecto que define:
- Metadatos del proyecto (nombre, versión, descripción)
- Dependencias principales y opcionales
- Configuración de herramientas de desarrollo (ruff, pytest, mypy)
- Sistema de construcción (setuptools)

## Secciones Principales

### [build-system]
Define el sistema de construcción del proyecto según PEP 517:
- `requires`: Dependencias necesarias para construir el paquete (setuptools)
- `build-backend`: Backend utilizado para la construcción (setuptools.build_meta)

### [project]
Contiene metadatos del proyecto según PEP 621:
- `name`: Nombre del paquete (kelly_api)
- `version`: Versión actual (0.1.0)
- `description`: Backend API para KellyBot usando FastAPI, RAG con Qdrant y LLMs
- `requires-python`: Versión mínima de Python requerida (3.10+)
- `license`: Tipo de licencia (MIT)
- `keywords`: Palabras clave para búsqueda
- `authors`: Lista de autores/maintainers
- `classifiers`: Clasificadores estándar de PyPI

### Dependencias Principales
Lista en `dependencies`:
- **API Web**: fastapi, uvicorn
- **Configuración**: pydantic-settings
- **Qdrant**: qdrant-client
- **Embeddings**: sentence-transformers, numpy, torch
- **LLM**: openai (compatible con DeepSeek)
- **Langchain**: core, mongodb, text-splitters
- **MongoDB**: pymongo

### Dependencias Opcionales
Definidas en `[project.optional-dependencies]`:
- `dev`: Herramientas para desarrollo (pytest, ruff, black, mypy, pre-commit)
- `test`: Dependencias para testing (pytest, httpx)

## Configuración de Herramientas

### [tool.ruff]
Configuración del linter Ruff:
- `line-length`: 88 caracteres
- `select`: Reglas activadas
- `exclude`: Directorios excluidos
- `isort`: Configuración para ordenar imports

### [tool.pytest.ini_options]
Configuración para pytest:
- `minversion`: 7.0
- `addopts`: Opciones por defecto (cobertura)
- `testpaths`: Directorio de tests
- `asyncio_mode`: auto (para pruebas async)

### [tool.mypy]
Configuración para el chequeador de tipos:
- `python_version`: 3.10
- `warn_return_any`: True
- `ignore_missing_imports`: True

## Notas para Desarrolladores
1. **Versión de Python**: El proyecto requiere Python 3.10 o superior
2. **Instalación con dependencias opcionales**:
   ```bash
   pip install -e ".[dev]"  # Para desarrollo
   pip install -e ".[test]" # Para testing
   ```
3. **Herramientas recomendadas**:
   - Ruff para linting
   - Black para formateo
   - mypy para chequeo de tipos
4. **Pruebas**: Ejecutar con `pytest` para obtener reporte de cobertura
5. **Construcción**: Usar `python -m build` para crear distribuciones

## Relación con Otros Archivos
- `README.md`: Documentación general referenciada en los metadatos
- `app/`: Paquete principal definido en [tool.setuptools]
- `tests/`: Directorio de pruebas configurado en pytest