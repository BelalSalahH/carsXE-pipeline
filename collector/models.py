from dataclasses import dataclass, field
from typing import Optional

FUEL_TYPES = {"gas", "hybrid", "phev", "ev"}
DRIVETRAINS = {"FWD", "AWD", "4WD", "RWD"}


def make_key(make: str, model: str, year: int, trim: str) -> str:
    return f"{make}|{model}|{year}|{trim}"


def _empty_dimensions() -> dict:
    return {"length": None, "width": None, "height": None, "wheelbase": None}


@dataclass
class TrimSpec:
    key: str
    year: int
    spec_year: int
    make: str
    model: str
    trim: str
    base_msrp_usd: Optional[int] = None
    fuel_type: Optional[str] = None
    horsepower_hp: Optional[int] = None
    drivetrain: Optional[str] = None
    seating_capacity: Optional[int] = None
    dimensions_in: dict = field(default_factory=_empty_dimensions)
    source_url: Optional[str] = None
    as_of: Optional[str] = None
    notes: Optional[str] = None
