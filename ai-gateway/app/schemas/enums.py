"""Enums métier de l'AI Gateway (main.md §1, §31).

Le gateway ne traite que les classes **dédiées à l'IA** :
`SPAM`, `MALICIOUS_LINK`, `OFF_TOPIC` sont gérés par les filtres à règles
du Moderation Service.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class RiskClass(StrEnum):
    """Classes de risque gérées par l'AI Gateway (12 valeurs)."""

    SCAM = "SCAM"
    PHISHING = "PHISHING"
    ADVERTISING = "ADVERTISING"
    TOXICITY = "TOXICITY"
    INSULT = "INSULT"
    HARASSMENT = "HARASSMENT"
    HATE_SPEECH = "HATE_SPEECH"
    THREAT = "THREAT"
    VIOLENCE = "VIOLENCE"
    SEXUAL = "SEXUAL"
    SELF_HARM = "SELF_HARM"
    ILLEGAL = "ILLEGAL"


class MediaType(StrEnum):
    """Type de média supporté."""

    TEXT = "text"
    IMAGE = "image"


# Capacités média par classe (main.md §1, CLASS_MEDIA_CAPABILITIES)
CLASS_MEDIA_CAPABILITIES: Final[dict[RiskClass, set[MediaType]]] = {
    RiskClass.SCAM: {MediaType.TEXT},
    RiskClass.PHISHING: {MediaType.TEXT},
    RiskClass.ADVERTISING: {MediaType.TEXT},
    RiskClass.TOXICITY: {MediaType.TEXT},
    RiskClass.INSULT: {MediaType.TEXT},
    RiskClass.HARASSMENT: {MediaType.TEXT},
    RiskClass.THREAT: {MediaType.TEXT},
    RiskClass.HATE_SPEECH: {MediaType.TEXT, MediaType.IMAGE},
    RiskClass.SEXUAL: {MediaType.TEXT, MediaType.IMAGE},
    RiskClass.VIOLENCE: {MediaType.TEXT, MediaType.IMAGE},
    RiskClass.ILLEGAL: {MediaType.TEXT, MediaType.IMAGE},
    RiskClass.SELF_HARM: {MediaType.TEXT, MediaType.IMAGE},
}

# Définitions textuelles par classe (injectées dans les prompts)
CLASS_DEFINITIONS: Final[dict[RiskClass, str]] = {
    RiskClass.SCAM: "Tentative d'arnaque, fraude, ou manipulation pour obtenir argent/informations.",
    RiskClass.PHISHING: "Usurpation d'identité, faux sites, collecte de credentials.",
    RiskClass.ADVERTISING: "Publicité non sollicitée, spam commercial, promotion agressive.",
    RiskClass.TOXICITY: "Contenu toxique, insultes, harcèlement, langage haineux.",
    RiskClass.INSULT: "Insultes directes, mépris, attaques personnelles.",
    RiskClass.HARASSMENT: "Harcèlement ciblé, menaces voilées, intimidation répétée.",
    RiskClass.HATE_SPEECH: "Discours de haine envers groupes protégés (race, religion, genre, orientation).",
    RiskClass.THREAT: "Menaces explicites de violence, de mort, de préjudice physique.",
    RiskClass.VIOLENCE: "Violence graphique, incitation à la violence, contenu gore.",
    RiskClass.SEXUAL: "Contenu sexuellement explicite, pornographie, exploitation sexuelle.",
    RiskClass.SELF_HARM: "Automutilation, suicide, troubles alimentaires, encouragement à l'auto-dommage.",
    RiskClass.ILLEGAL: "Activités illégales : drogues, armes, contrefaçon, cybercriminalité.",
}


__all__ = [
    "RiskClass",
    "MediaType",
    "CLASS_MEDIA_CAPABILITIES",
    "CLASS_DEFINITIONS",
]
