# Deterministic CSV ETL Pipeline

[![CI](https://github.com/bastiendfd/etl-pipeline-automation/actions/workflows/ci.yml/badge.svg)](https://github.com/bastiendfd/etl-pipeline-automation/actions/workflows/ci.yml)

A small, dependency-free Python command-line ETL pipeline for **synthetic CSV data**. It validates each input row, normalizes accepted values, sends invalid rows to a reject file, and writes a machine-readable audit summary.

## Why this project

The project demonstrates an operationally useful ETL shape without hiding data-quality failures:

```text
CSV input → schema check → normalize/validate → clean CSV + rejects CSV + JSON audit
```

The pipeline is deterministic: it preserves input order, uses stable validation messages, rewrites all outputs on every invocation, and makes no network calls.

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/bastiendfd/etl-pipeline-automation.git
cd etl-pipeline-automation
python -m pip install -e '.[dev]'
python -m etl_pipeline \
  --input examples/input.csv \
  --clean-output output/clean.csv \
  --rejects-output output/rejects.csv \
  --audit-output output/audit.json
```

The command prints a JSON summary, for example:

```json
{"accepted_rows": 2, "input_rows": 4, "rejected_rows": 2}
```

You can also use the installed command:

```bash
etl-pipeline --input examples/input.csv --clean-output output/clean.csv \
  --rejects-output output/rejects.csv --audit-output output/audit.json
```

## Input contract

The source must be UTF-8 CSV with these headers:

| Field | Rules / transformation |
| --- | --- |
| `record_id` | Required; leading/trailing whitespace is removed. |
| `customer` | Required; leading/trailing whitespace is removed. |
| `amount` | Required non-negative finite decimal (for example `12.50`). The original normalized string is retained. |
| `event_date` | Required ISO date in exactly `YYYY-MM-DD` format. |

If a header is missing, the command exits non-zero without producing partial outputs. For invalid rows, the pipeline emits the original normalized values plus one stable `reject_reason`. If a row has multiple problems, the first rule in the table order determines the reason.

## Outputs

- **Clean CSV**: accepted rows with the four input columns.
- **Rejects CSV**: rejected rows with the input columns plus `reject_reason`.
- **Audit JSON**: `input_rows`, `accepted_rows`, and `rejected_rows` counts.

All output parents are created automatically. Existing output files are replaced, so rerunning with identical input yields byte-for-byte equivalent outputs.

## Development

```bash
python -m pytest
```

The tests cover accepted/rejected records, validation, output ordering, malformed headers, and the module CLI. GitHub Actions runs the test suite on Python 3.10–3.12 for pushes and pull requests to `main`.

## Security and data

Use only synthetic or non-sensitive data in this repository. Do not commit credentials, `.env` files, or real customer data. See [SECURITY.md](SECURITY.md) for reporting guidance.

## License

[MIT](LICENSE)
