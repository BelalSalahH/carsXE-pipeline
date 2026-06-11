import json

from spec_collector.normalize import normalize_record
from spec_collector.providers.honda.provider import HondaProvider
from spec_collector.providers.sources.epa import EpaDrivetrainSource


def _cache(tmp_path, entries):
    path = tmp_path / "epa.json"
    path.write_text(json.dumps({"entries": entries}))
    return path


def test_epa_offline_returns_cached_drivetrain(tmp_path):
    src = EpaDrivetrainSource(
        "Honda",
        _cache(tmp_path, {"2026|CR-V AWD": "All-Wheel Drive"}),
        allow_network=False,
    )
    assert src.drivetrain_for(2026, "CR-V AWD") == "All-Wheel Drive"


def test_epa_offline_missing_key_returns_none(tmp_path):
    src = EpaDrivetrainSource("Honda", _cache(tmp_path, {}), allow_network=False)
    assert src.drivetrain_for(2026, "CR-V AWD") is None


def test_honda_drivetrain_sourced_from_epa_offline():
    # Uses the committed cache fixture; no network.
    provider = HondaProvider(allow_network=False)
    records = provider.collect(models=["CR-V"])
    by_trim = {r["trim"]: r for r in records}

    assert by_trim["LX"]["drivetrain"] == "Front-Wheel Drive"
    assert by_trim["EX-L"]["drivetrain"] == "All-Wheel Drive"
    for rec in records:
        assert rec["field_sources"]["drivetrain"] == "epa:fueleconomy.gov"
        assert rec["field_sources"]["horsepower"] == "curated:honda.com"


def test_provenance_recorded_per_field():
    raw = {
        "year": 2026, "make": "Honda", "model": "CR-V", "trim": "LX",
        "horsepower": 190, "drivetrain": "All-Wheel Drive",
        "source": "curated:honda.com",
        "field_sources": {"drivetrain": "epa:fueleconomy.gov"},
    }
    trim = normalize_record(raw)
    assert trim.sources["drivetrain"] == "epa:fueleconomy.gov"
    assert trim.sources["horsepower"] == "curated:honda.com"
    # base_msrp is null here -> no provenance entry
    assert "base_msrp" not in trim.sources
