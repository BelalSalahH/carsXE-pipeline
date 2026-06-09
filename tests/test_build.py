import json
from pathlib import Path
from collector.build import build

FIXTURE = Path(__file__).parent / "fixtures" / "source_min.json"


def test_build_writes_sorted_deduped_records(tmp_path):
    out = tmp_path / "output.json"
    result = build(source_path=FIXTURE, out_path=out)

    records = json.loads(out.read_text())
    assert len(records) == 2
    keys = [r["key"] for r in records]
    assert keys == sorted(keys)
    assert keys == ["TestMake|Alpha|2026|Base", "TestMake|Beta|2026|Sport"]


def test_build_preserves_nulls(tmp_path):
    out = tmp_path / "output.json"
    build(source_path=FIXTURE, out_path=out)
    records = json.loads(out.read_text())
    beta = next(r for r in records if r["model"] == "Beta")
    assert beta["base_msrp_usd"] is None
    assert beta["horsepower_hp"] is None
    assert beta["spec_year"] == 2025


def test_build_report_counts(tmp_path):
    out = tmp_path / "output.json"
    result = build(source_path=FIXTURE, out_path=out)
    assert result["record_count"] == 2
    assert result["duplicate_count"] == 1
    assert "warnings" in result
