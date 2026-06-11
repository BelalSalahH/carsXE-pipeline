"""Pipeline orchestration: collect -> normalize -> sanity-check -> export.

Owns no OEM specifics. Resolves providers from the registry, runs every record
through the shared normalization path, deduplicates by canonical key, and writes
the artifact. Per-record failures are isolated so one bad record never aborts a run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .errors import NormalizationError
from .export import write_output
from .models import Trim
from .normalize import normalize_record, sanity_warnings
from .registry import get_provider

log = logging.getLogger(__name__)


@dataclass(slots=True)
class RunSummary:
    make_counts: dict[str, int] = field(default_factory=dict)
    total: int = 0
    null_fields: int = 0
    sanity_warnings: int = 0
    skipped: int = 0
    duplicates: int = 0


# Spec fields whose completeness the null metric reflects. Identity fields are
# never null; notes/source are provenance, not spec data, so both are excluded.
_SPEC_FIELDS = ("base_msrp", "fuel_type", "horsepower", "drivetrain", "seating_capacity")


def _count_nulls(trim: Trim) -> int:
    record = trim.to_dict()
    nulls = sum(1 for f in _SPEC_FIELDS if record[f] is None)
    dimensions: dict[str, float | None] = record["dimensions"]  # type: ignore[assignment]
    nulls += sum(1 for v in dimensions.values() if v is None)
    return nulls


def run(
    makes: list[str],
    models: list[str] | None,
    out_path: Path,
    *,
    refresh: bool = False,
) -> RunSummary:
    summary = RunSummary()
    deduped: dict[tuple[int, str, str, str], Trim] = {}

    for make in makes:
        provider = get_provider(make, refresh=refresh)
        raw_records = provider.collect(models)
        kept = 0

        for raw in raw_records:
            try:
                trim = normalize_record(raw)
            except NormalizationError as exc:
                log.error("skipping record: %s", exc)
                summary.skipped += 1
                continue

            for warning in sanity_warnings(trim):
                log.warning("%s %s %s: %s", trim.make, trim.model, trim.trim, warning)
                summary.sanity_warnings += 1

            if trim.key in deduped:
                log.warning("duplicate trim %s — keeping first occurrence", trim.key)
                summary.duplicates += 1
                continue

            deduped[trim.key] = trim
            summary.null_fields += _count_nulls(trim)
            kept += 1

        summary.make_counts[provider.make] = summary.make_counts.get(provider.make, 0) + kept

    trims = sorted(deduped.values(), key=lambda t: t.key)
    summary.total = len(trims)
    write_output(trims, out_path)

    log.info(
        "run complete: %d trim(s) across %s | %d null field(s), %d sanity warning(s), "
        "%d duplicate(s), %d skipped",
        summary.total,
        ", ".join(f"{m}={c}" for m, c in summary.make_counts.items()) or "none",
        summary.null_fields,
        summary.sanity_warnings,
        summary.duplicates,
        summary.skipped,
    )
    return summary
