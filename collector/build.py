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
            continue
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
