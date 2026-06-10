import pytest

from spec_collector.errors import UnknownMakeError
from spec_collector.registry import available_makes, get_provider

REQUIRED_RAW_KEYS = {"year", "model", "trim", "make", "source"}


@pytest.mark.parametrize("make", ["toyota", "honda"])
def test_provider_collects_records_with_required_keys(make):
    provider = get_provider(make)
    records = provider.collect()
    assert records, f"{make} returned no records"
    for rec in records:
        assert REQUIRED_RAW_KEYS <= set(rec), f"missing keys in {rec}"


def test_registry_default_and_listing():
    assert "toyota" in available_makes()
    assert "honda" in available_makes()


def test_unknown_make_raises():
    with pytest.raises(UnknownMakeError):
        get_provider("tesla")


def test_model_filter_is_case_insensitive():
    provider = get_provider("toyota")
    records = provider.collect(models=["camry"])
    assert records
    assert {r["model"] for r in records} == {"Camry"}


def test_honda_covers_expected_models():
    models = set(get_provider("honda").available_models())
    assert {"Civic", "Accord", "CR-V"} <= models


def test_unknown_model_filter_warns(caplog):
    provider = get_provider("toyota")
    with caplog.at_level("WARNING"):
        records = provider.collect(models=["Camrry"])
    assert records == []
    assert any("Camrry".lower() in r.message.lower() for r in caplog.records)
