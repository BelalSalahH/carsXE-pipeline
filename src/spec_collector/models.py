"""Canonical, downstream-facing data model for a single vehicle trim.

The schema is intentionally flat and stable: this is the contract every OEM
provider must normalize into, regardless of how its raw source is shaped.
Unconfirmed values are ``None`` (serialized as JSON ``null``) — never guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FuelType(str, Enum):
    GAS = "gas"
    HYBRID = "hybrid"
    PHEV = "phev"
    EV = "ev"
    DIESEL = "diesel"


class Drivetrain(str, Enum):
    FWD = "FWD"
    RWD = "RWD"
    AWD = "AWD"
    FOUR_WD = "4WD"


@dataclass(frozen=True, slots=True)
class Dimensions:
    """Exterior dimensions in inches; any unknown axis is ``None``."""

    length_in: float | None = None
    width_in: float | None = None
    height_in: float | None = None
    wheelbase_in: float | None = None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "length_in": self.length_in,
            "width_in": self.width_in,
            "height_in": self.height_in,
            "wheelbase_in": self.wheelbase_in,
        }


@dataclass(frozen=True, slots=True)
class Trim:
    """One normalized record, uniquely identified by year/make/model/trim."""

    year: int
    make: str
    model: str
    trim: str
    base_msrp: int | None = None
    fuel_type: FuelType | None = None
    horsepower: int | None = None
    drivetrain: Drivetrain | None = None
    seating_capacity: int | None = None
    dimensions: Dimensions = field(default_factory=Dimensions)
    notes: str | None = None
    source: str | None = None

    @property
    def key(self) -> tuple[int, str, str, str]:
        return (self.year, self.make, self.model, self.trim)

    def to_dict(self) -> dict[str, object]:
        return {
            "year": self.year,
            "make": self.make,
            "model": self.model,
            "trim": self.trim,
            "base_msrp": self.base_msrp,
            "fuel_type": self.fuel_type.value if self.fuel_type else None,
            "horsepower": self.horsepower,
            "drivetrain": self.drivetrain.value if self.drivetrain else None,
            "seating_capacity": self.seating_capacity,
            "dimensions": self.dimensions.to_dict(),
            "notes": self.notes,
            "source": self.source,
        }
