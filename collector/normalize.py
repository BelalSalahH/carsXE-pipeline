import re
from typing import Optional

from collector.models import TrimSpec, make_key

_FUEL_MAP = {
    "gas": "gas", "gasoline": "gas", "petrol": "gas",
    "hybrid": "hybrid", "hev": "hybrid",
    "plug-in hybrid": "phev", "plugin hybrid": "phev", "phev": "phev",
    "electric": "ev", "bev": "ev", "ev": "ev",
}

_DRIVETRAIN_MAP = {
    "fwd": "FWD", "front-wheel drive": "FWD", "front wheel drive": "FWD",
    "awd": "AWD", "all-wheel drive": "AWD", "all wheel drive": "AWD",
    "4wd": "4WD", "4x4": "4WD", "four-wheel drive": "4WD", "4-wheel drive": "4WD",
    "rwd": "RWD", "4x2": "RWD", "2wd": "RWD", "rear-wheel drive": "RWD",
}


def normalize_fuel(raw) -> Optional[str]:
    if not raw:
        return None
    return _FUEL_MAP.get(str(raw).strip().lower())


def normalize_drivetrain(raw) -> Optional[str]:
    if not raw:
        return None
    return _DRIVETRAIN_MAP.get(str(raw).strip().lower())


def to_int(raw) -> Optional[int]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    cleaned = re.sub(r"[^0-9.]", "", str(raw))
    if cleaned in ("", "."):
        return None
    return int(float(cleaned))


def to_float(raw) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    cleaned = re.sub(r"[^0-9.]", "", str(raw))
    if cleaned in ("", "."):
        return None
    return float(cleaned)


def normalize_row(row: dict) -> TrimSpec:
    year = row["year"]
    make = row["make"]
    model = row["model"]
    trim = row["trim"]
    dims_raw = row.get("dimensions") or {}
    return TrimSpec(
        key=make_key(make, model, year, trim),
        year=year,
        spec_year=row.get("spec_year") or year,
        make=make,
        model=model,
        trim=trim,
        base_msrp_usd=to_int(row.get("base_msrp")),
        fuel_type=normalize_fuel(row.get("fuel_type")),
        horsepower_hp=to_int(row.get("horsepower")),
        drivetrain=normalize_drivetrain(row.get("drivetrain")),
        seating_capacity=to_int(row.get("seating_capacity")),
        dimensions_in={
            "length": to_float(dims_raw.get("length")),
            "width": to_float(dims_raw.get("width")),
            "height": to_float(dims_raw.get("height")),
            "wheelbase": to_float(dims_raw.get("wheelbase")),
        },
        source_url=row.get("source_url"),
        as_of=row.get("as_of"),
        notes=row.get("notes"),
    )
