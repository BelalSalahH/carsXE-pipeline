"""Toyota provider — the default OEM."""

from __future__ import annotations

from pathlib import Path

from ..base import JsonSourceProvider

_DATA_PATH = Path(__file__).parent / "source_data.json"


class ToyotaProvider(JsonSourceProvider):
    make = "Toyota"

    def __init__(self) -> None:
        super().__init__(_DATA_PATH)
