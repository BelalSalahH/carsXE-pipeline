"""Toyota provider — the default OEM."""

from __future__ import annotations

from pathlib import Path

from ..base import JsonSourceProvider

_DATA_PATH = Path(__file__).parent / "source_data.json"


class ToyotaProvider(JsonSourceProvider):
    make = "Toyota"

    # Accepts the shared provider kwargs for a uniform registry call; Toyota is
    # single-source today, so refresh/allow_network are not used.
    def __init__(self, *, refresh: bool = False, allow_network: bool = True) -> None:
        super().__init__(_DATA_PATH)
