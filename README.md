# FIN556 ETP Scanner (Assignment Starter)

This repository contains a Python tool that downloads **nasdaqtraded.txt** from NASDAQ Trader,
parses the symbols, and detects ETPs (ETFs/ETNs/Trusts) that match the assignment criteria:

1. Leveraged or inverse products (e.g., 2x/3x/-1x/-2x; Bull/Bear; UltraPro/Direxion with leverage context).
2. Products holding **futures** or **physical** exposure to commodities/crypto (e.g., crude oil, VIX, BTC/ETH; bullion trusts).

The tool produces **CSV**, **JSONL**, and a **single PDF** that includes both:
- The **full output list** of detected symbols, and
- The **full source code listing** used to produce the results.

> The PDF file is named using your NETID: `harsh6_fin556_algo_trading_symbols_homework.pdf`.

---

## Quickstart (VS Code)

1. **Clone or extract** this folder on your machine.
2. Open in **VS Code** → `File` → `Open Folder...` → select the project folder.
3. Create a virtual environment (one-time):
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Run locally** to generate outputs and the assignment PDF:
   ```bash
   python -m src.main --outdir outputs --netid harsh6 --make-assignment-pdf
   ```
   This downloads the live `nasdaqtraded.txt`, writes dated CSV/JSONL under `outputs/YYYY-MM-DD/`,
   and builds `outputs/harsh6_fin556_algo_trading_symbols_homework.pdf`.

If you only want CSV/JSONL (no PDF), omit `--make-assignment-pdf` and `--netid`:
```bash
python -m src.main --outdir outputs
```

---

## Detection rules (high level)

- **Leverage**: match `1.5x/2x/3x/4x` or brands like **UltraPro** / **ProShares Ultra** / **Direxion Daily**
  only when combined with **Bull/Bear** or a numeric `x` multiplier.
- **Inverse**: match `-1x/-2x` or keywords **inverse/short/bear** (but *not* duration cases).
- **Duration Exclusion**: `short-term`, `ultra-short`, `maturity/duration/treasury/t-bill/bond/income` are *not* inverse.
- **Commodity/Crypto**: crude oil, nat gas, VIX, gold/silver/platinum/palladium, copper; bitcoin/ether.
- **Futures**: require commodity/crypto term + `futures`/`front-month`/`strategy`.
- **Physical/Trust**: `Trust` only accepted when a commodity/crypto term is present; recognize `physical/bullion`.
- **Goldman exclusion**: `gold` inside `Goldman Sachs` does *not* count as commodity gold.

The `src/detectors.py` file implements these rules conservatively to reduce false positives.

---

## Output files

- `outputs/YYYY-MM-DD/etp_candidates.csv`
- `outputs/YYYY-MM-DD/etp_candidates.jsonl`
- `outputs/harsh6_fin556_algo_trading_symbols_homework.pdf` (single PDF for submission)

CSV/JSON schema:
- `symbol, name, etp_type, category, reasons, timestamp`

---

## GitHub Actions (optional automation)

A workflow is included at `.github/workflows/daily.yml` to run daily at **10:30 AM America/Chicago** (handles DST).
It commits new outputs only if they change.

### Enable it
1. Push to GitHub.
2. Ensure the repo has the default `contents: write` permission (or leave as-is).
3. The schedule will run automatically. You can also trigger manually via *Actions → Run workflow*.

---

## Notes

- The parser drops `Test Issue != 'N'` entries and tries to be robust to header variations.
- ReportLab is used to build the submission PDF with code + outputs in one file.
- If you want to tweak rules, edit `src/constants.py` and `src/detectors.py` and re-run the tool.


## Running tests

Create/activate venv as usual, then:

```
python -m unittest discover -s tests -v
```
