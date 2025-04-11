# app/core/config.py
# -*- coding: utf-8 -*-

"""
Configuración centralizada para la API KellyBot usando Pydantic Settings.
CORREGIDO: Eliminado validador 'normalize_literals' conflictivo.
"""

import logging
import sys
import os
from pathlib import Path
# CORRECCIÓN: Quitar imports no usados tras eliminar validador
from typing import Optional, Any, Literal, get_args # Quitar get_origin, Union si no se usan más

# Usar pydantic-settings y tipos/validadores de pydantic
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import (
    Field,
    HttpUrl,
    SecretStr,
    PositiveInt,
    FilePath,
    # Path NO se importa de pydantic
    field_validator, # Mantenido para validate_resolve_path
    model_validator, # Mantenido para check_overlap_less_than_size
    ValidationError,
    BeforeValidator # Mantenido para validate_resolve_path
)
from pydantic_core.core_schema import ValidationInfo

# --- Definir Logger a Nivel de Módulo ---
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
     handler = logging.StreamHandler(sys.stderr)
     formatter = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s')
     handler.setFormatter(formatter)
     logger.addHandler(handler)
     logger.setLevel(logging.WARNING)

# --- Definir Ruta Base del Proyecto ---
try:
    PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
except NameError:
    PROJECT_ROOT = Path.cwd()
    logger.warning(f"No se pudo determinar PROJECT_ROOT, usando CWD: {PROJECT_ROOT}")

