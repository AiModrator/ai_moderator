"""État de retry embarqué dans le job republié (`retryState`, §3.3) et état runtime `BatchState` (§13.2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from app.schemas import STRICT_CONFIG
from app.schemas.enums import TERMINAL_STATUSES, FilterStatus, RiskClass
from app.schemas.result import Detection, FilterOutcome

if TYPE_CHECKING:
    from app.schemas.job import ContentBatchJob


# ---------------------------------------------------------------------------
# Contrat `retryState` (main.md §3.3) — sérialisable dans le job republié
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# État runtime (Worker) — main.md §13.2, non sérialisé directement
# ---------------------------------------------------------------------------


@dataclass
class FilterItemState:
    """État runtime d'un item pour un filtre."""

    status: FilterStatus = FilterStatus.PENDING
    attempts: int = 0
    detections: list[Detection] = field(default_factory=list)
    last_error: str | None = None


@dataclass
class FilterState:
    """État runtime d'un filtre : contentId → état item."""

    items: dict[str, FilterItemState] = field(default_factory=dict)


class BatchState:
    """État de l'ensemble du lot (snapshot des filtres × items).

    - `new(payload)` : état initial PENDING pour chaque (filtre, item).
    - `from_retry(payload, retry_state)` : restaure l'état d'un passage précédent.
    - Les transitions `set`/`mark_*` suivent §6.2/6.3 ; `mark_transient` applique
      la borne `MAX_FILTER_RETRIES` (double garde avec le Worker, §6.1 étape 9).
    """

    def __init__(
        self,
        *,
        batch_id: str,
        community_ref: str,
        active_classes: list[RiskClass],
        max_retries: int,
        attempt: int = 0,
        first_job_id: str = "",
    ) -> None:
        self.batch_id = batch_id
        self.community_ref = community_ref
        self.active_classes = list(active_classes)
        self.max_retries = max_retries
        self.attempt = attempt
        self.first_job_id = first_job_id
        self.filters: dict[str, FilterState] = {}

    # ----- construction -----

    @classmethod
    def new(cls, payload: ContentBatchJob, max_retries: int) -> BatchState:
        return cls(
            batch_id=payload.batch_id,
            community_ref=payload.community_ref,
            active_classes=list(payload.active_classes),
            max_retries=max_retries,
        )

    @classmethod
    def from_retry(
        cls,
        payload: ContentBatchJob,
        retry_state: RetryState | None,
        max_retries: int,
    ) -> BatchState:
        """Restaure l'état depuis `retryState` (ou état initial si `None`)."""
        state = cls(
            batch_id=payload.batch_id,
            community_ref=payload.community_ref,
            active_classes=list(payload.active_classes),
            max_retries=max_retries,
            attempt=retry_state.attempt if retry_state else 0,
            first_job_id=retry_state.first_job_id if retry_state else "",
        )
        if retry_state:
            for filter_name, filter_state in retry_state.filters.items():
                items: dict[str, FilterItemState] = {}
                for content_id, item_state in filter_state.items.items():
                    items[content_id] = FilterItemState(
                        status=item_state.status,
                        attempts=item_state.attempts,
                        detections=list(item_state.detections),
                        last_error=item_state.last_error,
                    )
                state.filters[filter_name] = FilterState(items=items)
        return state

    def ensure_filter(self, filter_name: str, content_ids: list[str]) -> None:
        """Garantit l'existence d'un filtre et d'une entrée PENDING par item manquant."""
        filter_state = self.filters.setdefault(filter_name, FilterState())
        for content_id in content_ids:
            if content_id not in filter_state.items:
                filter_state.items[content_id] = FilterItemState(status=FilterStatus.PENDING)

    # ----- transitions -----

    def set(self, filter_name: str, outcome: FilterOutcome) -> None:
        """Applique le résultat d'une évaluation réussie (COMPLETED | SKIPPED | FAILED)."""
        state = self._item(filter_name, outcome.content_id)
        if outcome.status == FilterStatus.SKIPPED:
            state.status = FilterStatus.SKIPPED
            state.detections = []
            state.last_error = None
            return
        state.attempts += 1
        state.status = outcome.status
        state.detections = list(outcome.detections)
        state.last_error = outcome.error

    def mark_transient(self, filter_name: str, content_id: str, error_obj: Exception) -> None:
        """Erreur transitoire : PENDING_RETRY (ou UNAVAILABLE si retries épuisés)."""
        state = self._item(filter_name, content_id)
        state.attempts += 1
        state.last_error = f"{error_obj.__class__.__name__}: {error_obj}"
        state.status = (
            FilterStatus.UNAVAILABLE if state.attempts > self.max_retries else FilterStatus.PENDING_RETRY
        )

    def mark_failed(self, filter_name: str, content_id: str, error_obj: Exception) -> None:
        """Erreur permanente : FAILED (jamais ré-exécuté)."""
        state = self._item(filter_name, content_id)
        state.attempts += 1
        state.status = FilterStatus.FAILED
        state.last_error = f"{error_obj.__class__.__name__}: {error_obj}"

    def mark_skipped(self, filter_name: str, content_id: str) -> None:
        """Item non applicable → SKIPPED sans exécution."""
        state = self._item(filter_name, content_id)
        state.status = FilterStatus.SKIPPED
        state.detections = []

    # ----- lecture / export -----

    def item_status(self, filter_name: str, content_id: str) -> FilterStatus:
        return self._item(filter_name, content_id).status

    def resolved_items(self) -> list[str]:
        """Items dont tous les filtres du pipeline sont terminaux (§6.1 étape 7)."""
        if not self.filters:
            return []
        all_ids: set[str] = set()
        for fstate in self.filters.values():
            all_ids.update(fstate.items.keys())
        return sorted(
            content_id
            for content_id in all_ids
            if all(
                fstate.items[content_id].status in TERMINAL_STATUSES
                for fstate in self.filters.values()
                if content_id in fstate.items
            )
        )

    def to_retry_state(self, unresolved: list[str], next_attempt: int) -> RetryState:
        """Snapshot `retryState` : uniquement les items non résolus, détections conservées."""
        unresolved_set = set(unresolved)
        out_filters: dict[str, RetryFilterState] = {}
        for filter_name, fstate in self.filters.items():
            items = {
                content_id: RetryFilterItem(
                    status=item.status,
                    attempts=item.attempts,
                    detections=list(item.detections),
                    last_error=item.last_error,
                )
                for content_id, item in fstate.items.items()
                if content_id in unresolved_set
            }
            if items:
                out_filters[filter_name] = RetryFilterState(items=items)
        return RetryState(attempt=next_attempt, first_job_id=self.first_job_id, filters=out_filters)

    # ----- interne -----

    def _item(self, filter_name: str, content_id: str) -> FilterItemState:
        try:
            return self.filters[filter_name].items[content_id]
        except KeyError as exc:  # invariant : l'état doit exister pour (filtre, item)
            raise RuntimeError(f"no state for ({filter_name}, {content_id})") from exc

    def __repr__(self) -> str:
        return (
            f"BatchState(attempt={self.attempt}, filters={list(self.filters)} "
            f"resolved={len(self.resolved_items())})"
        )


__all__ = [
    "RetryFilterItem",
    "RetryFilterState",
    "RetryState",
    "FilterItemState",
    "FilterState",
    "BatchState",
]
