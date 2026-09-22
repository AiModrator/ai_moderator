"""Templates de prompt versionnés (main.md §5.4, §5.5)."""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.enums import MediaType, RiskClass


@dataclass(frozen=True)
class PromptTemplate:
    """Template de prompt versionné.

    Placeholders :
    - `{class}` : nom de la classe (ex: "TOXICITY")
    - `{definition}` : définition textuelle de la classe
    - `{score_scale}` : description de l'échelle de score (0-1)
    - `{output_schema}` : description du format JSON attendu
    """

    version: str
    system_template: str
    output_schema: str = (
        "Réponds UNIQUEMENT avec un objet JSON valide au format : "
        "{{\n  \"results\": [\n    {{\n      \"id\": \"<id_item>\",\n"
        "      \"score\": <float_0_1>,\n      \"reason\": \"<explication_courte>\"\n    }}\n  ]\n}}"
    )


# Définitions des classes (reprise spec fonctionnelle §4)
CLASS_DEFINITIONS: dict[RiskClass, str] = {
    "SCAM": "Tentative d'arnaque, fraude, ou manipulation pour obtenir argent/informations.",
    "PHISHING": "Usurpation d'identité, faux sites, collecte de credentials.",
    "ADVERTISING": "Publicité non sollicitée, spam commercial, promotion agressive.",
    "TOXICITY": "Contenu toxique, insultes, harcèlement, langage haineux.",
    "INSULT": "Insultes directes, mépris, attaques personnelles.",
    "HARASSMENT": "Harcèlement ciblé, menaces voilées, intimidation répétée.",
    "HATE_SPEECH": "Discours de haine envers groupes protégés (race, religion, genre, orientation).",
    "THREAT": "Menaces explicites de violence, de mort, de préjudice physique.",
    "VIOLENCE": "Violence graphique, incitation à la violence, contenu gore.",
    "SEXUAL": "Contenu sexuellement explicite, pornographie, exploitation sexuelle.",
    "SELF_HARM": "Automutilation, suicide, troubles alimentaires, encouragement à l'auto-dommage.",
    "ILLEGAL": "Activités illégales : drogues, armes, contrefaçon, cybercriminalité.",
}

# Templates système par (classe, media_type, version)
_PROMPT_TEMPLATES: dict[tuple[RiskClass, MediaType, str], PromptTemplate] = {}

# --- Text templates v1 ---
for rc in [
    "SCAM", "PHISHING", "ADVERTISING", "TOXICITY", "INSULT", "HARASSMENT",
    "HATE_SPEECH", "THREAT", "VIOLENCE", "SEXUAL", "SELF_HARM", "ILLEGAL",
]:
    _PROMPT_TEMPLATES[(rc, "text", "v1")] = PromptTemplate(
        version="v1",
        system_template=(
            "Tu es un modérateur de contenu expert. "
            "Analyse le(s) texte(s) fourni(s) pour détecter la classe « {class} ».\n\n"
            "Définition de la classe : {definition}\n\n"
            "Échelle de score : {score_scale}\n\n"
            "Pour chaque item, réponds avec un score ∈ [0, 1] et une raison courte.\n"
            "Score 0 = absence totale, 1 = certitude maximale.\n\n"
            "{output_schema}"
        ),
    )

# --- Image templates v1 ---
for rc in ["HATE_SPEECH", "SEXUAL", "VIOLENCE", "ILLEGAL", "SELF_HARM"]:
    _PROMPT_TEMPLATES[(rc, "image", "v1")] = PromptTemplate(
        version="v1",
        system_template=(
            "Tu es un modérateur de contenu expert vision. "
            "Analyse l'image fournie pour détecter la classe « {class} ».\n\n"
            "Définition de la classe : {definition}\n\n"
            "Échelle de score : {score_scale}\n\n"
            "Pour chaque image, réponds avec un score ∈ [0, 1] et une raison courte.\n"
            "Score 0 = absence totale, 1 = certitude maximale.\n\n"
            "{output_schema}"
        ),
    )


def get_template(risk_class: RiskClass, media_type: MediaType, version: str = "latest") -> PromptTemplate:
    """Récupère un template de prompt.

    Args:
        risk_class: Classe de risque
        media_type: Type de média (text/image)
        version: Version du template ("latest" ou version explicite)

    Returns:
        PromptTemplate correspondant

    Raises:
        KeyError: si (risk_class, media_type) non supporté
    """
    # Résolution de la version
    resolved_version = "v1" if version == "latest" else version
    key = (risk_class, media_type, resolved_version)
    if key in _PROMPT_TEMPLATES:
        return _PROMPT_TEMPLATES[key]

    # Fallback sur v1 si version demandée non trouvée
    fallback_key = (risk_class, media_type, "v1")
    if fallback_key in _PROMPT_TEMPLATES:
        return _PROMPT_TEMPLATES[fallback_key]

    raise KeyError(f"Template non trouvé pour {risk_class}/{media_type} version {version}")


def list_versions(risk_class: RiskClass, media_type: MediaType) -> list[str]:
    """Liste les versions disponibles pour un couple (classe, media)."""
    versions = {
        v for (rc, mt, v) in _PROMPT_TEMPLATES.keys()
        if rc == risk_class and mt == media_type
    }
    return sorted(versions)


__all__ = [
    "PromptTemplate",
    "CLASS_DEFINITIONS",
    "get_template",
    "list_versions",
]
