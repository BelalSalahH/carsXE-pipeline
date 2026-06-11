"""Honda provider — multi-source: curated specs reconciled with EPA drivetrain.

Curated data supplies HP / MSRP / fuel / seating / dimensions; EPA supplies the
authoritative drivetrain. Each field's origin is recorded in ``field_sources``
so the output can show exactly where every value came from.
"""

from __future__ import annotations

from pathlib import Path

from ..base import JsonSourceProvider
from ..sources.epa import EpaDrivetrainSource

_DATA_PATH = Path(__file__).parent / "source_data.json"
_CACHE_PATH = Path(__file__).parent.parent / "sources" / "cache" / "epa_honda.json"

_CURATED_ID = "curated:honda.com"
_SPEC_FIELDS = (
    "base_msrp",
    "fuel_type",
    "horsepower",
    "drivetrain",
    "seating_capacity",
    "dimensions",
)


class HondaProvider(JsonSourceProvider):
    make = "Honda"

    def __init__(
        self,
        epa: EpaDrivetrainSource | None = None,
        *,
        refresh: bool = False,
        allow_network: bool = True,
    ) -> None:
        super().__init__(_DATA_PATH)
        self._epa = epa or EpaDrivetrainSource(
            "Honda", _CACHE_PATH, refresh=refresh, allow_network=allow_network
        )

    def collect(self, models: list[str] | None = None) -> list[dict]:
        records = super().collect(models)
        for rec in records:
            field_sources = {f: _CURATED_ID for f in _SPEC_FIELDS}

            epa_model = rec.get("epa_model")
            if epa_model:
                drive = self._epa.drivetrain_for(int(rec["year"]), str(epa_model))
                if drive:
                    rec["drivetrain"] = drive  # EPA overrides curated drivetrain
                    field_sources["drivetrain"] = self._epa.source_id

            rec["field_sources"] = field_sources
        self._epa.flush()
        return records
