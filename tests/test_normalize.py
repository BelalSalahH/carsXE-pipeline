from collector.normalize import (
    normalize_fuel, normalize_drivetrain, to_int, to_float,
)


def test_normalize_fuel_synonyms():
    assert normalize_fuel("Gas") == "gas"
    assert normalize_fuel("Gasoline") == "gas"
    assert normalize_fuel("Hybrid") == "hybrid"
    assert normalize_fuel("Plug-in Hybrid") == "phev"
    assert normalize_fuel("PHEV") == "phev"
    assert normalize_fuel("Electric") == "ev"
    assert normalize_fuel("BEV") == "ev"


def test_normalize_fuel_unknown_is_none():
    assert normalize_fuel("") is None
    assert normalize_fuel(None) is None
    assert normalize_fuel("diesel-ish") is None


def test_normalize_drivetrain_synonyms():
    assert normalize_drivetrain("FWD") == "FWD"
    assert normalize_drivetrain("Front-Wheel Drive") == "FWD"
    assert normalize_drivetrain("AWD") == "AWD"
    assert normalize_drivetrain("All-Wheel Drive") == "AWD"
    assert normalize_drivetrain("4WD") == "4WD"
    assert normalize_drivetrain("4x4") == "4WD"
    assert normalize_drivetrain("RWD") == "RWD"
    assert normalize_drivetrain("4x2") == "RWD"
    assert normalize_drivetrain("mystery") is None


def test_to_int_strips_symbols():
    assert to_int("28,700") == 28700
    assert to_int("$35,420") == 35420
    assert to_int("225 hp") == 225
    assert to_int(5) == 5
    assert to_int("") is None
    assert to_int(None) is None
    assert to_int("n/a") is None


def test_to_float_strips_units():
    assert to_float("193.5 in") == 193.5
    assert to_float("72.2") == 72.2
    assert to_float(56.9) == 56.9
    assert to_float("") is None
    assert to_float(None) is None


from collector.normalize import normalize_row
from collector.models import TrimSpec


def _raw_row(**overrides):
    row = {
        "year": 2026, "spec_year": 2026, "make": "Toyota",
        "model": "Camry", "trim": "LE", "base_msrp": "28,700",
        "fuel_type": "Hybrid", "horsepower": "225 hp", "drivetrain": "FWD",
        "seating_capacity": 5,
        "dimensions": {"length": "193.5 in", "width": "72.2 in",
                       "height": "56.9 in", "wheelbase": "111.2 in"},
        "source_url": "https://example.com", "as_of": "2026-06-09", "notes": None,
    }
    row.update(overrides)
    return row


def test_normalize_row_full():
    spec = normalize_row(_raw_row())
    assert isinstance(spec, TrimSpec)
    assert spec.key == "Toyota|Camry|2026|LE"
    assert spec.base_msrp_usd == 28700
    assert spec.fuel_type == "hybrid"
    assert spec.horsepower_hp == 225
    assert spec.drivetrain == "FWD"
    assert spec.seating_capacity == 5
    assert spec.dimensions_in == {
        "length": 193.5, "width": 72.2, "height": 56.9, "wheelbase": 111.2
    }
    assert spec.source_url == "https://example.com"


def test_normalize_row_missing_fields_become_null():
    spec = normalize_row(_raw_row(base_msrp=None, horsepower="", dimensions={}))
    assert spec.base_msrp_usd is None
    assert spec.horsepower_hp is None
    assert spec.dimensions_in == {
        "length": None, "width": None, "height": None, "wheelbase": None
    }


def test_normalize_row_spec_year_defaults_to_year():
    row = _raw_row()
    del row["spec_year"]
    spec = normalize_row(row)
    assert spec.spec_year == 2026
