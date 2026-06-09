from collector.models import TrimSpec
from collector.validate import validate_spec


def _spec(**overrides):
    base = dict(
        key="Toyota|Camry|2026|LE", year=2026, spec_year=2026,
        make="Toyota", model="Camry", trim="LE",
        base_msrp_usd=28700, fuel_type="hybrid", horsepower_hp=225,
        drivetrain="FWD", seating_capacity=5,
        dimensions_in={"length": 193.5, "width": 72.2, "height": 56.9, "wheelbase": 111.2},
    )
    base.update(overrides)
    return TrimSpec(**base)


def test_plausible_spec_has_no_warnings():
    assert validate_spec(_spec()) == []


def test_implausible_horsepower_flagged():
    warnings = validate_spec(_spec(horsepower_hp=9000))
    assert any("horsepower_hp" in w for w in warnings)


def test_implausible_msrp_flagged():
    warnings = validate_spec(_spec(base_msrp_usd=5))
    assert any("base_msrp_usd" in w for w in warnings)


def test_missing_identity_field_flagged():
    warnings = validate_spec(_spec(make=""))
    assert any("make" in w for w in warnings)


def test_null_optional_field_is_not_flagged():
    assert validate_spec(_spec(horsepower_hp=None)) == []
