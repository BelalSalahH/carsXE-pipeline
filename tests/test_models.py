import dataclasses
from collector.models import TrimSpec, make_key, FUEL_TYPES, DRIVETRAINS


def test_make_key_format():
    assert make_key("Toyota", "Camry", 2026, "LE") == "Toyota|Camry|2026|LE"


def test_trimspec_defaults_are_null():
    spec = TrimSpec(
        key="Toyota|Camry|2026|LE", year=2026, spec_year=2026,
        make="Toyota", model="Camry", trim="LE",
    )
    assert spec.base_msrp_usd is None
    assert spec.fuel_type is None
    assert spec.dimensions_in == {
        "length": None, "width": None, "height": None, "wheelbase": None
    }


def test_trimspec_asdict_roundtrips():
    spec = TrimSpec(
        key="Toyota|Camry|2026|LE", year=2026, spec_year=2026,
        make="Toyota", model="Camry", trim="LE", horsepower_hp=225,
    )
    d = dataclasses.asdict(spec)
    assert d["horsepower_hp"] == 225
    assert set(d.keys()) == {
        "key", "year", "spec_year", "make", "model", "trim",
        "base_msrp_usd", "fuel_type", "horsepower_hp", "drivetrain",
        "seating_capacity", "dimensions_in", "source_url", "as_of", "notes",
    }


def test_enum_sets():
    assert FUEL_TYPES == {"gas", "hybrid", "phev", "ev"}
    assert DRIVETRAINS == {"FWD", "AWD", "4WD", "RWD"}
