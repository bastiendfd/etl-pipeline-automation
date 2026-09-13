"""CSV extraction, validation, transformation, and output writing."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

INPUT_FIELDS = ("record_id", "customer", "amount", "event_date")
REJECT_FIELDS = (*INPUT_FIELDS, "reject_reason")


def _write_rows(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _validate_distinct_paths(source: Path, clean_output: Path, rejects_output: Path, audit_output: Path) -> None:
    """Reject canonical path aliases before opening or creating any pipeline file."""
    paths = (
        ("input", source.resolve()),
        ("clean output", clean_output.resolve()),
        ("rejects output", rejects_output.resolve()),
        ("audit output", audit_output.resolve()),
    )
    for index, (left_name, left_path) in enumerate(paths):
        for right_name, right_path in paths[index + 1 :]:
            if left_path == right_path:
                raise ValueError(f"{left_name} and {right_name} must be different paths")


def _reject_reason(row: dict[str, str]) -> str | None:
    if not row["record_id"]:
        return "record_id is required"
    if not row["customer"]:
        return "customer is required"
    try:
        amount = Decimal(row["amount"])
    except InvalidOperation:
        return "amount must be a non-negative decimal"
    if not amount.is_finite() or amount < 0:
        return "amount must be a non-negative decimal"
    try:
        parsed_date = datetime.strptime(row["event_date"], "%Y-%m-%d")
    except ValueError:
        return "event_date must use YYYY-MM-DD"
    if parsed_date.strftime("%Y-%m-%d") != row["event_date"]:
        return "event_date must use YYYY-MM-DD"
    return None


def run_pipeline(source: Path, clean_output: Path, rejects_output: Path, audit_output: Path) -> dict[str, int]:
    """Process CSV rows deterministically into clean, reject, and audit files.

    Rows retain their input order. Every output file is rewritten on each run so the
    same input and paths produce the same contents.
    """
    _validate_distinct_paths(source, clean_output, rejects_output, audit_output)
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(INPUT_FIELDS).issubset(reader.fieldnames):
            required_headers = ", ".join(INPUT_FIELDS)
            raise ValueError(f"input CSV must contain headers: {required_headers}")
        rows = list(reader)

    accepted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    for row in rows:
        normalized = {field: (row.get(field) or "").strip() for field in INPUT_FIELDS}
        reason = _reject_reason(normalized)
        if reason:
            rejected.append({**normalized, "reject_reason": reason})
        else:
            accepted.append(normalized)

    summary = {"input_rows": len(rows), "accepted_rows": len(accepted), "rejected_rows": len(rejected)}
    _write_rows(clean_output, INPUT_FIELDS, accepted)
    _write_rows(rejects_output, REJECT_FIELDS, rejected)
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
