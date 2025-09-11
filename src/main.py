from __future__ import annotations
import argparse, os, sys, json
from typing import List, Dict

from .io_utils import fetch_nasdaq_traded, chicago_timestamp, write_csv, write_jsonl
from .detectors import detect
from . import constants as C
from .pdf_report import build_assignment_pdf

ASSIGNMENT_DEFAULT_URL = C.NASDAQ_TRADED_URL

def parse_args():
    ap = argparse.ArgumentParser(description="ETP scanner for NASDAQ nasdaqtraded.txt")
    ap.add_argument("--source-url", default=ASSIGNMENT_DEFAULT_URL, help="URL to nasdaqtraded.txt")
    ap.add_argument("--outdir", default="outputs", help="Base output directory")
    ap.add_argument("--netid", default="", help="Your NETID (used to name the assignment PDF)")
    ap.add_argument("--make-assignment-pdf", action="store_true", help="Build the single PDF containing code + output")
    return ap.parse_args()

def run(source_url: str, outdir: str, netid: str, make_pdf: bool):
    # Chicago-local timestamp and date folder (shared across ALL artifacts)
    ts = chicago_timestamp()
    date_dir = ts[:10]  # "YYYY-MM-DD"

    # Fetch data; also saves the raw snapshot under outdir/date_dir/
    rows = fetch_nasdaq_traded(source_url, outdir=outdir, date_dir=date_dir)

    # Columns to emit
    fields = ["symbol", "name", "etp_type", "category", "reasons", "timestamp"]
    records: List[Dict[str, str]] = []

    for row in rows:
        # Skip test issues
        if row.get("Test Issue", "").upper() != "N":
            continue
        name = row.get("Security Name", "")
        matched, category, reasons, etp_type = detect(name, row)
        if not matched:
            continue
        rec = {
            "symbol": row.get("Symbol", ""),
            "name": name,
            "etp_type": etp_type or "",
            "category": category or "",
            "reasons": reasons,
            "timestamp": ts,
        }
        records.append(rec)

    # Write CSV/JSONL into the SAME date folder used for the raw file
    base_dir = os.path.join(outdir, date_dir)
    csv_path = os.path.join(base_dir, "etp_candidates.csv")
    jsonl_path = os.path.join(base_dir, "etp_candidates.jsonl")
    write_csv(csv_path, records, fields)
    write_jsonl(jsonl_path, records)

    # Build the single assignment PDF if requested
    pdf_path = None
    if make_pdf:
        if not netid:
            print("ERROR: --netid is required when --make-assignment-pdf is used", file=sys.stderr)
            sys.exit(2)
        pdf_name = f"{netid.lower()}_fin556_algo_trading_symbols_homework.pdf"
        pdf_path = os.path.join(outdir, pdf_name)
        # Collect code paths to embed
        code_paths = []
        here = os.path.dirname(__file__)
        for rel in ["constants.py", "detectors.py", "io_utils.py", "pdf_report.py", "main.py"]:
            code_paths.append(os.path.join(here, rel))
        # add workflow for completeness if present
        wf = os.path.join(os.path.dirname(here), ".github", "workflows", "daily.yml")
        if os.path.exists(wf):
            code_paths.append(wf)
        run_meta = {
            "source_url": source_url,
            "timestamp_chicago": ts,
            "records_count": str(len(records)),
            "output_csv": os.path.relpath(csv_path),
            "output_jsonl": os.path.relpath(jsonl_path),
            "date_dir": date_dir,
        }
        build_assignment_pdf(pdf_path, netid=netid, records=records, code_paths=code_paths, run_meta=run_meta)

    # Summary to stdout (useful in Actions logs)
    print(json.dumps({
        "count": len(records),
        "csv": csv_path,
        "jsonl": jsonl_path,
        "pdf": pdf_path,
        "date_dir": date_dir
    }, indent=2))

if __name__ == "__main__":
    args = parse_args()
    run(args.source_url, args.outdir, args.netid, args.make_assignment_pdf)
