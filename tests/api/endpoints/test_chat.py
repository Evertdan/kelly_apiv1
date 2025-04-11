# tests/api/endpoints/test_chat.py
# -*- coding: utf-8 -*-

"""
Pruebas para el endpoint de chat definido en app.api.v1.endpoints.chat.
CORREGIDO: Ajuste final en mocking de seguridad.
"""

import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock, patch # Asegurar AsyncMock

# Importar schemas para verificar la respuesta
try:
    from app.schemas.chat import ChatResponse, SourceInfo
except ImportError:
     print("[WARN test_chat.py] No se pudieron importar schemas ChatResponse/SourceInfo.")
     ChatResponse = dict # Fallback
     SourceInfo = dict # Fallback

# Clave API dummy para pruebas
TEST_API_KEY = "test-api-key-123"
HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}

# Datos de entrada válidos
VALID_CHAT_PAYLOAD = {"message": "Hola", "session_id": "test-session-chat"}

# Respuesta simulada que esperamos del servicio RAG
MOCKED_RAG_RESPONSE = {
    "answer": "Respuesta simulada por el RAG.",
    "sources": [{"source_id": "DOC_SIMULADO_q0", "score": 0.99}]
}

# Marcar todas las pruebas como asíncronas
pytestmark = pytest.mark.asyncio


async def test_chat_endpoint_success(client: AsyncClient, mocker):
    """Prueba una llamada exitosa al endpoint POST /api/v1/chat."""

    # Mockear RAG Service (ruta ya corregida)
    mocked_rag_call = mocker.patch(
        "app.services.rag_pipeline.generate_response",
        return_value=MOCKED_RAG_RESPONSE,
        new_callable=AsyncMock
    )
    # --- CORRECCIÓN MOCK SEGURIDAD ---
    # Intentar parchear la función verify_api_key en el módulo deps donde es llamada
    # por la dependencia get_api_key
    mocker.patch(
        "app.api.deps.verify_api_key", # <- Parchear donde se usa en la dependencia
        return_value=TEST_API_KEY,
        new_callable=AsyncMock
    )
    # --- FIN CORRECCIÓN ---

    response = await client.post("/api/v1/chat", json=VALID_CHAT_PAYLOAD, headers=HEADERS)

    # Verificar respuesta HTTP
    assert response.status_code == status.HTTP_200_OK

    # Verificar llamada al RAG mockeado
    mocked_rag_call.assert_awaited_once_with(
        question=VALID_CHAT_PAYLOAD["message"],
        session_id=VALID_CHAT_PAYLOAD["session_id"]
    )

    # Verificar contenido respuesta JSON
    json_response = response.json()
    assert json_response["answer"] == MOCKED_RAG_RESPONSE["answer"]
    assert json_response["session_id"] == VALID_CHAT_PAYLOAD["session_id"]
    assert len(json_response["sources"]) == 1
    assert json_response["sources"][0]["source_id"] == MOCKED_RAG_RESPONSE["sources"][0]["source_id"]
    assert json_response["sources"][0]["score"] == pytest.approx(MOCKED_RAG_RESPONSE["sources"][0]["score"])


async def test_chat_endpoint_missing_message(client: AsyncClient, mocker):
    """Prueba error 422 si falta 'message'."""
    # Mockear seguridad
    mocker.patch("app.api.deps.verify_api_key", return_value=TEST_API_KEY, new_callable=AsyncMock)

    invalid_payload = {"session_id": "test-session-chat"}
    response = await client.post("/api/v1/chat", json=invalid_payload, headers=HEADERS)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


async def test_chat_endpoint_missing_session_id(client: AsyncClient, mocker):
    """Prueba error 422 si falta 'session_id'."""
    # Mockear seguridad
    mocker.patch("app.api.deps.verify_api_key", return_value=TEST_API_KEY, new_callable=AsyncMock)

    invalid_payload = {"message": "Hola"}
    response = await client.post("/api/v1/chat", json=invalid_payload, headers=HEADERS)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# --- Pruebas de Autenticación (NO necesitan mock de seguridad) ---
async def test_chat_endpoint_no_auth(client: AsyncClient):
    """Prueba error 401 si falta cabecera Authorization."""
    response = await client.post("/api/v1/chat", json=VALID_CHAT_PAYLOAD)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_chat_endpoint_invalid_auth(client: AsyncClient):
    """Prueba error 401 si la API Key es incorrecta."""
    invalid_headers = {"Authorization": "Bearer invalidkey"}
    response = await client.post("/api/v1/chat", json=VALID_CHAT_PAYLOAD, headers=invalid_headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_chat_endpoint_rag_service_error(client: AsyncClient, mocker):
    """Prueba cómo maneja el endpoint un error 500 del servicio RAG."""
    # Mockear seguridad
    mocker.patch("app.api.deps.verify_api_key", return_value=TEST_API_KEY, new_callable=AsyncMock)

    # Mockear RAG Service para que lance error (ruta ya corregida)
    mocker.patch(
        "app.services.rag_pipeline.generate_response",
        side_effect=Exception("Error simulado en RAG"),
        new_callable=AsyncMock # Si generate_response es async
    )

    response = await client.post("/api/v1/chat", json=VALID_CHAT_PAYLOAD, headers=HEADERS)

    # Esperamos un error interno del servidor desde el endpoint
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    json_response = response.json()
    assert "detail" in json_response
    assert "Ocurrió un error interno" in json_response["detail"]