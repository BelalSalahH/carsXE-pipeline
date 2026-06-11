"""EPA fueleconomy.gov source — supplies authoritative **drivetrain**.

EPA exposes drivetrain via its model taxonomy (e.g. "CR-V FWD" vs "CR-V AWD")
and the ``drive`` field, which is uniform within an EPA model name. It does not
expose horsepower, MSRP, seating, or dimensions, so those stay curated.

Cache-first with live refresh:
- A committed cache fixture makes runs reproducible and offline-capable (and
  lets tests avoid the network entirely via ``allow_network=False``).
- On a cache miss (or ``refresh=True``) it fetches live and updates the cache.
- If the network is unavailable, it falls back to whatever the cache holds.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from pathlib import Path

from .http import get_json

log = logging.getLogger(__name__)

_BASE = "https://www.fueleconomy.gov/ws/rest/vehicle"


class EpaDrivetrainSource:
    source_id = "epa:fueleconomy.gov"

    def __init__(
        self,
        make: str,
        cache_path: Path,
        *,
        refresh: bool = False,
        allow_network: bool = True,
    ) -> None:
        self._make = make
        self._cache_path = cache_path
        self._refresh = refresh
        self._allow_network = allow_network
        self._cache = self._load_cache()
        self._dirty = False

    def _load_cache(self) -> dict:
        if self._cache_path.is_file():
            try:
                return json.loads(self._cache_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("EPA cache unreadable (%s); starting empty", exc)
        return {"_meta": {"source": "EPA fueleconomy.gov web services"}, "entries": {}}

    def drivetrain_for(self, year: int, epa_model: str) -> str | None:
        """Return raw EPA drive string (e.g. "Front-Wheel Drive") or ``None``."""
        entries: dict[str, str] = self._cache.setdefault("entries", {})
        key = f"{year}|{epa_model}"

        if not self._refresh and key in entries:
            return entries[key]
        if not self._allow_network:
            return entries.get(key)

        drive = self._fetch_drive(year, epa_model)
        if drive is not None:
            entries[key] = drive
            self._dirty = True
            return drive
        return entries.get(key)  # network failed — fall back to cache

    def _fetch_drive(self, year: int, epa_model: str) -> str | None:
        model_q = urllib.parse.quote(epa_model)
        menu_url = f"{_BASE}/menu/options?year={year}&make={self._make}&model={model_q}"
        try:
            menu = get_json(menu_url)
        except OSError as exc:
            log.warning("EPA lookup failed for %s %s: %s", year, epa_model, exc)
            return None

        items = menu.get("menuItem", [])
        if isinstance(items, dict):
            items = [items]
        if not items:
            log.warning("EPA has no options for %s %s", year, epa_model)
            return None

        try:
            detail = get_json(f"{_BASE}/{items[0]['value']}")
        except OSError as exc:
            log.warning("EPA detail failed for %s %s: %s", year, epa_model, exc)
            return None
        return detail.get("drive")

    def flush(self) -> None:
        """Persist any newly fetched entries back to the cache file (atomic)."""
        if not self._dirty:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._cache_path.with_name(self._cache_path.name + ".tmp")
        tmp.write_text(json.dumps(self._cache, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self._cache_path)
        self._dirty = False
        log.info("EPA cache updated: %s", self._cache_path)
