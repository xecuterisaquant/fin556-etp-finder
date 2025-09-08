"""
algo_symbols_finder.py
FIN556 — Algorithmic Market Microstructure: ETP Symbol Finder
----------------------------------------------------------------
Downloads NASDAQ's nasdaqtraded.txt and identifies Exchange Traded Products (ETPs)
that are:
  (1) Leveraged or inverse variants of other instruments
  (2) Futures-based or physically-backed exposures (e.g., oil, BTC futures, gold trust)

Only the instrument *name* is used to infer eligibility (as required).

Outputs (dated):
  - results/YYYY-MM-DD/etp_candidates.csv
  - results/YYYY-MM-DD/etp_candidates.json
  - results/latest/etp_candidates.csv (convenience copy)

Usage (CLI):
  python algo_symbols_finder.py --outdir results --date 2025-09-08
  # --date optional; defaults to today (UTC)
"""
from __future__ import annotations

import argparse
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
import requests

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"

def _norm(s: str) -> str:
    import re as _re
    return _re.sub(r'\s+', ' ', s.strip())

def _contains(pattern, s: str) -> bool:
    return bool(pattern.search(s))

PATTERNS_LEV_INV = [
    # Multipliers with boundaries
    re.compile(r'(?<![A-Z0-9])[-–—]?\s*1x(?![A-Z0-9])', re.I),
    re.compile(r'(?<![A-Z0-9])[-–—]?\s*2x(?![A-Z0-9])', re.I),
    re.compile(r'(?<![A-Z0-9])[-–—]?\s*3x(?![A-Z0-9])', re.I),
    re.compile(r'\b(?:bull|bear)\s+(?:1x|2x|3x)\b', re.I),
    re.compile(r'\b(?:2x|3x)\s+(?:bull|bear|long|short)\b', re.I),
    re.compile(r'\bdaily\s+\w+\s+(?:bull|bear)\s+(?:1x|2x|3x)\b', re.I),
    # Brand cues (tighter for "Ultra")
    re.compile(r'\bultrapro\b', re.I),
    re.compile(r'\bproshares\s+ultra\b', re.I),
    re.compile(r'\bultra\b(?=.*\b(2x|3x|daily|bull|bear)\b)', re.I),
    re.compile(r'\bdirexion daily\b', re.I),
    re.compile(r'\bT[- ]?Rex\b.*\b2x\b', re.I),
    re.compile(r'\bLeverage Shares\b', re.I),
    re.compile(r'\bInverse\b', re.I),
    # "Short" → guarded by context function below
    re.compile(r'\bshort\b', re.I),
]

NEGATIVE_SHORT_PHRASES = [
    "short term", "short-term", "short duration", "short-duration",
    "short maturity", "short-maturity", "short interest rate", "short-interval",
    "short treasury (1-3)", "ultra short", "ultra-short", "ultra short-term", "ultra-short-term"
]

def is_inverse_short(name: str) -> bool:
    if "short" not in name.lower():
        return False
    n = name.lower()
    for bad in NEGATIVE_SHORT_PHRASES:
        if bad in n:
            return False
    return any(k in n for k in [
        "daily", "bear", "inverse", "proshares", "direxion", "vix",
        "oil", "natural gas", "bitcoin", "ether", "ethereum"
    ])

PATTERNS_FUTURES_PHYS = [
    re.compile(r'\bfuture(s)?\b', re.I),
    re.compile(r'\bbitcoin\b|\bbtc\b|\beth(?:ereum)?\b|\beth\b', re.I),
    re.compile(r'\b(vix|cboe volatility)\b', re.I),
    re.compile(r'\b(physical|physically)\b', re.I),
    # Metals
    re.compile(r'\b(gold|silver|platinum|palladium)\b', re.I),
    # Energy
    re.compile(r'\b(wti|brent|crude oil|natural gas|gasoline|heating oil)\b', re.I),
    # US Commodity Funds like USO/UNG
    re.compile(r'\bUnited States (Oil|Natural Gas|Gasoline|Heating Oil) Fund\b', re.I),
    # Ags
    re.compile(r'\b(corn|soybean|soybeans|wheat|coffee|sugar|cocoa|cotton|live cattle|lean hogs|feeder cattle)\b', re.I),
    # Other materials
    re.compile(r'\b(uranium|lithium|nickel|copper|aluminum|zinc|tin)\b', re.I),
    # Trusts that usually mean direct commodity/crypto (heuristic: trust + commodity term)
    re.compile(r'\btrust\b', re.I),
]

COMMODITY_KEYWORDS = {
    'gold', 'silver', 'platinum', 'palladium', 'bitcoin', 'ether', 'ethereum',
    'oil', 'crude', 'wti', 'brent', 'natural gas', 'gasoline', 'heating oil',
    'corn', 'soybean', 'soybeans', 'wheat', 'coffee', 'sugar', 'cocoa', 'cotton',
    'uranium', 'lithium', 'nickel', 'copper', 'aluminum', 'zinc', 'tin', 'vix', 'volatility'
}

