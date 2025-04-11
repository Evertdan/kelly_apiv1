# tests/core/test_config.py
# -*- coding: utf-8 -*-

"""
Pruebas unitarias para el módulo de configuración de Kelly API (app.core.config).
Verifica la carga desde el entorno, valores por defecto, tipos y validaciones.
"""

import os
import pytest
import shutil
from pathlib import Path
from pydantic import ValidationError, SecretStr, HttpUrl
from pydantic_settings import SettingsConfigDict

# Importar la CLASE Settings y PROJECT_ROOT desde el módulo config
# Asumiendo que pytest corre desde la raíz y app está en PYTHONPATH
try:
    from app.core.config import Settings, PROJECT_ROOT, QdrantDistance, EmbeddingDevice, LogLevel
    CONFIG_IMPORTED = True
except ImportError:
    pytest.fail("No se pudo importar 'Settings' desde 'app.core.config'.", pytrace=False)
    CONFIG_IMPORTED = False # Para satisfacer linters en el resto del archivo


# --- Pruebas de Configuración ---

# Asegurarse de que el módulo se importó antes de correr las pruebas
pytestmark = pytest.mark.skipif(not CONFIG_IMPORTED, reason="No se pudo importar app.core.config")


def test_project_root_detection():
    """Verifica que PROJECT_ROOT apunte al directorio raíz correcto."""
    assert isinstance(PROJECT_ROOT, Path)
    assert (PROJECT_ROOT / "pyproject.toml").is_file(), f"PROJECT_ROOT ({PROJECT_ROOT}) no parece la raíz."
    assert (PROJECT_ROOT / "app").is_dir(), f"No se encontró 'app' en PROJECT_ROOT ({PROJECT_ROOT})."


def test_missing_required_env_variables(monkeypatch):
    """Verifica que falle si faltan variables requeridas sin .env ni env vars."""
    # Eliminar todas las variables requeridas del entorno
    required_vars = ["API_ACCESS_KEY", "DEEPSEEK_API_KEY", "QDRANT_URL", "VECTOR_DIMENSION", "EMBEDDING_MODEL_NAME"]
    for var in required_vars:
        monkeypatch.delenv(var, raising=False)

    # Intentar instanciar Settings forzando a no leer ningún archivo .env
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None) # _env_file=None evita leer cualquier .env

    # Verificar que el error mencione al menos algunas de las variables faltantes
    error_str = str(excinfo.value).lower()
    assert "api_access_key" in error_str
    assert "deepseek_api_key" in error_str
    assert "qdrant_url" in error_str
    assert "vector_dimension" in error_str
    assert "embedding_model_name" in error_str
    assert "field required" in error_str or "validation error" in error_str


def test_load_required_from_environment(monkeypatch):
    """Verifica que cargue las variables requeridas desde el entorno."""
    # Valores simulados
    api_access_key_val = "test-access-key-env"
    deepseek_key_val = "test-deepseek-key-env"
    qdrant_url_val = "http://qdrant-test-env:6333"
    vector_dim_val = "128" # Como string, pydantic convierte
    embed_model_val = "model-from-env"

    monkeypatch.setenv("API_ACCESS_KEY", api_access_key_val)
    monkeypatch.setenv("DEEPSEEK_API_KEY", deepseek_key_val)
    monkeypatch.setenv("QDRANT_URL", qdrant_url_val)
    monkeypatch.setenv("VECTOR_DIMENSION", vector_dim_val)
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", embed_model_val)

    # Instanciar sin .env
    settings_instance = Settings(_env_file=None)

    assert isinstance(settings_instance.API_ACCESS_KEY, SecretStr)
    assert settings_instance.API_ACCESS_KEY.get_secret_value() == api_access_key_val
    assert isinstance(settings_instance.DEEPSEEK_API_KEY, SecretStr)
    assert settings_instance.DEEPSEEK_API_KEY.get_secret_value() == deepseek_key_val
    assert isinstance(settings_instance.QDRANT_URL, HttpUrl)
    assert str(settings_instance.QDRANT_URL) == qdrant_url_val + "/" # Pydantic añade /
    assert settings_instance.VECTOR_DIMENSION == int(vector_dim_val)
    assert settings_instance.EMBEDDING_MODEL_NAME == embed_model_val


def test_load_defaults_and_overrides_from_env(monkeypatch):
    """Verifica defaults y cómo env vars las sobrescriben."""
    # Variables requeridas mínimas
    monkeypatch.setenv("API_ACCESS_KEY", "req-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "req-key")
    monkeypatch.setenv("QDRANT_URL", "http://required-qdrant")
    monkeypatch.setenv("VECTOR_DIMENSION", "384") # Usar dimensión default para este test
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "default-model-test")

    # Sobrescribir algunos defaults vía env vars
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "overridden-collection")
    monkeypatch.setenv("API_RELOAD", "true") # Probar boolean

    # Instanciar sin .env
    settings_instance = Settings(_env_file=None)

    # Verificar valores sobrescritos
    assert settings_instance.API_HOST == "127.0.0.1"
    assert settings_instance.LOG_LEVEL == "DEBUG" # Validador lo pone en mayúsculas
    assert settings_instance.QDRANT_COLLECTION_NAME == "overridden-collection"
    assert settings_instance.API_RELOAD is True # Pydantic convierte "true"

    # Verificar valores que tomaron el default (porque no se sobrescribieron)
    assert settings_instance.API_PORT == 8000
    assert settings_instance.DEEPSEEK_MODEL_NAME == "deepseek-chat" # Default de config.py
    assert settings_instance.DISTANCE_METRIC == "Cosine" # Default de config.py
    assert settings_instance.MONGO_URI is None # Default de config.py
    assert settings_instance.RAG_TOP_K == 3 # Default de config.py


