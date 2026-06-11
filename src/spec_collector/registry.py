"""OEM registry: make name -> provider. The one place new OEMs are wired in."""

from __future__ import annotations

from .errors import UnknownMakeError
from .providers.base import OEMProvider
from .providers.honda.provider import HondaProvider
from .providers.toyota.provider import ToyotaProvider

# To add an OEM: implement a provider + curated source_data.json, add one entry.
_PROVIDERS: dict[str, type[OEMProvider]] = {
    "toyota": ToyotaProvider,
    "honda": HondaProvider,
}

DEFAULT_MAKE = "toyota"


def available_makes() -> list[str]:
    return sorted(_PROVIDERS)


def get_provider(make: str, *, refresh: bool = False) -> OEMProvider:
    key = make.strip().lower()
    provider_cls = _PROVIDERS.get(key)
    if provider_cls is None:
        raise UnknownMakeError(
            f"unknown make {make!r}; available: {', '.join(available_makes())}"
        )
    return provider_cls(refresh=refresh)
