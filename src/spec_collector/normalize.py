"""Normalization: raw provider records -> canonical ``Trim``.

OEM-agnostic and the single place where vocabulary mapping, unit coercion, and
the null-over-guess rule live. If a value is absent or unrecognized, the field
becomes ``None`` — we never substitute a default.
"""

from __future__ import annotations

import logging

from .errors import NormalizationError
from .models import Dimensions, Drivetrain, FuelType, Trim

log = logging.getLogger(__name__)

_FUEL_MAP: dict[str, FuelType] = {
    "gas": FuelType.GAS,
    "gasoline": FuelType.GAS,
    "petrol": FuelType.GAS,
    "hybrid": FuelType.HYBRID,
    "hev": FuelType.HYBRID,
    "phev": FuelType.PHEV,
    "plug-in hybrid": FuelType.PHEV,
    "plug in hybrid": FuelType.PHEV,
    "ev": FuelType.EV,
    "electric": FuelType.EV,
    "bev": FuelType.EV,
    "diesel": FuelType.DIESEL,
}

_DRIVETRAIN_MAP: dict[str, Drivetrain] = {
    "fwd": Drivetrain.FWD,
    "front-wheel drive": Drivetrain.FWD,
    "front wheel drive": Drivetrain.FWD,
    "rwd": Drivetrain.RWD,
    "rear-wheel drive": Drivetrain.RWD,
    "rear wheel drive": Drivetrain.RWD,
    "awd": Drivetrain.AWD,
    "all-wheel drive": Drivetrain.AWD,
    "all wheel drive": Drivetrain.AWD,
    "4wd": Drivetrain.FOUR_WD,
    "4x4": Drivetrain.FOUR_WD,
    "four-wheel drive": Drivetrain.FOUR_WD,
}

_IDENTITY_FIELDS = ("year", "make", "model", "trim")


def _map_fuel(value: object) -> FuelType | None:
    if value is None:
        return None
    mapped = _FUEL_MAP.get(str(value).strip().lower())
    if mapped is None:
        log.warning("unrecognized fuel_type %r -> null", value)
    return mapped


def _map_drivetrain(value: object) -> Drivetrain | None:
    if value is None:
        return None
    mapped = _DRIVETRAIN_MAP.get(str(value).strip().lower())
    if mapped is None:
        log.warning("unrecognized drivetrain %r -> null", value)
    return mapped


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(round(float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        log.warning("non-numeric integer value %r -> null", value)
        return None


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        log.warning("non-numeric float value %r -> null", value)
        return None


def normalize_record(raw: dict) -> Trim:
    """Map one raw record to a canonical ``Trim``.

    Raises ``NormalizationError`` only when an identity field is missing — those
    cannot be defaulted to null without producing an unusable record.
    """
    missing = [f for f in _IDENTITY_FIELDS if raw.get(f) in (None, "")]
    if missing:
        raise NormalizationError(
            f"record missing identity field(s) {missing}: {raw!r}"
        )

    dims_raw = raw.get("dimensions") or {}
    dimensions = Dimensions(
        length_in=_to_float(dims_raw.get("length")),
        width_in=_to_float(dims_raw.get("width")),
        height_in=_to_float(dims_raw.get("height")),
        wheelbase_in=_to_float(dims_raw.get("wheelbase")),
    )

    return Trim(
        year=int(raw["year"]),
        make=str(raw["make"]),
        model=str(raw["model"]),
        trim=str(raw["trim"]),
        base_msrp=_to_int(raw.get("base_msrp")),
        fuel_type=_map_fuel(raw.get("fuel_type")),
        horsepower=_to_int(raw.get("horsepower")),
        drivetrain=_map_drivetrain(raw.get("drivetrain")),
        seating_capacity=_to_int(raw.get("seating_capacity")),
        dimensions=dimensions,
        notes=raw.get("notes"),
        source=raw.get("source"),
    )


# Plausibility bounds for the sanity pass. Outliers are flagged, not dropped —
# data honesty means surfacing the doubt, not silently editing the value.
_HP_RANGE = (50, 1500)
_MSRP_RANGE = (10_000, 250_000)
_SEATS_RANGE = (1, 9)


def sanity_warnings(trim: Trim) -> list[str]:
    """Return human-readable warnings for implausible (but non-null) values."""
    warnings: list[str] = []
    if trim.horsepower is not None and not (
        _HP_RANGE[0] <= trim.horsepower <= _HP_RANGE[1]
    ):
        warnings.append(f"horsepower {trim.horsepower} outside {_HP_RANGE}")
    if trim.base_msrp is not None and not (
        _MSRP_RANGE[0] <= trim.base_msrp <= _MSRP_RANGE[1]
    ):
        warnings.append(f"base_msrp {trim.base_msrp} outside {_MSRP_RANGE}")
    if trim.seating_capacity is not None and not (
        _SEATS_RANGE[0] <= trim.seating_capacity <= _SEATS_RANGE[1]
    ):
        warnings.append(f"seating_capacity {trim.seating_capacity} outside {_SEATS_RANGE}")
    return warnings
