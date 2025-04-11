# tests/api/v1/endpoints/test_status.py
# -*- coding: utf-8 -*-

"""
Pruebas para los endpoints de estado definidos en app.api.v1.endpoints.status.
"""

import pytest
from httpx import AsyncClient # Cliente para hacer peticiones
from fastapi import status # Códigos de estado HTTP

# Importar el schema para verificar la respuesta es opcional pero bueno
try:
    from app.schemas.status import StatusResponse
except ImportError:
    StatusResponse = dict # Fallback

# Marcar todas las pruebas en este módulo como asíncronas
pytestmark = pytest.mark.asyncio


async def test_get_root_status(client: AsyncClient): # Usa la fixture 'client' de conftest.py
    """Verifica que el endpoint raíz GET / funcione y devuelva el estado correcto."""
    response = await client.get("/") # Hacer petición a la raíz

    # Verificar Status Code
    assert response.status_code == status.HTTP_200_OK

    # Verificar Contenido del Body
    json_response = response.json()
    assert json_response["status"] == "ok"
    # Verificar que el mensaje sea el esperado para el endpoint raíz
    assert "KellyBot API (v1) está operativa" in json_response["message"]

async def test_get_health_status(client: AsyncClient):
    """Verifica que el endpoint GET /health funcione y devuelva estado 'ok'."""
    response = await client.get("/health") # Hacer petición a /health

    # Verificar Status Code
    assert response.status_code == status.HTTP_200_OK

    # Verificar Contenido del Body
    json_response = response.json()
    assert json_response["status"] == "ok"
    # Verificar que el mensaje sea el esperado para /health
    assert json_response["message"] == "API healthy."