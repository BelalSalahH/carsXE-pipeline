"""Export: canonical trims -> output.json.

Atomic write (temp file + rename) so a failed/interrupted run never leaves a
half-written artifact in place.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from .models import Trim

log = logging.getLogger(__name__)


def write_output(trims: list[Trim], path: Path) -> None:
    records = [t.to_dict() for t in trims]
    payload = json.dumps(records, indent=2, ensure_ascii=False)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload + "\n", encoding="utf-8")
    os.replace(tmp, path)

    log.info("wrote %d record(s) to %s", len(records), path)
