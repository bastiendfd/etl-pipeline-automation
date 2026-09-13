from __future__ import annotations

import csv
import json
import subprocess
import sys

from etl_pipeline.pipeline import run_pipeline


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["record_id", "customer", "amount", "event_date"])
        writer.writeheader()
        writer.writerows(rows)


def test_run_pipeline_writes_clean_rows_rejects_and_audit_summary(tmp_path):
    source = tmp_path / "input.csv"
    clean = tmp_path / "clean.csv"
    rejects = tmp_path / "rejects.csv"
    audit = tmp_path / "audit.json"
    write_csv(
        source,
        [
            {"record_id": "001", "customer": "  Ada Lovelace ", "amount": "12.50", "event_date": "2025-01-15"},
            {"record_id": "002", "customer": "", "amount": "9.00", "event_date": "2025-01-16"},
        ],
    )

    summary = run_pipeline(source, clean, rejects, audit)

    assert summary == {"input_rows": 2, "accepted_rows": 1, "rejected_rows": 1}
    assert list(csv.DictReader(clean.open(encoding="utf-8"))) == [
        {"record_id": "001", "customer": "Ada Lovelace", "amount": "12.50", "event_date": "2025-01-15"}
    ]
    assert list(csv.DictReader(rejects.open(encoding="utf-8"))) == [
        {
            "record_id": "002",
            "customer": "",
            "amount": "9.00",
            "event_date": "2025-01-16",
            "reject_reason": "customer is required",
        }
    ]
    assert json.loads(audit.read_text(encoding="utf-8")) == summary


def test_run_pipeline_rejects_invalid_amount_and_date_in_stable_input_order(tmp_path):
    source = tmp_path / "input.csv"
    clean = tmp_path / "clean.csv"
    rejects = tmp_path / "rejects.csv"
    audit = tmp_path / "audit.json"
    write_csv(
        source,
        [
            {"record_id": "003", "customer": "Grace", "amount": "free", "event_date": "2025-01-17"},
            {"record_id": "004", "customer": "Lin", "amount": "3", "event_date": "17-01-2025"},
        ],
    )

    summary = run_pipeline(source, clean, rejects, audit)

    assert summary == {"input_rows": 2, "accepted_rows": 0, "rejected_rows": 2}
    assert list(csv.DictReader(rejects.open(encoding="utf-8"))) == [
        {
            "record_id": "003",
            "customer": "Grace",
            "amount": "free",
            "event_date": "2025-01-17",
            "reject_reason": "amount must be a non-negative decimal",
        },
        {
            "record_id": "004",
            "customer": "Lin",
            "amount": "3",
            "event_date": "17-01-2025",
            "reject_reason": "event_date must use YYYY-MM-DD",
        },
    ]


def test_run_pipeline_requires_expected_headers(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("record_id,customer,amount\\n1,Ada,1.00\\n", encoding="utf-8")

    try:
        run_pipeline(source, tmp_path / "clean.csv", tmp_path / "rejects.csv", tmp_path / "audit.json")
    except ValueError as error:
        assert str(error) == "input CSV must contain headers: record_id, customer, amount, event_date"
    else:
        raise AssertionError("expected malformed input headers to be rejected")


def test_module_cli_reports_summary_and_writes_requested_outputs(tmp_path):
    source = tmp_path / "input.csv"
    write_csv(
        source,
        [{"record_id": "005", "customer": "Mina", "amount": "4.00", "event_date": "2025-01-18"}],
    )
    clean = tmp_path / "out" / "clean.csv"
    rejects = tmp_path / "out" / "rejects.csv"
    audit = tmp_path / "out" / "audit.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "etl_pipeline",
            "--input",
            str(source),
            "--clean-output",
            str(clean),
            "--rejects-output",
            str(rejects),
            "--audit-output",
            str(audit),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {"input_rows": 1, "accepted_rows": 1, "rejected_rows": 0}
    assert clean.exists() and rejects.exists() and audit.exists()


def test_run_pipeline_rejects_source_and_output_aliases_before_writing(tmp_path):
    source = tmp_path / "input.csv"
    source_contents = "record_id,customer,amount,event_date\n006,Ada,6.00,2025-01-19\n"
    source.write_text(source_contents, encoding="utf-8")
    clean = tmp_path / "nested" / ".." / "input.csv"
    rejects = tmp_path / "rejects.csv"
    audit = tmp_path / "audit.json"

    try:
        run_pipeline(source, clean, rejects, audit)
    except ValueError as error:
        assert str(error) == "input and clean output must be different paths"
    else:
        raise AssertionError("expected source/output path collision to be rejected")

    assert source.read_text(encoding="utf-8") == source_contents
    assert not rejects.exists()
    assert not audit.exists()


def test_run_pipeline_rejects_output_aliases_before_writing(tmp_path):
    source = tmp_path / "input.csv"
    write_csv(source, [{"record_id": "007", "customer": "Lin", "amount": "7.00", "event_date": "2025-01-20"}])
    clean = tmp_path / "outputs" / "clean.csv"
    rejects = tmp_path / "outputs" / "nested" / ".." / "clean.csv"
    audit = tmp_path / "audit.json"

    try:
        run_pipeline(source, clean, rejects, audit)
    except ValueError as error:
        assert str(error) == "clean output and rejects output must be different paths"
    else:
        raise AssertionError("expected output/output path collision to be rejected")

    assert not clean.exists()
    assert not audit.exists()


def test_module_cli_reports_path_collision_without_writing_outputs(tmp_path):
    source = tmp_path / "input.csv"
    source_contents = "record_id,customer,amount,event_date\n008,Mina,8.00,2025-01-21\n"
    source.write_text(source_contents, encoding="utf-8")
    rejects = tmp_path / "rejects.csv"
    audit = tmp_path / "audit.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "etl_pipeline",
            "--input",
            str(source),
            "--clean-output",
            str(tmp_path / "nested" / ".." / "input.csv"),
            "--rejects-output",
            str(rejects),
            "--audit-output",
            str(audit),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stderr == "etl-pipeline: input and clean output must be different paths\n"
    assert source.read_text(encoding="utf-8") == source_contents
    assert not rejects.exists()
    assert not audit.exists()
