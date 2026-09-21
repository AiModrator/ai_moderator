"""Enums métier du service de modération.

Aucun enum de sévérité ici : le seul signal de détection est le `score` ∈ [0,1].
Le mapping score → sévérité relève de l'Action Service (phase 5).
"""

from __future__ import annotations

from enum import StrEnum


class RiskClass(StrEnum):
    """Classes de risque reconnues par le contrat inter-services (D-02)."""

    SPAM = "SPAM"
    SCAM = "SCAM"
    PHISHING = "PHISHING"
    MALICIOUS_LINK = "MALICIOUS_LINK"
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
    OFF_TOPIC = "OFF_TOPIC"


class ContentType(StrEnum):
    POST = "post"
    COMMENT = "comment"
    MESSAGE = "message"
    PROFILE_BIO = "profile_bio"
    ATTACHMENT_ONLY = "attachment_only"


class AttachmentType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class Source(StrEnum):
    """Origine d'une détection : texte, image, ou comportement (SpamFilter)."""

    TEXT = "text"
    IMAGE = "image"
    BEHAVIOR = "behavior"


class FilterStatus(StrEnum):
    """Machine d'états d'un filtre pour un item (cf. main.md §13.4)."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    PENDING_RETRY = "PENDING_RETRY"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


TERMINAL_STATUSES = frozenset(
    {FilterStatus.COMPLETED, FilterStatus.SKIPPED, FilterStatus.FAILED, FilterStatus.UNAVAILABLE}
)


__all__ = [
    "RiskClass",
    "ContentType",
    "AttachmentType",
    "Source",
    "FilterStatus",
    "TERMINAL_STATUSES",
]