# --- Tipos Específicos ---
QdrantDistance = Literal["Cosine", "Dot", "Euclid"]
EmbeddingDevice = Literal["auto", "cpu", "cuda"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# --- Helper para resolver rutas ---
def _resolve_path(value: Optional[str]) -> Optional[Path]:
     """Convierte string a Path y resuelve relativo a PROJECT_ROOT si no es absoluto."""
     if value:
         path = Path(value)
         if not path.is_absolute():
             if PROJECT_ROOT and PROJECT_ROOT.is_dir():
                return (PROJECT_ROOT / path).resolve()
             else:
                 logger.warning(f"PROJECT_ROOT no válido, no se puede resolver ruta relativa: {value}")
                 return path
         return path
     return None

# --- Clase Principal de Settings ---
class Settings(BaseSettings):
    """Carga y valida las configuraciones para la API KellyBot."""

    # --- API Server ---
    API_HOST: str = Field(default="0.0.0.0", alias='API_HOST')
    API_PORT: int = Field(default=8000, alias='API_PORT')
    LOG_LEVEL: LogLevel = Field(default='INFO', alias='LOG_LEVEL')
    API_LOG_FILE: Optional[Path] = Field(default=None, alias='API_LOG_FILE')
    API_ACCESS_KEY: SecretStr = Field(..., alias='API_ACCESS_KEY')
    API_RELOAD: bool = Field(default=False, alias='API_RELOAD')

    # --- LLM ---
    DEEPSEEK_API_KEY: SecretStr = Field(..., alias='DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL: HttpUrl = Field(default="https://api.deepseek.com/", alias='DEEPSEEK_BASE_URL')
    DEEPSEEK_MODEL_NAME: str = Field(default="deepseek-chat", alias='DEEPSEEK_MODEL_NAME')
    LLM_REQUEST_TIMEOUT: float = Field(default=120.0, alias='LLM_REQUEST_TIMEOUT')

    # --- Qdrant ---
    QDRANT_URL: HttpUrl = Field(..., alias='QDRANT_URL')
    QDRANT_API_KEY: Optional[SecretStr] = Field(default=None, alias='QDRANT_API_KEY')
    QDRANT_COLLECTION_NAME: str = Field(default="kellybot-docs-v1", alias='QDRANT_COLLECTION_NAME')
    DISTANCE_METRIC: QdrantDistance = Field(default="Cosine", alias='DISTANCE_METRIC')
    VECTOR_DIMENSION: PositiveInt = Field(..., alias='VECTOR_DIMENSION')

    # --- Embeddings ---
    EMBEDDING_MODEL_NAME: str = Field(..., alias='EMBEDDING_MODEL_NAME')
    EMBEDDING_DEVICE: EmbeddingDevice = Field(default="auto", alias='EMBEDDING_DEVICE')

    # --- MongoDB (Opcional) ---
    MONGO_URI: Optional[SecretStr] = Field(default=None, alias='MONGO_URI')
    MONGO_DATABASE_NAME: str = Field(default="kellybot_chat", alias='MONGO_DATABASE_NAME')
    MONGO_COLLECTION_NAME: str = Field(default="chat_histories", alias='MONGO_COLLECTION_NAME')

    # --- Contexto Prioritario (Opcional) ---
    PRIORITY_CONTEXT_FILE_PATH: Optional[Path] = Field(
        default=PROJECT_ROOT / "data" / "priority_context.json",
        alias='PRIORITY_CONTEXT_FILE_PATH'
    )
    PRIORITY_SIMILARITY_THRESHOLD: float = Field(
         default=0.85, alias='PRIORITY_SIMILARITY_THRESHOLD', ge=0.0, le=1.0
    )

    # --- RAG (Opcional) ---
    CHUNK_SIZE: PositiveInt = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=150, ge=0)
    RAG_TOP_K: PositiveInt = Field(default=3, alias='RAG_TOP_K')
    RAG_MAX_CONTEXT_TOKENS: PositiveInt = Field(default=3000, alias='RAG_MAX_CONTEXT_TOKENS')

    # --- Configuración del Modelo Pydantic Settings ---
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False, # Importante para validar Literals sin importar mayús/minús
    )

    # --- Validadores ---
    # Validador para rutas (se ejecuta ANTES de la validación de tipo Path)
    @field_validator('API_LOG_FILE', 'PRIORITY_CONTEXT_FILE_PATH', mode='before')
    @classmethod
    def validate_resolve_path(cls, value: Any) -> Optional[Path]:
        return _resolve_path(value)

    # --- ELIMINADO: Validador normalize_literals ---
    # Se confía ahora en case_sensitive=False y la validación de Literal de Pydantic.
    # Asegúrate de usar valores exactos (ej. Cosine, Dot, Euclid) para DISTANCE_METRIC en .env.

    # Validador para overlap < size (usa @model_validator)
    @model_validator(mode='after')
    def check_overlap_less_than_size(self) -> 'Settings':
        # (Código sin cambios)
        chunk_size = getattr(self, 'CHUNK_SIZE', None)
        chunk_overlap = getattr(self, 'CHUNK_OVERLAP', None)
        if isinstance(chunk_size, int) and isinstance(chunk_overlap, int):
             if chunk_overlap >= chunk_size:
                  raise ValueError(f"CHUNK_OVERLAP ({chunk_overlap}) debe ser < CHUNK_SIZE ({chunk_size})")
        return self

# --- Instancia Global de Configuración ---
# (Sin cambios aquí)
try:
    settings = Settings()
except ValidationError as e:
    # Configurar logging básico si falla la instancia principal
    logging.basicConfig(level='CRITICAL', format='%(name)s [%(levelname)s] - %(message)s')
    logger = logging.getLogger("config_loader") # Usar logger específico para este error
    logger.critical("!!! Error CRÍTICO de Validación de Configuración !!!")
    logger.critical(f"Revisa tu archivo .env ({PROJECT_ROOT / '.env'}):")
    logger.critical(e)
    sys.exit("Error fatal de configuración.")
except Exception as e:
    logging.basicConfig(level='CRITICAL', format='%(name)s [%(levelname)s] - %(message)s')
    logger = logging.getLogger("config_loader")
    logger.critical(f"!!! Error CRÍTICO Inesperado al Cargar Configuración !!!: {e}", exc_info=True)
    sys.exit("Error fatal inesperado.")


# --- Bloque de prueba opcional ---
if __name__ == "__main__":
    # ... (sin cambios) ...
    print("--- Configuración Cargada (Modo Prueba Directa) ---")
    # ...