def futures_phys_trust_guard(name: str) -> bool:
    n = name.lower()
    if "trust" in n and not any(kw in n for kw in COMMODITY_KEYWORDS):
        return False
    return True

def classify_etp_type(name: str, etf_flag: str) -> str:
    n = name.lower()
    if 'exchange traded note' in n or 'etn' in n or 'etns' in n or 'etracs' in n or 'ipath' in n:
        return 'ETN'
    if 'trust' in n and futures_phys_trust_guard(name):
        return 'Trust'
    if str(etf_flag).strip().upper() == 'Y':
        return 'ETF'
    return 'Other ETP'

def load_nasdaq_df(url: str = NASDAQ_URL) -> pd.DataFrame:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    raw = resp.text
    df = pd.read_csv(io.StringIO(raw), sep='|', dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    cols = df.columns
    sym_col = 'NASDAQ Symbol' if 'NASDAQ Symbol' in cols else ('Symbol' if 'Symbol' in cols else cols[1])
    name_col = 'Security Name' if 'Security Name' in cols else cols[2]
    test_col = 'Test Issue' if 'Test Issue' in cols else None
    traded_col = 'Nasdaq Traded' if 'Nasdaq Traded' in cols else None
    etf_col = 'ETF' if 'ETF' in cols else None

    if test_col in df and test_col is not None:
        df = df[df[test_col].str.upper().eq('N')]
    if traded_col in df and traded_col is not None:
        df = df[df[traded_col].str.upper().eq('Y')]

    keep = [sym_col, name_col]
    if etf_col: keep.append(etf_col)
    out = df[keep].dropna(subset=[sym_col, name_col]).copy()
    out.rename(columns={sym_col: 'symbol', name_col: 'security_name', (etf_col or 'ETF'): 'etf'}, inplace=True)
    out['security_name'] = out['security_name'].apply(_norm)
    return out

def match_categories(name: str):
    cats, hits = [], []
    levhit = any(_contains(p, name) for p in PATTERNS_LEV_INV) or is_inverse_short(name)
    if levhit:
        cats.append('leveraged_or_inverse')
        for p in PATTERNS_LEV_INV:
            if _contains(p, name):
                hits.append(f'lev/inv: {p.pattern}')
        if is_inverse_short(name):
            hits.append('lev/inv: short-inverse context')
    futphys = any(_contains(p, name) for p in PATTERNS_FUTURES_PHYS) and futures_phys_trust_guard(name)
    if futphys:
        cats.append('futures_or_physical')
        for p in PATTERNS_FUTURES_PHYS:
            if _contains(p, name):
                hits.append(f'fut/phys: {p.pattern}')
    return cats, hits

def find_etp_candidates() -> pd.DataFrame:
    df = load_nasdaq_df()
    mask_etp = (
        df['etf'].str.upper().eq('Y')
        | df['security_name'].str.contains(r'\betn(s)?\b|exchange traded note|etracs|ipath', case=False, regex=True)
        | df['security_name'].str.contains(r'\btrust\b', case=False)
    )
    df = df[mask_etp].copy()
    cats, reasons, types = [], [], []
    for name, etf_flag in zip(df['security_name'], df['etf']):
        c, r = match_categories(name)
        cats.append(c)
        reasons.append(r)
        types.append(classify_etp_type(name, etf_flag))
    df['categories'] = cats
    df['reasons'] = reasons
    df['etp_type'] = types
    df = df[df['categories'].apply(lambda lst: len(lst) > 0)].copy()
    df.sort_values(['etp_type', 'symbol'], inplace=True, ignore_index=True)
    df['as_of_utc'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    return df

def _validate_yyyymmdd(s: str) -> str:
    s = s.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    if re.fullmatch(r"\d{8}", s):
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    raise ValueError("Date must be YYYY-MM-DD or YYYYMMDD")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--outfile_prefix', default=None, help='(Deprecated) Use --outdir and --date instead')
    ap.add_argument('--outdir', default='results', help='Base output directory for dated runs (default: results)')
    ap.add_argument('--date', default=None, help='Date to attribute results to (YYYY-MM-DD or YYYYMMDD). Defaults to today (UTC).')
    args = ap.parse_args()

    date_str = args.date
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    else:
        date_str = _validate_yyyymmdd(date_str)

    df = find_etp_candidates()

    outdir = Path(args.outdir) / date_str
    outdir.mkdir(parents=True, exist_ok=True)
    prefix = outdir / 'etp_candidates'

    csv_path = f"{prefix}.csv"
    json_path = f"{prefix}.json"
    df.to_csv(csv_path, index=False)
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(df.to_json(orient='records', indent=2))

    latest_dir = Path(args.outdir) / 'latest'
    latest_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(latest_dir / 'etp_candidates.csv', index=False)
    with open(latest_dir / 'etp_candidates.json', 'w', encoding='utf-8') as f:
        f.write(df.to_json(orient='records', indent=2))

    print(f"[{date_str}] Wrote {len(df)} rows -> {csv_path} and {json_path}")

if __name__ == '__main__':
    main()