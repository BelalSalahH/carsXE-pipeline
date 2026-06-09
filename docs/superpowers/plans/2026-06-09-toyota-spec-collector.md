# Toyota 2026 Spec Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small, re-runnable Python script that normalizes curated OEM-sourced 2026 Toyota spec data (Camry, RAV4, Tacoma) into a clean, schema-consistent `output.json` keyed by Year/Make/Model/Trim.

**Architecture:** A curated, provenance-tagged `source_data.json` (values transcribed from Toyota's official US sources — toyota.com and pressroom.toyota.com) is the source of record. A small package reads it, normalizes fuel/drivetrain/numeric fields to a canonical schema, runs a plausibility + data-honesty validation pass (null over guesses), and emits a flat array of trim records plus a run report. The curated approach was chosen over live scraping (brittle) and Toyota's gated/telematics-shaped developer API (inaccessible, wrong domain) — see decision notes below. Re-running is deterministic; adding a model year means editing the source file and re-running.

**Tech Stack:** Python 3.10+, standard library only at runtime (`json`, `dataclasses`, `argparse`, `pathlib`). `pytest` for tests. No runtime third-party dependencies.

### Decision notes (carried from brainstorming)
- **No usable official API.** Toyota's Developer Portal Vehicle/Get-Vehicle-Configuration APIs are gated (403, partner-only) and telematics/dealer-shaped, not a public per-trim spec catalog. NHTSA vPIC is public+stable but lacks MSRP/HP/dimensions per trim. Configurator backend is undocumented and brittle. Hence curated.
- **Data honesty is a graded criterion.** Any field not confirmed from an OEM source is `null`. Never guess or interpolate. Provenance (`source_url`, `as_of`) is carried into every output record.
- **Keep it small.** ~5 trims/model, 3 models. Don't gold-plate.

---

## File Structure

```
carxe/
  source_data.json              # curated OEM input, provenance-tagged (hand-edited)
  collector/
    __init__.py
    models.py                   # TrimSpec dataclass, canonical enums, make_key()
    normalize.py                # field normalizers + normalize_row() -> TrimSpec
    validate.py                 # plausibility ranges + identity checks -> warnings/errors
    build.py                    # load -> normalize -> dedupe -> validate -> write + report; CLI
  tests/
    test_models.py
    test_normalize.py
    test_validate.py
    test_build.py
    fixtures/source_min.json     # tiny synthetic fixture (NOT real Toyota data)
  output.json                   # generated artifact
  requirements.txt
  README.md
```

**Run command (final):** `python -m collector.build` (defaults: `--source source_data.json --out output.json`).

### Canonical output schema (one object per trim, flat array, sorted by `key`)

```json
{
  "key": "Toyota|Camry|2026|LE",
  "year": 2026,
  "spec_year": 2026,
  "make": "Toyota",
  "model": "Camry",
  "trim": "LE",
  "base_msrp_usd": 28700,
  "fuel_type": "hybrid",
  "horsepower_hp": 225,
  "drivetrain": "FWD",
  "seating_capacity": 5,
  "dimensions_in": {"length": 193.5, "width": 72.2, "height": 56.9, "wheelbase": 111.2},
  "source_url": "https://pressroom.toyota.com/...",
  "as_of": "2026-06-09",
  "notes": null
}
```

- `fuel_type` ∈ {`gas`, `hybrid`, `phev`, `ev`} or `null`
- `drivetrain` ∈ {`FWD`, `AWD`, `4WD`, `RWD`} or `null`
- Every numeric field is `int`/`float` or `null`. No strings, no units inside values.

### Raw source row schema (`source_data.json` is a JSON array of these)

```json
{
  "year": 2026,
  "spec_year": 2026,
  "make": "Toyota",
  "model": "Camry",
  "trim": "LE",
  "base_msrp": "28,700",
  "fuel_type": "Hybrid",
  "horsepower": "225 hp",
  "drivetrain": "FWD",
  "seating_capacity": 5,
  "dimensions": {"length": "193.5 in", "width": "72.2 in", "height": "56.9 in", "wheelbase": "111.2 in"},
  "source_url": "https://...",
  "as_of": "2026-06-09",
  "notes": null
}
```

Any field that cannot be confirmed is omitted or set to `null` in the raw row; the normalizer maps it to `null` in output.

---

## Task 0: Project scaffold

**Files:**
- Create: `carxe/requirements.txt`
- Create: `carxe/collector/__init__.py`
- Create: `carxe/tests/__init__.py`
- Create: `carxe/.gitignore`

- [ ] **Step 1: Initialize git and package layout**

Run from `/Users/belalsalah/carxe`:
```bash
git init
mkdir -p collector tests/fixtures docs/superpowers/plans
```

- [ ] **Step 2: Create the files**

`requirements.txt`:
```
pytest>=8.0
```

`collector/__init__.py`:
```python
```
(empty file)

`tests/__init__.py`:
```python
```
(empty file)

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

- [ ] **Step 3: Create venv and install**

Run:
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
```
Expected: pytest installs successfully.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt collector/__init__.py tests/__init__.py .gitignore
git commit -m "chore: scaffold project layout"
```

---

## Task 1: Data model (`models.py`)

**Files:**
- Create: `collector/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'collector.models'`

- [ ] **Step 3: Write minimal implementation**

`collector/models.py`:
```python
from dataclasses import dataclass, field
from typing import Optional

FUEL_TYPES = {"gas", "hybrid", "phev", "ev"}
DRIVETRAINS = {"FWD", "AWD", "4WD", "RWD"}


def make_key(make: str, model: str, year: int, trim: str) -> str:
    return f"{make}|{model}|{year}|{trim}"


def _empty_dimensions() -> dict:
    return {"length": None, "width": None, "height": None, "wheelbase": None}


@dataclass
class TrimSpec:
    key: str
    year: int
    spec_year: int
    make: str
    model: str
    trim: str
    base_msrp_usd: Optional[int] = None
    fuel_type: Optional[str] = None
    horsepower_hp: Optional[int] = None
    drivetrain: Optional[str] = None
    seating_capacity: Optional[int] = None
    dimensions_in: dict = field(default_factory=_empty_dimensions)
    source_url: Optional[str] = None
    as_of: Optional[str] = None
    notes: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add collector/models.py tests/test_models.py
git commit -m "feat: add TrimSpec schema and key generation"
```

---

## Task 2: Field normalizers (`normalize.py`)

**Files:**
- Create: `collector/normalize.py`
- Test: `tests/test_normalize.py`

- [ ] **Step 1: Write the failing test**

`tests/test_normalize.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'collector.normalize'`

- [ ] **Step 3: Write minimal implementation**

`collector/normalize.py`:
```python
import re
from typing import Optional

_FUEL_MAP = {
    "gas": "gas", "gasoline": "gas", "petrol": "gas",
    "hybrid": "hybrid", "hev": "hybrid",
    "plug-in hybrid": "phev", "plugin hybrid": "phev", "phev": "phev",
    "electric": "ev", "bev": "ev", "ev": "ev",
}

_DRIVETRAIN_MAP = {
    "fwd": "FWD", "front-wheel drive": "FWD", "front wheel drive": "FWD",
    "awd": "AWD", "all-wheel drive": "AWD", "all wheel drive": "AWD",
    "4wd": "4WD", "4x4": "4WD", "four-wheel drive": "4WD", "4-wheel drive": "4WD",
    "rwd": "RWD", "4x2": "RWD", "2wd": "RWD", "rear-wheel drive": "RWD",
}


def normalize_fuel(raw) -> Optional[str]:
    if not raw:
        return None
    return _FUEL_MAP.get(str(raw).strip().lower())


def normalize_drivetrain(raw) -> Optional[str]:
    if not raw:
        return None
    return _DRIVETRAIN_MAP.get(str(raw).strip().lower())


def to_int(raw) -> Optional[int]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    cleaned = re.sub(r"[^0-9.]", "", str(raw))
    if cleaned in ("", "."):
        return None
    return int(float(cleaned))


def to_float(raw) -> Optional[float]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    cleaned = re.sub(r"[^0-9.]", "", str(raw))
    if cleaned in ("", "."):
        return None
    return float(cleaned)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalize.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add collector/normalize.py tests/test_normalize.py
git commit -m "feat: add field-level normalizers"
```

---

## Task 3: Row assembler (`normalize_row`)

**Files:**
- Modify: `collector/normalize.py` (append `normalize_row`)
- Test: `tests/test_normalize.py` (append tests)

- [ ] **Step 1: Write the failing test (append to tests/test_normalize.py)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize.py -k normalize_row -v`
Expected: FAIL with `ImportError: cannot import name 'normalize_row'`

- [ ] **Step 3: Write minimal implementation (append to collector/normalize.py)**

```python
from collector.models import TrimSpec, make_key


def normalize_row(row: dict) -> TrimSpec:
    year = row["year"]
    make = row["make"]
    model = row["model"]
    trim = row["trim"]
    dims_raw = row.get("dimensions") or {}
    return TrimSpec(
        key=make_key(make, model, year, trim),
        year=year,
        spec_year=row.get("spec_year") or year,
        make=make,
        model=model,
        trim=trim,
        base_msrp_usd=to_int(row.get("base_msrp")),
        fuel_type=normalize_fuel(row.get("fuel_type")),
        horsepower_hp=to_int(row.get("horsepower")),
        drivetrain=normalize_drivetrain(row.get("drivetrain")),
        seating_capacity=to_int(row.get("seating_capacity")),
        dimensions_in={
            "length": to_float(dims_raw.get("length")),
            "width": to_float(dims_raw.get("width")),
            "height": to_float(dims_raw.get("height")),
            "wheelbase": to_float(dims_raw.get("wheelbase")),
        },
        source_url=row.get("source_url"),
        as_of=row.get("as_of"),
        notes=row.get("notes"),
    )
```

Note: move the `from collector.models import ...` line to the top of the file with the other imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalize.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add collector/normalize.py tests/test_normalize.py
git commit -m "feat: assemble raw rows into normalized TrimSpec"
```

---

## Task 4: Validation (`validate.py`)

**Files:**
- Create: `collector/validate.py`
- Test: `tests/test_validate.py`

- [ ] **Step 1: Write the failing test**

`tests/test_validate.py`:
```python
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
    # null is allowed (data honesty); only out-of-range numbers are flagged
    assert validate_spec(_spec(horsepower_hp=None)) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_validate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'collector.validate'`

- [ ] **Step 3: Write minimal implementation**

`collector/validate.py`:
```python
from typing import List
from collector.models import TrimSpec

# Plausibility ranges (inclusive). None means unconfirmed -> never flagged.
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_validate.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add collector/validate.py tests/test_validate.py
git commit -m "feat: add plausibility and identity validation"
```

---

## Task 5: Build pipeline + CLI (`build.py`)

**Files:**
- Create: `collector/build.py`
- Create: `tests/fixtures/source_min.json`
- Test: `tests/test_build.py`

- [ ] **Step 1: Create the synthetic fixture**

`tests/fixtures/source_min.json` (synthetic — NOT real Toyota data; includes a duplicate key and a missing field on purpose):
```json
[
  {
    "year": 2026, "spec_year": 2026, "make": "TestMake", "model": "Alpha", "trim": "Base",
    "base_msrp": "20,000", "fuel_type": "Gas", "horsepower": "150 hp", "drivetrain": "FWD",
    "seating_capacity": 5,
    "dimensions": {"length": "180 in", "width": "70 in", "height": "55 in", "wheelbase": "105 in"},
    "source_url": "https://example.com/alpha", "as_of": "2026-06-09", "notes": null
  },
  {
    "year": 2026, "spec_year": 2025, "make": "TestMake", "model": "Beta", "trim": "Sport",
    "base_msrp": null, "fuel_type": "Hybrid", "horsepower": "", "drivetrain": "AWD",
    "seating_capacity": 5,
    "dimensions": {"length": "185 in", "width": "72 in", "height": "58 in", "wheelbase": "108 in"},
    "source_url": "https://example.com/beta", "as_of": "2026-06-09",
    "notes": "2026 specs unpublished; using 2025"
  },
  {
    "year": 2026, "spec_year": 2026, "make": "TestMake", "model": "Alpha", "trim": "Base",
    "base_msrp": "21,000", "fuel_type": "Gas", "horsepower": "150 hp", "drivetrain": "FWD",
    "seating_capacity": 5,
    "dimensions": {"length": "180 in", "width": "70 in", "height": "55 in", "wheelbase": "105 in"},
    "source_url": "https://example.com/alpha-dup", "as_of": "2026-06-09", "notes": null
  }
]
```

- [ ] **Step 2: Write the failing test**

`tests/test_build.py`:
```python
import json
from pathlib import Path
from collector.build import build

FIXTURE = Path(__file__).parent / "fixtures" / "source_min.json"


def test_build_writes_sorted_deduped_records(tmp_path):
    out = tmp_path / "output.json"
    result = build(source_path=FIXTURE, out_path=out)

    records = json.loads(out.read_text())
    # 3 rows in, 1 duplicate key -> 2 records out
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_build.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'collector.build'`

- [ ] **Step 4: Write minimal implementation**

`collector/build.py`:
```python
import argparse
import dataclasses
import json
from pathlib import Path
from typing import Optional

from collector.normalize import normalize_row
from collector.validate import validate_spec


def build(source_path: Path, out_path: Path) -> dict:
    rows = json.loads(Path(source_path).read_text())

    specs_by_key = {}
    duplicate_count = 0
    for row in rows:
        spec = normalize_row(row)
        if spec.key in specs_by_key:
            duplicate_count += 1
            continue  # keep first occurrence deterministically
        specs_by_key[spec.key] = spec

    specs = [specs_by_key[k] for k in sorted(specs_by_key)]

    warnings = []
    for spec in specs:
        warnings.extend(validate_spec(spec))

    records = [dataclasses.asdict(s) for s in specs]
    Path(out_path).write_text(json.dumps(records, indent=2) + "\n")

    return {
        "record_count": len(records),
        "duplicate_count": duplicate_count,
        "warnings": warnings,
    }


def _print_report(report: dict, out_path: Path) -> None:
    print(f"Wrote {report['record_count']} records to {out_path}")
    if report["duplicate_count"]:
        print(f"Skipped {report['duplicate_count']} duplicate trim(s) by key")
    if report["warnings"]:
        print(f"{len(report['warnings'])} plausibility/identity warning(s):")
        for w in report["warnings"]:
            print(f"  - {w}")
    else:
        print("No plausibility warnings.")


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Normalize Toyota spec data to output.json")
    parser.add_argument("--source", default="source_data.json", type=Path)
    parser.add_argument("--out", default="output.json", type=Path)
    args = parser.parse_args(argv)
    report = build(args.source, args.out)
    _print_report(report, args.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_build.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests green)

- [ ] **Step 7: Commit**

```bash
git add collector/build.py tests/test_build.py tests/fixtures/source_min.json
git commit -m "feat: add build pipeline with dedupe, validation, and run report"
```

---

## Task 6: Populate curated source data (`source_data.json`)

**This is a data-collection task, not a coding task. Accuracy and honesty are graded here.**

**Files:**
- Create: `carxe/source_data.json`

- [ ] **Step 1: Collect from official Toyota US sources**

For each model (Camry, RAV4, Tacoma), pick ~5 representative trims (skip special editions/packages). For each trim, open the official spec source and record values:
- Primary: `https://www.toyota.com/<model>/` → "Specs" / "Features & Specs" section, and `https://www.toyota.com/configurator/` for Base MSRP.
- Authoritative cross-check: Toyota USA Newsroom spec sheets at `https://pressroom.toyota.com/` (search "<Model> 2026 specifications").

Record the exact `source_url` you took each trim's data from, and today's date as `as_of` (`2026-06-09`).

**Rules (graded):**
- If a 2026 spec sheet is not published for a trim, use the latest available year, set `spec_year` to that year, and put a short explanation in `notes`.
- Any value you cannot confirm from the source → set the field to `null` (or omit it). **Do not guess, interpolate, or copy from a third-party aggregator.**
- Base MSRP is the trim's starting price excluding destination/options, in whole USD.
- Horsepower: if a trim offers multiple powertrains, record the base/standard engine's HP and note the choice.

- [ ] **Step 2: Write `source_data.json`**

A JSON array of raw rows matching the raw-source schema (see File Structure section). One fully-worked example row (verify the values against the live source before committing — do not ship these numbers unverified):
```json
[
  {
    "year": 2026, "spec_year": 2026, "make": "Toyota", "model": "Camry", "trim": "LE",
    "base_msrp": null, "fuel_type": "Hybrid", "horsepower": null, "drivetrain": "FWD",
    "seating_capacity": 5,
    "dimensions": {"length": null, "width": null, "height": null, "wheelbase": null},
    "source_url": "https://www.toyota.com/camry/", "as_of": "2026-06-09",
    "notes": "fill confirmed values from source; leave unconfirmed fields null"
  }
]
```
Replace this with ~15 real, source-verified rows (≈5 per model). Leave any unconfirmed field `null`.

- [ ] **Step 3: Generate and sanity-check output**

Run:
```bash
python -m collector.build
```
Expected: prints `Wrote N records to output.json` and a warnings section. Read the warnings — every flagged value must be re-checked against its source. A real out-of-range value that the source confirms can stay (note it); a transcription error must be fixed in `source_data.json` and the build re-run.

- [ ] **Step 4: Commit**

```bash
git add source_data.json output.json
git commit -m "data: add curated 2026 Toyota source specs and generated output"
```

---

## Task 7: README and final verification

**Files:**
- Create: `carxe/README.md`

- [ ] **Step 1: Write README.md**

`README.md` must cover exactly the assessment's required sections:
```markdown
# Toyota 2026 Spec Collector

Re-runnable script that normalizes curated OEM 2026 spec data for Toyota Camry,
RAV4, and Tacoma into a clean `output.json` keyed by Year/Make/Model/Trim.

## How to run
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m collector.build            # reads source_data.json -> writes output.json
pytest                               # run the test suite
```

## Sources and why
Source of record is Toyota's own US channels: toyota.com Features & Specs +
configurator (Base MSRP), cross-checked against Toyota USA Newsroom
(pressroom.toyota.com) spec sheets. Rationale: these are OEM-grade and
authoritative. Toyota's developer API is gated/partner-only and telematics-shaped
(no public per-trim spec catalog); NHTSA vPIC is public but lacks MSRP/HP/dimensions;
configurator scraping is brittle. A curated, provenance-tagged source file gives
accurate + stable + re-runnable data that never breaks on a site redesign. Each
record carries `source_url` and `as_of` for auditability.

## Missing data and duplicate trims
Any field not confirmed from an OEM source is `null` — never guessed. Where 2026
specs are unpublished, the latest year is used, recorded in `spec_year` with a
`notes` explanation. Duplicate trims (same Year|Make|Model|Trim key) are deduped
deterministically (first occurrence wins; count reported). A plausibility pass
flags out-of-range MSRP/HP/seating/dimensions for human review.

## Known gaps / with more time
- Multi-source reconciliation (e.g., confirm HP/dimensions against pressroom PDFs
  programmatically) and per-field source confidence.
- Optional NHTSA vPIC cross-check to validate make/model/year.
- Powertrain variants per trim (currently base engine only).

## Scheduling re-runs (design, not deployed)
Run `python -m collector.build` on a monthly cron (e.g. GitHub Actions scheduled
workflow). A thin pre-step would poll Toyota Newsroom for new model-year spec
sheets; when a new year appears, it opens a PR adding rows to `source_data.json`
for human verification before merge. Because the build is deterministic and the
data is provenance-tagged, diffs in `output.json` are reviewable and auditable.
Catching a new model year = add rows + re-run; no code change needed.
```

- [ ] **Step 2: Final full-suite run**

Run: `pytest -v && python -m collector.build`
Expected: all tests pass; `output.json` regenerates with the printed report.

- [ ] **Step 3: Export the session log**

Per the assessment, run `/export` in Claude Code and save the session log alongside the deliverables.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README covering run, sources, gaps, and scheduling"
```

---

## Self-Review Notes (completed)

- **Spec coverage:** All 11 required fields are in `TrimSpec` (Task 1) and output schema; null-over-guess enforced in normalizers (Task 3) and source rules (Task 6); flat-array keyed output (Task 5); README covers all 5 required sections + scheduling (Task 7); session-log export (Task 7). ✓
- **Placeholder scan:** No TBD/TODO in code. The only "fill in" is Task 6, which is inherent data-collection with an explicit procedure and rules — not a code placeholder. ✓
- **Type consistency:** `make_key` signature `(make, model, year, trim)` used consistently in models + normalize_row; `dimensions_in` dict keys `{length,width,height,wheelbase}` consistent across models/normalize/validate/build; `build()` returns `{record_count, duplicate_count, warnings}` matching test_build. ✓
```

