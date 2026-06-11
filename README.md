# Vehicle Spec Collector

A small, re-runnable Python tool that collects and normalizes OEM vehicle
specifications into a clean `output.json` keyed by Year / Make / Model / Trim.
It exists to enrich thin VIN-decoder data with OEM-grade specs, and is structured
so adding a new OEM is a drop-in change.

Ships with **Toyota** (Camry, RAV4, Tacoma) and **Honda** (Civic, Accord, CR-V),
2026 model year, US market — 12 trims each.

## Requirements

- Python 3.12+
- Runtime: `certifi` (CA bundle for live source fetches; see Source rationale)
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
| `--refresh-sources` | off | Force a live re-fetch of external sources (EPA) and update the cache |
| `--log-level` | `INFO` | Logging verbosity |

Runs are offline by default: external-source data is read from a committed cache,
so no network is required unless you pass `--refresh-sources`.

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
  "source": "curated:honda.com (...)",
  "sources": {
    "drivetrain": "epa:fueleconomy.gov",
    "horsepower": "curated:honda.com",
    "base_msrp": "curated:honda.com",
    "fuel_type": "curated:honda.com",
    "seating_capacity": "curated:honda.com",
    "dimensions": "curated:honda.com"
  }
}
```

`fuel_type` ∈ {gas, hybrid, phev, ev, diesel}; `drivetrain` ∈ {FWD, RWD, AWD, 4WD}.
`notes` carries year-fallback annotations. `sources` is a **per-field provenance
map** — it shows exactly which source supplied each value (e.g. Honda drivetrain
comes from EPA, the rest from curated data). Any unconfirmed value is `null` and
gets no `sources` entry.

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
    ├── sources/      # external sources a provider can reconcile
    │   ├── http.py   # JSON-over-HTTPS GET (certifi TLS + retry)
    │   ├── epa.py    # EPA drivetrain source (cache-first, live refresh)
    │   └── cache/    # committed EPA cache fixture (offline/reproducible)
    ├── toyota/       # ToyotaProvider (single curated source)
    └── honda/        # HondaProvider (curated + EPA, per-field provenance)
```

**Adding an OEM** (e.g. Nissan): create `providers/nissan/` with a provider
subclass and a `source_data.json`, then add one line to `registry.py`. Nothing in
`normalize`, `export`, `pipeline`, or `models` changes — that is the point of the
provider pattern.

## Source rationale

**Toyota — single curated source.** Specs come from a curated `source_data.json`
sourced from Toyota's official US spec pages. Curated-over-scraping was a
deliberate call: official OEM pages are JS-rendered and ToS-sensitive, so brittle
selectors would dominate the effort while producing *less* trustworthy data. The
curated file sits behind the same `collect()` interface a real scraper/feed
would, so swapping in a live fetch later is provider-internal.

**Honda — multi-source reconciliation (curated + EPA).** Honda demonstrates the
real goal: combining sources with per-field provenance. After probing the free
options, the division of labor is:

| Field | Source | Why |
|-------|--------|-----|
| `drivetrain` | **EPA** (fueleconomy.gov, live) | EPA's model taxonomy + `drive` field give authoritative, verifiable FWD/AWD per model |
| `fuel_type`, `horsepower`, `base_msrp`, `seating_capacity`, `dimensions` | curated | EPA exposes none of these; no free API provides MSRP at all |

EPA was scoped to **drivetrain only** on purpose: it's the one field EPA reports
unambiguously and uniformly within a model name. Fuel/HP/MSRP are not in EPA (the
`hpv` field is not horsepower, and there is no price field), so claiming them from
EPA would be dishonest — they stay curated and are labeled as such in `sources`.

The EPA source is **cache-first with live refresh**: a committed cache fixture
makes every run reproducible and offline-capable (and keeps tests off the
network); `--refresh-sources` forces a live re-fetch and updates the cache. TLS
uses `certifi` because some Python installs lack a usable system trust store.

This is the seam for scaling: a paid feed (Edmunds/MarketCheck) for MSRP, or a
real OEM scraper, becomes just another source reconciled the same way.

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

- The curated specs (HP, MSRP, fuel, seating, dimensions) are a hand-verified
  **snapshot**; some 2026 trims/pricing may not be officially published yet and
  should be re-verified against the OEM. Each record's `source` field flags this,
  and `notes` is reserved for year-fallback annotations. Honda's drivetrain is the
  exception — it is reconciled live from EPA and labeled as such in `sources`.
- Multi-source reconciliation is **drivetrain-only** for now: EPA supplies the one
  field it reports unambiguously; HP/MSRP/fuel/seating/dimensions remain curated
  because no free source exposes them (MSRP in particular has no free API). A paid
  feed (Edmunds/MarketCheck) or a real OEM scraper would slot in as another source
  behind the same per-field reconciliation seam.
- Toyota is still single-source (curated). The provider pattern makes adding EPA or
  another source to Toyota the same drop-in change Honda already demonstrates.
- The one runtime dependency is `certifi`, used only for live EPA fetches; default
  runs are offline (cache-backed) and need no network. `--refresh-sources` is the
  only path that hits the wire.
- Validation is advisory (warnings), not enforced — a stricter mode that fails CI
  on schema/plausibility violations would be the next step.
- Fields are limited to the assessment's required set; MPG, cargo, and weight are
  out of scope.
