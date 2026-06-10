"""Tiny retry decorator for transient collection failures.

Today providers read a local JSON file, so retries rarely trigger. The seam is
here deliberately: when a provider's ``collect`` becomes an HTTP/scraper call,
wrapping the fetch with ``@with_retry`` is the only change needed.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

log = logging.getLogger(__name__)


def with_retry(
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry ``func`` on ``exceptions`` with exponential backoff.

    Re-raises the last exception once ``attempts`` is exhausted.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = base_delay
            last_exc: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == attempts:
                        break
                    log.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__name__,
                        attempt,
                        attempts,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= backoff
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator
