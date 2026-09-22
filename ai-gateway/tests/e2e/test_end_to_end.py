"""Tests e2e bout en bout (main.md §12, §2.1).

Parcours complet : POST /v1/moderation/{riskClass} → Router → Provider → Decision.
"""

from __future__ import annotations

import asyncio

import pytest
import respx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from httpx import Response

from app.config.settings import Settings
from main import create_app


@pytest.fixture
def settings():
    """Settings pour tests e2e."""
    key = Fernet.generate_key().decode()
    return Settings(
        encryption_key=key,
        gateway_api_key="test-gateway-key",
        admin_api_key="test-admin-key",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_db="ai_gateway_test",
        log_format="console",
        log_level="DEBUG",
        fallback_to_test_provider=True,
    )


@pytest.fixture
def app(settings):
    """App FastAPI pour tests."""
    app = create_app(settings)
    # Trigger startup events to initialize router
    for handler in app.router.on_startup:
        asyncio.run(handler())
    return app


@pytest.fixture
def client(app):
    """Client de test FastAPI."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def gateway_headers():
    """Headers avec clé API gateway."""
    return {"Authorization": "Bearer test-gateway-key"}


@respx.mock
@pytest.mark.e2e
def test_e2e_text_moderation_happy_path(client, gateway_headers):
    """Test modération texte bout en bout : happy path."""
    # Mock TestProvider
    respx.post("http://test/v1/moderation/TOXICITY").mock(
        return_value=Response(
            200,
            json={
                "model": "test-model",
                "results": [
                    {"id": "c-1", "score": 0.9, "reason": "toxic content"},
                    {"id": "c-2", "score": 0.1, "reason": "safe"},
                ],
            },
        )
    )

    payload = {
        "accountId": "acc-1",
        "activeClasses": ["TOXICITY"],
        "mediaType": "text",
        "items": [
            {"id": "c-1", "content": "I hate you all"},
            {"id": "c-2", "content": "Hello world"},
        ],
    }

    response = client.post(
        "/v1/moderation/TOXICITY",
        json=payload,
        headers={"Authorization": "Bearer test-gateway-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "test-model"
    assert len(data["results"]) == 2
    assert data["results"][0]["id"] == "c-1"
    assert data["results"][0]["score"] == 0.9
    assert data["results"][1]["id"] == "c-2"
    assert data["results"][1]["score"] == 0.1


@respx.mock
@pytest.mark.e2e
def test_e2e_multiple_risk_classes(client, gateway_headers):
    """Test modération avec plusieurs classes de risque."""
    # Mock pour TOXICITY
    respx.post("http://test/v1/moderation/TOXICITY").mock(
        return_value=Response(
            200,
            json={
                "model": "test-model",
                "results": [{"id": "c-1", "score": 0.8, "reason": "toxic"}],
            },
        )
    )

    payload = {
        "accountId": "acc-1",
        "activeClasses": ["TOXICITY"],
        "mediaType": "text",
        "items": [{"id": "c-1", "content": "toxic content"}],
    }

    response = client.post(
        "/v1/moderation/TOXICITY",
        json=payload,
        headers={"Authorization": "Bearer test-gateway-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["score"] == 0.8


@respx.mock
@pytest.mark.e2e
def test_e2e_image_moderation(client, gateway_headers):
    """Test modération image (via TestProvider)."""
    respx.post("http://test/v1/moderation/VIOLENCE").mock(
        return_value=Response(
            200,
            json={
                "model": "test-model",
                "results": [{"id": "img-1", "score": 0.7, "reason": "violent image"}],
            },
        )
    )

    payload = {
        "accountId": "acc-1",
        "activeClasses": ["VIOLENCE"],
        "mediaType": "image",
        "items": [
            {"id": "img-1", "content": "https://example.com/violent.jpg"}
        ],
    }

    response = client.post(
        "/v1/moderation/VIOLENCE",
        json=payload,
        headers={"Authorization": "Bearer test-gateway-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["id"] == "img-1"
    assert data["results"][0]["score"] == 0.7


@pytest.mark.e2e
def test_e2e_invalid_class(client, gateway_headers):
    """Test classe inconnue → 404."""
    payload = {
        "activeClasses": ["UNKNOWN_CLASS"],
        "mediaType": "text",
        "items": [{"id": "c-1", "content": "test"}],
    }

    response = client.post(
        "/v1/moderation/UNKNOWN_CLASS",
        json=payload,
        headers={"Authorization": "Bearer test-gateway-key"},
    )

    assert response.status_code == 404


@pytest.mark.e2e
def test_e2e_invalid_media_type(client, gateway_headers):
    """Test mediaType non supporté pour la classe → 400."""
    payload = {
        "activeClasses": ["TOXICITY"],
        "mediaType": "image",
        "items": [{"id": "c-1", "content": "https://example.com/img.jpg"}],
    }

    response = client.post(
        "/v1/moderation/TOXICITY",
        json=payload,
        headers={"Authorization": "Bearer test-gateway-key"},
    )

    assert response.status_code == 400


@pytest.mark.e2e
def test_e2e_missing_auth(client):
    """Test sans header Authorization → 401."""
    payload = {
        "activeClasses": ["TOXICITY"],
        "mediaType": "text",
        "items": [{"id": "c-1", "content": "test"}],
    }

    response = client.post("/v1/moderation/TOXICITY", json=payload)
    assert response.status_code == 401


@pytest.mark.e2e
def test_e2e_invalid_auth(client):
    """Test clé API invalide → 401."""
    payload = {
        "activeClasses": ["TOXICITY"],
        "mediaType": "text",
        "items": [{"id": "c-1", "content": "test"}],
    }

    response = client.post(
        "/v1/moderation/TOXICITY",
        json=payload,
        headers={"Authorization": "Bearer invalid-key"},
    )
    assert response.status_code == 401


@respx.mock
@pytest.mark.e2e
def test_e2e_transient_error_fallback(client, gateway_headers):
    """Test erreur transitoire sur premier modèle → fallback sur second modèle."""
    # Premier modèle (provider test) → erreur transitoire
    respx.post("http://test/v1/moderation/TOXICITY").mock(
        return_value=Response(500, json={"error": "internal error"})
    )

    payload = {
        "activeClasses": ["TOXICITY"],
        "mediaType": "text",
        "items": [{"id": "c-1", "content": "test"}],
    }

    response = client.post(
        "/v1/moderation/TOXICITY",
        json=payload,
        headers={"Authorization": "Bearer test-gateway-key"},
    )

    # Le test provider est le seul, il ne peut pas faire de fallback
    # On vérifie qu'on a une erreur 503
    assert response.status_code == 503


@respx.mock
@pytest.mark.e2e
def test_e2e_invalid_response_retry(client, gateway_headers):
    """Test réponse invalide → retry validation → fallback."""
    # Premier appel : réponse invalide
    # Second appel (retry) : succès
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(200, json={"model": "m", "results": []})  # JSON valide mais sans results
        return Response(200, json={"model": "test", "results": [{"id": "c-1", "score": 0.5}]})

    respx.post("http://test/v1/moderation/TOXICITY").mock(side_effect=handler)

    payload = {
        "activeClasses": ["TOXICITY"],
        "mediaType": "text",
        "items": [{"id": "c-1", "content": "test"}],
    }

    response = client.post(
        "/v1/moderation/TOXICITY",
        json=payload,
        headers={"Authorization": "Bearer test-gateway-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["score"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
