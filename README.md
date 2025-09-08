# FIN556 — ETP Symbol Finder (Automated, Daily)

## Quickstart (local)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

TODAY=$(date -u +%F)  # Windows PowerShell: $TODAY = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd')
python algo_symbols_finder.py --outdir results --date "$TODAY"
python make_submission_pdf.py --netid yournetid --prefix "results/$TODAY/etp_candidates"
```

Outputs:
- `results/YYYY-MM-DD/etp_candidates.csv` and `.json`
- `results/latest/etp_candidates.csv` and `.json`
- `yournetid_fin556_algo_trading_symbols_homework.pdf`

## Daily GitHub Automation
- Workflow file: `.github/workflows/daily-etp.yml`
- Set a repo Secret called `NETID` to your NETID (Settings → Secrets and variables → Actions).
- The workflow runs daily at 10:05 UTC or on manual `workflow_dispatch`.
- Results are committed to `results/` and also uploaded as an artifact.