def test_load_from_dotenv_file(tmp_path):
    """Verifica la carga correcta desde un archivo .env específico."""
    # Contenido del .env temporal
    # Incluir todas las requeridas + algunas opcionales
    env_content = f"""
    # Comentario
    API_ACCESS_KEY=key_from_dotenv_file
    DEEPSEEK_API_KEY=deepseek_dotenv_key
    QDRANT_URL=https://dotenv.qdrant.cloud:6333
    VECTOR_DIMENSION=1024 # Valor diferente
    EMBEDDING_MODEL_NAME=dotenv-model

    QDRANT_API_KEY=optional_qdrant_key_dotenv
    API_PORT=9999
    LOG_LEVEL=WARNING
    MONGO_URI="mongodb://testuser:testpass@localmongo"
    RAG_TOP_K=5
    PRIORITY_CONTEXT_FILE_PATH=./data/custom_priority.json # Ruta relativa
    """
    test_env_file = tmp_path / ".env_test_load"
    test_env_file.write_text(env_content, encoding='utf-8')

    # Crear temporalmente el archivo de prioridad para que FilePath no falle (si se usa)
    # O asegurar que el validador/tipo en config.py no requiera existencia al cargar.
    # Asumiendo que PRIORITY_CONTEXT_FILE_PATH usa Path normal o el validador es robusto:
    priority_path_rel = Path("./data/custom_priority.json")
    abs_priority_path = (PROJECT_ROOT / priority_path_rel).resolve()

    # Usar subclase o model_config para apuntar al .env temporal
    class TestLoadSettings(Settings):
        model_config = SettingsConfigDict(env_file=test_env_file, case_sensitive=False, extra='ignore')

    settings_instance = TestLoadSettings()

    # Verificar valores cargados/sobrescritos
    assert settings_instance.API_ACCESS_KEY.get_secret_value() == "key_from_dotenv_file"
    assert settings_instance.DEEPSEEK_API_KEY.get_secret_value() == "deepseek_dotenv_key"
    assert str(settings_instance.QDRANT_URL) == "https://dotenv.qdrant.cloud:6333/"
    assert settings_instance.VECTOR_DIMENSION == 1024
    assert settings_instance.EMBEDDING_MODEL_NAME == "dotenv-model"
    assert settings_instance.QDRANT_API_KEY is not None
    assert settings_instance.QDRANT_API_KEY.get_secret_value() == "optional_qdrant_key_dotenv"
    assert settings_instance.API_PORT == 9999
    assert settings_instance.LOG_LEVEL == "WARNING"
    assert settings_instance.MONGO_URI is not None
    assert settings_instance.MONGO_URI.get_secret_value() == "mongodb://testuser:testpass@localmongo"
    assert settings_instance.RAG_TOP_K == 5
    # Verificar ruta resuelta
    assert settings_instance.PRIORITY_CONTEXT_FILE_PATH == abs_priority_path

    # Verificar un default no sobrescrito
    assert settings_instance.API_HOST == "0.0.0.0"


# --- Pruebas para Validadores Específicos (ya probados indirectamente antes) ---

def test_validator_log_level(monkeypatch):
    """Prueba explícita del validador de log_level."""
    # Establecer requeridas mínimas
    monkeypatch.setenv("API_ACCESS_KEY", "k"); monkeypatch.setenv("DEEPSEEK_API_KEY", "k");
    monkeypatch.setenv("QDRANT_URL", "http://a"); monkeypatch.setenv("VECTOR_DIMENSION", "1");
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "m")

    monkeypatch.setenv("LOG_LEVEL", "info")
    assert Settings(_env_file=None).LOG_LEVEL == "INFO"

    with pytest.raises(ValidationError, match="LOG_LEVEL inválido"):
        monkeypatch.setenv("LOG_LEVEL", "VERBOSE")
        Settings(_env_file=None)

def test_validator_distance_metric(monkeypatch):
    """Prueba explícita del validador de distance_metric."""
    # Establecer requeridas mínimas
    monkeypatch.setenv("API_ACCESS_KEY", "k"); monkeypatch.setenv("DEEPSEEK_API_KEY", "k");
    monkeypatch.setenv("QDRANT_URL", "http://a"); monkeypatch.setenv("VECTOR_DIMENSION", "1");
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "m")

    monkeypatch.setenv("DISTANCE_METRIC", "euclidean") # Probar alias/case
    assert Settings(_env_file=None).DISTANCE_METRIC == "Euclid"

    with pytest.raises(ValidationError, match="DISTANCE_METRIC inválida"):
        monkeypatch.setenv("DISTANCE_METRIC", "Hamming")
        Settings(_env_file=None)

def test_validator_embedding_device(monkeypatch):
    """Prueba explícita del validador de embedding_device."""
    # Establecer requeridas mínimas
    monkeypatch.setenv("API_ACCESS_KEY", "k"); monkeypatch.setenv("DEEPSEEK_API_KEY", "k");
    monkeypatch.setenv("QDRANT_URL", "http://a"); monkeypatch.setenv("VECTOR_DIMENSION", "1");
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "m")

    monkeypatch.setenv("EMBEDDING_DEVICE", "CUDA") # Probar case
    assert Settings(_env_file=None).EMBEDDING_DEVICE == "cuda" # Normaliza a minúsculas

    with pytest.raises(ValidationError, match="EMBEDDING_DEVICE inválido"):
        monkeypatch.setenv("EMBEDDING_DEVICE", "tpu")
        Settings(_env_file=None)