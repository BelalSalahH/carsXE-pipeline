"""Minimal JSON-over-HTTPS GET with sane TLS and retry.

Uses ``certifi``'s CA bundle when available — many environments (incl. some
macOS Python builds) ship without a usable system trust store, which otherwise
fails verification. Falls back to the default context if certifi is absent.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.request

from ...retry import with_retry

log = logging.getLogger(__name__)

_TIMEOUT = 20.0
_USER_AGENT = "spec-collector/0.1 (+https://github.com/BelalSalahH/carsXE-pipeline)"


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover - environment dependent
        log.debug("certifi not installed; using default SSL context")
        return ssl.create_default_context()


@with_retry(attempts=3, exceptions=(OSError,))
def get_json(url: str) -> dict:
    """GET ``url`` and parse JSON. Retries transient network errors."""
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": _USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))
