# tests/conftest.py
# -*- coding: utf-8 -*-

"""
Configuraciones y fixtures compartidos para las pruebas de Kelly API con pytest.
CORREGIDO: Usa @pytest_asyncio.fixture y httpx.ASGITransport para el cliente async.
"""

import pytest
import asyncio
from typing import Generator, Any

# NUEVO: Importar pytest_asyncio para su decorador
import pytest_asyncio

# Usar AsyncClient y ASGITransport de httpx
try:
    # Asegúrate de tener httpx instalado (está en [dev,test] de pyproject.toml)
    from httpx import AsyncClient, ASGITransport
except ImportError:
    AsyncClient = None # type: ignore
    ASGITransport = None # type: ignore
    print("[ERROR conftest.py] httpx no instalado. Ejecuta: pip install httpx")


# Importar la aplicación FastAPI principal
try:
    # La ruta de importación asume que ejecutas pytest desde la raíz del proyecto
    from app.main import app as fastapi_app
except ImportError:
    print("[ERROR conftest.py] No se pudo importar 'app' desde 'app.main'.")
    print("Verifica la estructura del proyecto y que los __init__.py existan.")
    fastapi_app = None # type: ignore
except Exception as e: # Capturar otros errores como los de validación de config
     print(f"[ERROR conftest.py] Error al importar 'app' desde 'app.main' (posiblemente config): {e}")
     fastapi_app = None # type: ignore


# --- Fixture Principal: Cliente HTTP Asíncrono (CORREGIDA) ---

@pytest_asyncio.fixture(scope="module") # Usar decorador de pytest-asyncio
async def client() -> Generator[AsyncClient, Any, None]:
    """
    Fixture que proporciona un cliente HTTP asíncrono (httpx.AsyncClient)
    configurado para hacer peticiones a la aplicación FastAPI en memoria usando ASGITransport.
    """
    if AsyncClient is None or ASGITransport is None: # Verificar ambas importaciones
        pytest.fail("httpx no está instalado, necesario para el cliente de prueba async.")
        yield # type: ignore # Necesario para que Pytest lo trate como generador aunque falle

    if fastapi_app is None:
         pytest.fail("La aplicación FastAPI ('app') no pudo ser importada. Revisa errores previos.")
         yield # type: ignore

    # Crear un transporte ASGI que apunte a tu app FastAPI
    try:
        transport = ASGITransport(app=fastapi_app)
    except Exception as e_transport:
         pytest.fail(f"Error al crear ASGITransport: {e_transport}")
         yield # type: ignore

    # Crear el cliente async usando el transporte y la base_url
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        # print("\n[Debug Fixture] Creando AsyncClient...") # Descomentar para debug
        yield async_client # Proporciona el cliente a las pruebas que lo pidan
        # print("\n[Debug Fixture] Cerrando AsyncClient...") # Descomentar para debug
        # Limpieza automática por 'async with'


# --- (Opcional) Fixture para el Event Loop ---
# Generalmente no necesario con pytest-asyncio >= 0.15 y asyncio_mode = auto
# @pytest.fixture(scope="session")
# def event_loop(policy):
#     loop = policy.new_event_loop()
#     yield loop
#     loop.close()

# --- (Opcional) Otras Fixtures ---
# Ejemplo: Mockear settings para pruebas
# @pytest.fixture(autouse=True) # autouse=True para aplicarlo a todas las pruebas
# def override_settings(monkeypatch):
#     monkeypatch.setattr(config, "QDRANT_URL", "http://fake-qdrant:6333")
#     monkeypatch.setattr(config, "DEEPSEEK_API_KEY", SecretStr("fake-key"))
#     # ...etc