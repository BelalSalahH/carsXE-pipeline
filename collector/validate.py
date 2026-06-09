from typing import List
from collector.models import TrimSpec

_RANGES = {
    "base_msrp_usd": (15000, 120000),
    "horsepower_hp": (70, 1000),
    "seating_capacity": (2, 8),
}
_DIM_RANGES = {
    "length": (140, 260),
    "width": (60, 90),
    "height": (50, 90),
    "wheelbase": (90, 160),
}
_IDENTITY = ("year", "spec_year", "make", "model", "trim")


def validate_spec(spec: TrimSpec) -> List[str]:
    warnings: List[str] = []

    for fieldname in _IDENTITY:
        value = getattr(spec, fieldname)
        if value in (None, ""):
            warnings.append(f"{spec.key}: missing identity field '{fieldname}'")

    for fieldname, (low, high) in _RANGES.items():
        value = getattr(spec, fieldname)
        if value is not None and not (low <= value <= high):
            warnings.append(
                f"{spec.key}: {fieldname}={value} outside plausible [{low}, {high}]"
            )

    for dim, (low, high) in _DIM_RANGES.items():
        value = spec.dimensions_in.get(dim)
        if value is not None and not (low <= value <= high):
            warnings.append(
                f"{spec.key}: dimensions_in.{dim}={value} outside plausible [{low}, {high}]"
            )

    return warnings
