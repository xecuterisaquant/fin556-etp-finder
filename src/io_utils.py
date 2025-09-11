from __future__ import annotations
import csv, io, requests, datetime, os, json
from typing import List, Dict, Iterable
from dateutil import tz

from .constants import NASDAQ_TRADED_URL, EXPECTED_COLUMNS

def fetch_nasdaq_traded(
    url: str = NASDAQ_TRADED_URL,
    timeout: int = 30,
    outdir: str = "outputs"
) -> List[Dict[str, str]]:
    """Download nasdaqtraded.txt, save a raw snapshot for today, and return parsed rows."""
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()

    # --- Save raw file snapshot for auditing ---
    today_dir = datetime.date.today().isoformat()
    raw_dir = os.path.join(outdir or "outputs", today_dir)
    os.makedirs(raw_dir, exist_ok=True)
    raw_path = os.path.join(raw_dir, "nasdaqtraded_raw.txt")
    with open(raw_path, "w", encoding="utf-8") as rf:
        rf.write(r.text)

    # --- Parse the pipe-delimited content ---
    content = r.text.splitlines()

    # The first line is headers separated by '|'
    # The last line is usually "File Creation Time: ..."
    header = content[0].split('|')
    if header[0].strip() not in ("Nasdaq Traded", "Nasdaq Traded\xef\xbb\xbf"):
        # try to find header if there's a BOM or comment lines
        for i, line in enumerate(content):
            parts = line.split('|')
            if len(parts) >= 5 and parts[0].strip() in ("Nasdaq Traded", "Nasdaq Traded\xef\xbb\xbf"):
                header = parts
                content = content[i:]
                break

    rows: List[Dict[str, str]] = []
    for line in content[1:]:
        if line.startswith("File Creation Time"):
            break
        parts = line.split('|')
        if len(parts) < len(header):
            parts += [""] * (len(header) - len(parts))
        row = {header[i].strip(): parts[i].strip() if i < len(parts) else "" for i in range(len(header))}
        rows.append(row)

    return rows

def chicago_timestamp() -> str:
    tz_chi = tz.gettz("America/Chicago")
    return datetime.datetime.now(tz_chi).replace(microsecond=0).isoformat()

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def write_csv(path: str, records: List[Dict[str, str]], fieldnames: List[str]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for rec in records:
            w.writerow(rec)

def write_jsonl(path: str, records: List[Dict[str, str]]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
