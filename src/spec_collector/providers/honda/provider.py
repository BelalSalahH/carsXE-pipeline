"""Honda provider — Civic, Accord, CR-V (US market)."""

from __future__ import annotations

from pathlib import Path

from ..base import JsonSourceProvider

_DATA_PATH = Path(__file__).parent / "source_data.json"


class HondaProvider(JsonSourceProvider):
    make = "Honda"

    def __init__(self) -> None:
        super().__init__(_DATA_PATH)
