"""Schémas Pydantic v2 du service — contrats inter-services et structures internes."""

from pydantic import AliasGenerator, ConfigDict
from pydantic.alias_generators import to_camel


def camel_alias_generator() -> AliasGenerator:
    """Générateur d'alias : snake_case en Python, camelCase en JSON (contrats §3)."""
    return AliasGenerator(validation_alias=to_camel, serialization_alias=to_camel)


STRICT_CONFIG = ConfigDict(
    alias_generator=camel_alias_generator(),
    populate_by_name=True,
    extra="forbid",
)

__all__ = ["STRICT_CONFIG", "to_camel"]
