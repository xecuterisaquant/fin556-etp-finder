"""
make_submission_pdf.py
--------------------------------------------------
Creates the single PDF required for submission:
  <netid>_fin556_algo_trading_symbols_homework.pdf
"""
from __future__ import annotations

import argparse
from pathlib import Path
from datetime import datetime
import textwrap

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # safe for headless CI
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import algo_symbols_finder as finder


def _draw_text_page(pdf, title: str, body: str, footer: str = ""):
    fig = plt.figure(figsize=(8.5, 11))
    plt.axis('off')
    y = 0.95
    plt.text(0.5, y, title, ha='center', va='top', fontsize=16, family='monospace')
    y -= 0.03
    if footer:
        plt.text(0.5, y, footer, ha='center', va='top', fontsize=9, family='monospace')
        y -= 0.02
    y -= 0.02
    plt.text(0.02, y, body, ha='left', va='top', fontsize=9, family='monospace')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)


def build_pdf(netid: str, outfile_prefix: str, dry_run: bool = False, results_prefix: str | None = None):
    outname = f"{netid.lower()}_fin556_algo_trading_symbols_homework.pdf"
    outpath = Path(outname)
    with PdfPages(outpath) as pdf:
        # Cover
        cover = (
            "FIN556 — Algorithmic Market Microstructure\n"
            "ETP Symbol Finder (Automated)\n\n"
            f"Student NETID: {netid.lower()}\n"
            f"Generated: {datetime.now():%Y-%m-%d %H:%M}"
        )
        _draw_text_page(pdf, "Submission PDF", cover, footer="This PDF contains source code + detected ETP symbols.")

        # Source code (split across pages)
        code_text = Path('algo_symbols_finder.py').read_text(encoding='utf-8')
        page_buf = []
        line_count = 0
        for line in code_text.splitlines():
            page_buf.append(line)
            line_count += 1
            if line_count >= 60:
                _draw_text_page(pdf, "Source: algo_symbols_finder.py", "\n".join(page_buf))
                page_buf = []
                line_count = 0
        if page_buf:
            _draw_text_page(pdf, "Source: algo_symbols_finder.py", "\n".join(page_buf))

        if dry_run and results_prefix is None:
            body = ("[DRY RUN]\n\n"
                    "Offline preview. To embed results:\n"
                    "1) Run:  python algo_symbols_finder.py --outdir results\n"
                    "2) Then: python make_submission_pdf.py --netid {netid}\n")
            _draw_text_page(pdf, "Results Placeholder", body.format(netid=netid))
        else:
            # Load or compute results
            if dry_run:
                df = pd.DataFrame([])
            elif results_prefix is not None and Path(f"{results_prefix}.csv").exists():
                df = pd.read_csv(f"{results_prefix}.csv")
            else:
                df = finder.find_etp_candidates()

            # Handle empty (dry-run) gracefully
            if len(df) == 0:
                _draw_text_page(pdf, "Results Placeholder",
                                "[DRY RUN]\nNo results embedded due to offline environment.")
                return outpath

            # Summary page
            total = len(df)
            by_type = df['etp_type'].value_counts().to_dict()
            by_cat = {}
            for cats in df['categories']:
                if isinstance(cats, str) and cats.startswith('['):
                    import ast
                    try:
                        cats_list = ast.literal_eval(cats)
                    except Exception:
                        cats_list = []
                else:
                    cats_list = cats if isinstance(cats, list) else []
                for c in cats_list:
                    by_cat[c] = by_cat.get(c, 0) + 1

            summary_lines = (
                [f"Total ETP symbols detected: {total}", "", "By ETP Type:"]
                + [f"  - {k}: {v}" for k, v in by_type.items()]
                + ["", "By Category:"]
                + [f"  - {k}: {v}" for k, v in by_cat.items()]
            )
            _draw_text_page(pdf, "Detection Summary", "\n".join(summary_lines))

            # Full listing (paginate)
            df_show = df[['symbol', 'security_name', 'etp_type', 'categories', 'reasons', 'as_of_utc']]
            rows = []
            for _, r in df_show.iterrows():
                rows.append(f"{r['symbol']: <8} | {r['etp_type']: <6} | {r['as_of_utc']: <20} | {r['security_name']}")
                rows.append(f"    cats: {r['categories']}")
                rows.append(f"    why : {r['reasons']}")
                rows.append("")
            buf, lc = [], 0
            for line in rows:
                buf.append(line)
                lc += 1
                if lc >= 65:
                    _draw_text_page(pdf, "Detected Symbols", "\n".join(buf))
                    buf, lc = [], 0
            if buf:
                _draw_text_page(pdf, "Detected Symbols", "\n".join(buf))

    return outpath


def _resolve_prefix(given_prefix: str | None, given_date: str | None) -> str:
    if given_prefix:
        return given_prefix
    if given_date:
        return str(Path("results") / given_date / "etp_candidates")
    latest = Path("results") / "latest" / "etp_candidates.csv"
    if latest.exists():
        return str((Path("results") / "latest" / "etp_candidates").as_posix())
    return "artifacts/etp_candidates"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netid", required=True, help="Your NETID (lowercase in filename)")
    ap.add_argument("--prefix", default=None, help="Prefix of CSV/JSON produced by finder (e.g., results/2025-09-08/etp_candidates)")
    ap.add_argument("--date", default=None, help="Date (YYYY-MM-DD) if using results/<date>/etp_candidates")
    ap.add_argument("--dry-run", action="store_true", help="Do not fetch; just embed code (useful in offline envs)")
    args = ap.parse_args()

    prefix = _resolve_prefix(args.prefix, args.date)
    path = build_pdf(args.netid, outfile_prefix=prefix, dry_run=args.dry_run, results_prefix=prefix)
    print(f"Wrote PDF: {path}")


if __name__ == "__main__":
    main()
