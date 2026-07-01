"""Run the SQL pipeline against the DuckDB warehouse, in order.

Usage:  python src/run_pipeline.py
Run from the repo root (paths in the SQL are relative to it).
"""
import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "warehouse.duckdb"
SQL_DIR = ROOT / "sql"
RAW = ROOT / "data" / "raw" / "accepted_2007_to_2018Q4.csv.gz"


def main() -> None:
    if not RAW.exists():
        sys.exit(
            f"Raw data not found: {RAW}\n"
            "Run scripts/download_data.ps1 first (needs a Kaggle API token)."
        )
    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB))
    con.execute(f"SET file_search_path='{ROOT.as_posix()}'")

    for script in sorted(SQL_DIR.glob("*.sql")):
        t0 = time.time()
        print(f"→ {script.name} ...", flush=True)
        statements = script.read_text(encoding="utf-8")
        # execute the file; the last statement's result set (the sanity
        # SELECT at the bottom of each script) gets printed as a table
        result = con.execute(statements)
        try:
            df = result.fetchdf()
            if not df.empty:
                print(df.to_string(index=False))
        except Exception:
            pass  # last statement was DDL/COPY — nothing to show
        print(f"  done in {time.time() - t0:.1f}s")

    con.close()
    print(f"\nWarehouse built: {DB}")
    print("Power BI exports in data/processed/")


if __name__ == "__main__":
    main()
