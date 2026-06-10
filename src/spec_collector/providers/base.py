"""Provider contract and a shared JSON-file-backed implementation.

The extension seam: adding an OEM means subclassing ``JsonSourceProvider`` (or
implementing ``OEMProvider`` directly), dropping a ``source_data.json`` next to
it, and registering it. Nothing downstream of ``collect()`` changes.
"""

from __future__ import annotations

import abc
import json
import logging
from pathlib import Path

from ..errors import CollectionError
from ..retry import with_retry

log = logging.getLogger(__name__)


class OEMProvider(abc.ABC):
    """A source of raw spec records for a single OEM make."""

    make: str

    @abc.abstractmethod
    def available_models(self) -> list[str]:
        """Model names this provider can supply."""

    @abc.abstractmethod
    def collect(self, models: list[str] | None = None) -> list[dict]:
        """Return raw, provider-shaped records, optionally filtered by model.

        Raw records carry free-text values (e.g. ``"All-Wheel Drive"``); the
        shared normalization layer maps them to the canonical schema. Missing
        fields are simply absent — providers never invent values.
        """


class JsonSourceProvider(OEMProvider):
    """Provider backed by a curated ``source_data.json`` file.

    File shape::

        {"make": "Toyota", "source": "...", "trims": [ {raw record}, ... ]}

    The file read is wrapped with retry/backoff so that swapping the source for
    a network fetch later is a drop-in change.
    """

    make: str = ""

    def __init__(self, data_path: Path) -> None:
        self._data_path = data_path
        self._raw = self._load_source()

    @with_retry(attempts=3, exceptions=(OSError,))
    def _read_text(self) -> str:
        # Retried only on transient I/O. A missing file is handled up front in
        # _load_source — retrying a path that does not exist is pointless.
        return self._data_path.read_text(encoding="utf-8")

    def _load_source(self) -> dict:
        name = self.make or "provider"
        if not self._data_path.is_file():
            raise CollectionError(f"{name}: source not found: {self._data_path}")
        try:
            text = self._read_text()
        except OSError as exc:
            raise CollectionError(
                f"{name}: cannot read source {self._data_path}: {exc}"
            ) from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CollectionError(
                f"{name}: malformed JSON in {self._data_path}: {exc}"
            ) from exc
        if "trims" not in data:
            raise CollectionError(f"{name}: source {self._data_path} has no 'trims'")
        return data

    def available_models(self) -> list[str]:
        return sorted({str(t["model"]) for t in self._raw["trims"]})

    def collect(self, models: list[str] | None = None) -> list[dict]:
        source = self._raw.get("source")
        make = self._raw.get("make", self.make)

        wanted = {m.strip().lower() for m in models} if models else None
        if wanted is not None:
            unknown = wanted - {m.lower() for m in self.available_models()}
            if unknown:
                log.warning(
                    "%s: no data for requested model(s): %s",
                    make,
                    ", ".join(sorted(unknown)),
                )

        records: list[dict] = []
        for trim in self._raw["trims"]:
            if wanted is not None and str(trim["model"]).lower() not in wanted:
                continue
            record = dict(trim)
            record.setdefault("make", make)
            record["source"] = source
            records.append(record)

        log.info(
            "%s: collected %d raw record(s)%s",
            make,
            len(records),
            f" for models={sorted(wanted)}" if wanted else "",
        )
        return records
