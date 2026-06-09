# Toyota 2026 Spec Collector

A small, re-runnable Python tool that normalizes curated 2026 specification data for the
Toyota **Camry**, **RAV4**, and **Tacoma** (US market) into a clean `output.json`, one
record per trim, keyed by `Year|Make|Model|Trim`.

## How to run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

python -m collector.build      # reads source_data.json -> writes output.json + prints a run report
pytest                         # run the test suite (20 tests)
```

Options: `python -m collector.build --source source_data.json --out output.json`.

To add models or a new model year, edit `source_data.json` and re-run — no code change needed.

## Architecture

```
source_data.json  -->  normalize  -->  dedupe + sort  -->  validate  -->  output.json + run report
(curated, provenance-tagged)   (canonical enums/units)   (by key)    (plausibility/identity)
```

- `collector/models.py` — `TrimSpec` schema (all spec fields default to `null`) + composite key.
- `collector/normalize.py` — maps a raw source row to a `TrimSpec`: fuel → `{gas,hybrid,phev,ev}`,
  drivetrain → `{FWD,AWD,4WD,RWD}`, MSRP/HP/dimensions coerced to numbers (units stripped).
- `collector/validate.py` — plausibility ranges (MSRP/HP/seating/dimensions) + identity checks;
  `null` is allowed and never flagged (data honesty), only out-of-range numbers are.
- `collector/build.py` — orchestrates load → normalize → dedupe → validate → write, and prints a report.

## Sources and why

**Source of record: Toyota's official US specs**, captured via the structured per-model 2026
spec pages on `cars.com` (which mirror Toyota's published figures) and cross-checked against
`toyota.com/<model>/features/` and the Toyota USA Newsroom. Each output record carries its
`source_url` and `as_of` date for auditability.

I deliberately chose a **curated, provenance-tagged data file + a normalization pipeline** over
two alternatives I evaluated:

- **Toyota's developer API** (`developer.eig.toyota.com`) is gated/partner-only (HTTP 403) and
  telematics/dealer-shaped (config-by-VIN), not a public per-trim spec catalog — unusable here.
- **NHTSA vPIC** is public and stable but lacks MSRP, per-trim horsepower, and dimensions.
- **Scraping toyota.com's configurator** is accurate but brittle (JS-rendered, undocumented
  private endpoints) — it would break on any redesign, the opposite of "re-runnable."

The curated approach is **stable** (re-runs are deterministic and never break on a site change),
**accurate** (OEM-grade values), and **honest** (provenance on every field).

## Missing data and duplicate trims

- **Missing data → `null`, never guessed.** Examples in the current output: TRD Sport and TRD
  Off-Road `base_msrp_usd` are `null` (not confirmed from the source), and all Tacoma + the RAV4
  Woodland `height` is `null` because overall height varies by cab/suspension and I couldn't confirm
  a per-trim value. The `notes` field explains each null.
- **Model-year fallback:** if a trim's 2026 specs were unpublished, the tool keeps `year=2026` but
  records the actual `spec_year` and a `notes` explanation. (All three 2026 models are published,
  so no fallback was needed in this run.)
- **Duplicate trims** (same `Year|Make|Model|Trim` key) are deduped deterministically — first
  occurrence wins — and the count is printed in the run report.
- A **plausibility pass** flags out-of-range MSRP/HP/seating/dimensions for human review (the
  current dataset produces no warnings).

## Scheduling re-runs (design, not deployed)

Run `python -m collector.build` on a monthly cron — e.g. a GitHub Actions scheduled workflow.
A thin pre-step would poll the Toyota USA Newsroom for newly published model-year spec sheets;
when a new year appears, it opens a pull request adding rows to `source_data.json` for human
verification before merge. Because the build is deterministic and every value is provenance-tagged,
the resulting `output.json` diff is small and reviewable. Catching a new model year is then just
"add rows + re-run" — no code change. The same workflow could re-validate existing rows and flag
any field whose source URL has changed since `as_of`.
