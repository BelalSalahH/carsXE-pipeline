import json

from spec_collector.pipeline import run
from spec_collector.registry import available_makes


def test_run_writes_output_for_all_makes(tmp_path):
    out = tmp_path / "output.json"
    summary = run(available_makes(), None, out)

    records = json.loads(out.read_text())
    assert len(records) == summary.total > 0

    makes = {r["make"] for r in records}
    assert {"Toyota", "Honda"} <= makes

    required = {
        "year", "make", "model", "trim", "base_msrp", "fuel_type",
        "horsepower", "drivetrain", "seating_capacity", "dimensions",
    }
    for rec in records:
        assert required <= set(rec)
        assert set(rec["dimensions"]) == {
            "length_in", "width_in", "height_in", "wheelbase_in",
        }


def test_records_unique_by_key(tmp_path):
    out = tmp_path / "output.json"
    run(available_makes(), None, out)
    records = json.loads(out.read_text())
    keys = [(r["year"], r["make"], r["model"], r["trim"]) for r in records]
    assert len(keys) == len(set(keys))


def test_model_filter_limits_output(tmp_path):
    out = tmp_path / "output.json"
    run(["toyota"], ["Tacoma"], out)
    records = json.loads(out.read_text())
    assert {r["model"] for r in records} == {"Tacoma"}


def test_explicit_null_survives_to_output(tmp_path):
    out = tmp_path / "output.json"
    run(["toyota"], ["Tacoma"], out)
    records = json.loads(out.read_text())
    trd_pro = next(r for r in records if r["trim"] == "TRD Pro")
    assert trd_pro["dimensions"]["height_in"] is None
