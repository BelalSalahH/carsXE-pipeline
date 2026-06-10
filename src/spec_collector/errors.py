"""Exception hierarchy for the spec collector.

Structural failures (bad config, unknown make, unreadable source) abort the run.
Data-level problems are handled in-place by emitting ``null`` and logging, so they
do not raise.
"""

from __future__ import annotations


class SpecCollectorError(Exception):
    """Base class for all collector errors."""


class UnknownMakeError(SpecCollectorError):
    """Requested OEM has no registered provider."""


class CollectionError(SpecCollectorError):
    """A provider could not read its underlying source."""


class NormalizationError(SpecCollectorError):
    """A raw record is missing an identity field (year/make/model/trim)."""
