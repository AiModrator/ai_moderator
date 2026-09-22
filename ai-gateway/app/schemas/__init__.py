"""Configuration stricte Pydantic (extra='forbid')."""

from __future__ import annotations

from pydantic import ConfigDict

STRICT_CONFIG = ConfigDict(
    extra="forbid",
    validate_assignment=True,
    str_strip_whitespace=True,
)
