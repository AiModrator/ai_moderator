#!/usr/bin/env python
"""Script de seed des providers et modèles pour l'AI Gateway.

Usage:
    python -m tests.scripts.seed_providers

Variables d'environnement requises :
    MONGODB_URI (défaut: mongodb://localhost:27017)
    MONGODB_DB (défaut: ai_gateway)
    AI_GATEWAY_ENCRYPTION_KEY (requis)
    AI_GATEWAY_API_KEY (requis)
    AI_GATEWAY_ADMIN_API_KEY (requis)
    OPENROUTER_API_KEY (optionnel, pour provider openrouter)
"""

from __future__ import annotations

import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient

from app.config.security import FernetCipher
from app.config.settings import Settings
from app.db import get_database
from app.db.repositories import ModelRepository, ProviderRepository
from app.schemas.enums import MediaType, RiskClass
from app.schemas.providers import ModelDocument, ProviderKind


async def main() -> int:
    # Charger settings
    settings = Settings(
        mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
        mongodb_db=os.getenv("MONGODB_DB", "ai_gateway"),
        encryption_key=os.getenv("AI_GATEWAY_ENCRYPTION_KEY", ""),
        gateway_api_key=os.getenv("AI_GATEWAY_API_KEY", "test-gateway-key"),
        admin_api_key=os.getenv("AI_GATEWAY_ADMIN_API_KEY", "test-admin-key"),
        log_format="console",
    )

    # Validation
    if not settings.encryption_key:
        print("ERREUR: AI_GATEWAY_ENCRYPTION_KEY manquant")
        return 1

    # Connexion MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = get_database(client, settings)

    cipher = FernetCipher(settings.encryption_key)
    provider_repo = ProviderRepository(db.providers, cipher)
    model_repo = ModelRepository(db.models)

    # Nettoyer collections existantes
    await db.providers.delete_many({})
    await db.models.delete_many({})

    print("=== Seed des providers ===")

    # 1. Provider Test (déterministe, pour tests)
    print("Création provider 'test'...")
    await ProviderRepository(db.providers, cipher).create(
        name="test",
        kind=ProviderKind.TEST,
        display_name="Test Provider",
        base_url="http://test",
        api_key=None,
        enabled=True,
    )

    # 2. Provider OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key:
        print("Création provider 'openrouter'...")
        await ProviderRepository(db.providers, cipher).create(
            name="openrouter",
            kind=ProviderKind.OPENROUTER,
            display_name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            enabled=True,
        )
    else:
        print("ATTENTION: OPENROUTER_API_KEY non fourni, provider openrouter non créé")

    print("=== Seed des modèles ===")

    # Modèles pour provider 'test'
    test_models = [
        ModelDocument(
            id="test-text",
            provider="test",
            model="test-text-model",
            display_name="Test Text Model",
            capabilities=[MediaType.TEXT],
            tasks=[
                RiskClass.SCAM, RiskClass.PHISHING, RiskClass.ADVERTISING,
                RiskClass.TOXICITY, RiskClass.INSULT, RiskClass.HARASSMENT,
                RiskClass.HATE_SPEECH, RiskClass.THREAT, RiskClass.VIOLENCE,
                RiskClass.SEXUAL, RiskClass.SELF_HARM, RiskClass.ILLEGAL,
            ],
            max_input_tokens=32000,
            max_output_tokens=500,
            cost_input=0.0,
            cost_output=0.0,
            priority=1,
            enabled=True,
        ),
    ]

    # Modèles pour provider 'openrouter' (si créé)
    openrouter_models = []
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_key:
        openrouter_models = [
            ModelDocument(
                id="openrouter-text",
                provider="openrouter",
                model="meta-llama/llama-3.1-8b-instruct:free",
                display_name="Llama 3.1 8B (Text)",
                capabilities=[MediaType.TEXT],
                tasks=[
                    RiskClass.SCAM, RiskClass.PHISHING, RiskClass.ADVERTISING,
                    RiskClass.TOXICITY, RiskClass.INSULT, RiskClass.HARASSMENT,
                    RiskClass.HATE_SPEECH, RiskClass.THREAT, RiskClass.VIOLENCE,
                    RiskClass.SEXUAL, RiskClass.SELF_HARM, RiskClass.ILLEGAL,
                ],
                max_input_tokens=32000,
                max_output_tokens=500,
                cost_input=0.0,
                cost_output=0.0,
                priority=10,
                enabled=True,
            ),
            ModelDocument(
                id="openrouter-image",
                provider="openrouter",
                model="llava-v1.6-mistral-7b:free",
                display_name="LLaVA 1.6 (Image)",
                capabilities=[MediaType.IMAGE],
                tasks=[
                    RiskClass.HATE_SPEECH, RiskClass.SEXUAL,
                    RiskClass.VIOLENCE, RiskClass.ILLEGAL, RiskClass.SELF_HARM,
                ],
                max_input_tokens=32000,
                max_output_tokens=500,
                cost_input=0.0,
                cost_output=0.0,
                priority=10,
                enabled=True,
            ),
        ]

    # Insertion modèles
    model_repo = ModelRepository(db.models)
    for model in test_models + openrouter_models:
        await model_repo.create(model)
        print(f"  Modèle créé: {model.id} ({model.provider})")

    print("\n=== Seed terminé avec succès ===")

    # Afficher résumé
    providers = await db.providers.find().to_list(100)
    models = await db.models.find().to_list(100)
    print(f"\nProviders: {len(providers)}")
    for p in providers:
        print(f"  - {p['name']} ({p['kind']}) {'enabled' if p['enabled'] else 'disabled'}")
    print(f"\nModèles: {len(models)}")
    for m in models:
        print(f"  - {m['id']} (provider: {m['provider']}, tasks: {m['tasks']})")

    return 0


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
