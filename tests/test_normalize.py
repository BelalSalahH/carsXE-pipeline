import pytest

from spec_collector.errors import NormalizationError
from spec_collector.models import Drivetrain, FuelType
from spec_collector.normalize import normalize_record, sanity_warnings


def _raw(**overrides):
    base = {
        "year": 2026,
        "make": "Toyota",
        "model": "Camry",
        "trim": "LE",
        "base_msrp": 28700,
        "fuel_type": "Hybrid",
        "horsepower": 225,
        "drivetrain": "Front-Wheel Drive",
        "seating_capacity": 5,
        "dimensions": {"length": 193.5, "width": 72.2, "height": 56.9, "wheelbase": 111.2},
    }
    base.update(overrides)
    return base


def test_maps_free_text_vocabulary():
    trim = normalize_record(_raw(fuel_type="Plug-in Hybrid", drivetrain="All-Wheel Drive"))
    assert trim.fuel_type is FuelType.PHEV
    assert trim.drivetrain is Drivetrain.AWD


def test_unrecognized_values_become_null():
    trim = normalize_record(_raw(fuel_type="fusion", drivetrain="6WD"))
    assert trim.fuel_type is None
    assert trim.drivetrain is None


def test_missing_optional_fields_are_null_not_guessed():
    raw = _raw()
    del raw["base_msrp"]
    del raw["horsepower"]
    raw["dimensions"] = {"length": 193.5}
    trim = normalize_record(raw)
    assert trim.base_msrp is None
    assert trim.horsepower is None
    assert trim.dimensions.width_in is None
    assert trim.dimensions.length_in == 193.5


def test_explicit_null_dimension_preserved():
    trim = normalize_record(_raw(dimensions={"length": 213.0, "height": None}))
    assert trim.dimensions.height_in is None
    assert trim.dimensions.length_in == 213.0


def test_missing_identity_field_raises():
    raw = _raw()
    del raw["trim"]
    with pytest.raises(NormalizationError):
        normalize_record(raw)


def test_sanity_warns_on_implausible_values():
    trim = normalize_record(_raw(horsepower=9000, base_msrp=5))
    warnings = sanity_warnings(trim)
    assert any("horsepower" in w for w in warnings)
    assert any("base_msrp" in w for w in warnings)


def test_to_dict_serializes_enums_to_strings():
    record = normalize_record(_raw()).to_dict()
    assert record["fuel_type"] == "hybrid"
    assert record["drivetrain"] == "FWD"
    assert set(record["dimensions"]) == {"length_in", "width_in", "height_in", "wheelbase_in"}
