"""Command-line entrypoint.

    python -m spec_collector [--make toyota|honda|all]
                             [--models Camry RAV4 ...]
                             [--out output.json]
                             [--log-level INFO]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .errors import SpecCollectorError
from .logging_config import configure_logging
from .pipeline import run
from .registry import DEFAULT_MAKE, available_makes

log = logging.getLogger("spec_collector")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spec-collector",
        description="Collect and normalize OEM vehicle specifications into output.json.",
    )
    parser.add_argument(
        "--make",
        default=DEFAULT_MAKE,
        help=f"OEM to collect, or 'all'. Available: {', '.join(available_makes())}, all "
        f"(default: {DEFAULT_MAKE}).",
    )
    parser.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Optional model filter, e.g. --models Camry RAV4. Default: all models.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output.json"),
        help="Output path (default: output.json).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    configure_logging(args.log_level)

    makes = available_makes() if args.make.strip().lower() == "all" else [args.make]

    try:
        run(makes, args.models, args.out)
    except SpecCollectorError as exc:
        log.error("%s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
