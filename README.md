# Vehicle Spec Collector

A small, re-runnable Python tool that collects and normalizes OEM vehicle
specifications into a clean `output.json` keyed by Year / Make / Model / Trim.
It exists to enrich thin VIN-decoder data with OEM-grade specs, and is structured
so adding a new OEM is a drop-in change.

Ships with **Toyota** (Camry, RAV4, Tacoma) and **Honda** (Civic, Accord, CR-V),
2026 model year, US market — 12 trims each.

## Requirements

- Python 3.12+
- No third-party runtime dependencies (standard library only)
- `pytest` for tests

## How to run

```bash
# from the repo root
python -m spec_collector --make all              # Toyota + Honda -> output.json

python -m spec_collector --make toyota           # default OEM only
python -m spec_collector --make honda --models Civic Accord
python -m spec_collector --make all --out specs.json --log-level DEBUG
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--make` | `toyota` | OEM to collect: `toyota`, `honda`, or `all` |
| `--models` | all | Optional model filter, space-separated (case-insensitive) |
| `--out` | `output.json` | Output path |
| `--log-level` | `INFO` | Logging verbosity |

Run the tests:

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m pytest        # or just: pytest  (pythonpath set in pyproject.toml)
```

## Output schema

A JSON array, one record per trim:

```json
{
  "year": 2026,
  "make": "Toyota",
  "model": "Camry",
  "trim": "XSE AWD",
  "base_msrp": 36900,
  "fuel_type": "hybrid",
  "horsepower": 232,
  "drivetrain": "AWD",
  "seating_capacity": 5,
  "dimensions": {"length_in": 193.5, "width_in": 72.2, "height_in": 56.9, "wheelbase_in": 111.2},
  "notes": null,
  "source": "Toyota USA model specs (toyota.com) — curated 2026, ..."
}
```

`fuel_type` ∈ {gas, hybrid, phev, ev, diesel}; `drivetrain` ∈ {FWD, RWD, AWD, 4WD}.
`notes` carries year-fallback annotations; `source` carries provenance. Any
unconfirmed value is `null`.

## Architecture

Three separated concerns, connected only by plain data:

```
registry → provider.collect()  →  normalize_record()  →  write_output()
           (collection)            (normalization)        (export)
```

```
src/spec_collector/
├── cli.py            # argparse entrypoint (--make / --models / --out)
├── pipeline.py       # orchestration: collect → normalize → sanity → export
├── registry.py       # make name → provider (one line to add an OEM)
├── models.py         # Trim dataclass + FuelType / Drivetrain enums (the schema)
├── normalize.py      # raw → canonical: vocab mapping, unit coercion, null rule
├── export.py         # atomic write to output.json
├── retry.py          # retry/backoff decorator for the collection step
└── providers/
    ├── base.py       # OEMProvider ABC + JSON-file-backed base
    ├── toyota/       # ToyotaProvider + curated source_data.json
    └── honda/        # HondaProvider + curated source_data.json
```

**Adding an OEM** (e.g. Nissan): create `providers/nissan/` with a provider
subclass and a `source_data.json`, then add one line to `registry.py`. Nothing in
`normalize`, `export`, `pipeline`, or `models` changes — that is the point of the
provider pattern.

## Source rationale

Specs are curated into per-OEM `source_data.json` files, sourced from the
manufacturers' official US spec pages (`toyota.com`, `honda.com`).

A single authoritative source per OEM, curated, was chosen over live scraping
deliberately. Official OEM pages are JS-rendered and ToS-sensitive; in a small
slice, brittle selectors would dominate the effort while producing *less*
trustworthy data. A curated source keeps the run **deterministic, re-runnable,
and verifiable**, and — crucially — sits behind the same `collect()` interface a
real scraper or licensed feed would. Swapping in a live fetch later is a
provider-internal change; the `@with_retry` seam on the read step is already in
place for that transition.

## Missing data strategy

- **Null over guess, always.** If a field is absent from the source, or its value
  can't be mapped to the canonical vocabulary (e.g. an unrecognized fuel type),
  normalization emits `null` and logs a warning. Values are never fabricated or
  defaulted.
- **Identity is mandatory.** Only the four key fields (year/make/model/trim) are
  required; a record missing one is skipped (logged), not invented.
- **Sanity pass.** Horsepower, MSRP, and seating are range-checked. Implausible
  values are flagged as warnings — never silently corrected or dropped.

## Duplicate handling

- Records are deduplicated by the canonical key `(year, make, model, trim)`; the
  first occurrence wins and a warning is logged.
- This is also how multiple OEMs coexist in one `--make all` run without
  collisions, and how a future second source would reconcile against the first.
- Drivetrain/powertrain variants whose specs differ (e.g. Camry `XSE AWD`) are
  intentionally **distinct** records, not duplicates, since they carry different
  HP/MSRP.

## Scheduling strategy

The collector is a single idempotent command, so scheduling is straightforward:
run `python -m spec_collector --make all` on a cron / scheduled CI job (e.g. a
weekly GitHub Action or Airflow DAG). Each run regenerates `output.json`
atomically; a follow-up step diffs the new artifact against the committed one and
opens a PR / alert when records change or new trims appear. To catch **new model
years**, the job parameterizes the target year (or providers detect the latest
published year); because the dedup key includes `year`, new years land as new
rows rather than overwriting history. With no external runtime dependencies and a
deterministic run, the same command works identically on a laptop, in CI, or in a
container.

## Known limitations

- The curated data is a hand-verified **snapshot**; some 2026 trims/pricing may
  not be officially published yet and should be re-verified against the OEM. Each
  record's `source` field flags this, and `notes` is reserved for year-fallback
  annotations.
- Collection is file-backed today. Real per-OEM adapters (HTTP/scraper or
  licensed feed) would slot behind the existing `collect()` interface and reuse
  `@with_retry`.
- No multi-source reconciliation (single source per OEM by design for this slice).
- Validation is advisory (warnings), not enforced — a stricter mode that fails CI
  on schema/plausibility violations would be the next step.
- Fields are limited to the assessment's required set; MPG, cargo, and weight are
  out of scope.
