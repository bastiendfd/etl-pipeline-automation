"""Command-line interface for the deterministic CSV ETL pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and transform a CSV file deterministically.")
    parser.add_argument("--input", type=Path, required=True, help="Path to the source CSV file.")
    parser.add_argument("--clean-output", type=Path, required=True, help="Destination for accepted rows.")
    parser.add_argument("--rejects-output", type=Path, required=True, help="Destination for rejected rows.")
    parser.add_argument("--audit-output", type=Path, required=True, help="Destination for the JSON audit summary.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        summary = run_pipeline(args.input, args.clean_output, args.rejects_output, args.audit_output)
    except (OSError, UnicodeError, ValueError) as error:
        raise SystemExit(f"etl-pipeline: {error}") from error
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
