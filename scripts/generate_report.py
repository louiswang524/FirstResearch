from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firstresearch.benchmark.report import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Markdown benchmark report.")
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", default="outputs/reports/firstresearch_report.md")
    parser.add_argument("--table-output", default="outputs/reports/paper_ready_table.csv")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Use only the first N rows from the results CSV before generating the report.",
    )
    args = parser.parse_args()
    results = Path(args.results)
    if args.max_rows is None:
        generate_report(results, Path(args.output), Path(args.table_output))
    else:
        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", suffix=".csv", delete=False) as handle:
            temp_path = Path(handle.name)
            with results.open(encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                writer = csv.DictWriter(handle, fieldnames=reader.fieldnames)
                writer.writeheader()
                for index, row in enumerate(reader):
                    if index >= args.max_rows:
                        break
                    writer.writerow(row)
        try:
            generate_report(temp_path, Path(args.output), Path(args.table_output))
        finally:
            temp_path.unlink(missing_ok=True)
    print(args.output)


if __name__ == "__main__":
    main()
