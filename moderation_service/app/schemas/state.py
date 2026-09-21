"""État de retry embarqué dans le job republié (`retryState`, main.md §3.3)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import STRICT_CONFIG
from app.schemas.enums import FilterStatus
from app.schemas.result import Detection


class RetryFilterItem(BaseModel):
    """État d'un item pour un filtre donné au sein du `retryState`."""

    model_config = STRICT_CONFIG

    status: FilterStatus
    attempts: int = Field(default=1, ge=0)
    detections: list[Detection] = []
    last_error: str | None = None


class RetryFilterState(BaseModel):
    """État d'un filtre : snapshot items → état."""

    model_config = STRICT_CONFIG

    items: dict[str, RetryFilterItem] = Field(default_factory=dict)


class RetryState(BaseModel):
    """`retryState` du job : ne contient que les items non résolus (§3.3)."""

    model_config = STRICT_CONFIG

    attempt: int = Field(default=0, ge=0)
    first_job_id: str = ""
    filters: dict[str, RetryFilterState] = Field(default_factory=dict)


__all__ = ["RetryFilterItem", "RetryFilterState", "RetryState"]
