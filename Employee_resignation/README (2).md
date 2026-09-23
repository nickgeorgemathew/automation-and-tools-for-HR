# Notice Period Tracker

## Files
- `data_pipeline.py` — reads `employee_resignation.xlsx`, computes Completion Date
  and month/week labels for both Resignation and Completion dates, writes `processed.parquet`.
- `app.py` — Streamlit dashboard. Reads only `processed.parquet`, never the raw Excel.
- `requirements.txt` — dependencies.

## One-time setup

```bash
pip install -r requirements.txt
```

## Manual run

```bash
python data_pipeline.py --input employee_resignation.xlsx --output processed.parquet
streamlit run app.py
```

## Automating the data refresh (cron)

The dashboard itself doesn't need "automating" — Streamlit re-reads `processed.parquet`
on every page load, so it's always showing whatever that file currently contains.
What you automate is *keeping that file fresh* whenever the HR team updates the source
Excel. That's a single cron job:

```bash
# crontab -e
# Refresh the processed data every morning at 7 AM
0 7 * * * cd /path/to/notice_tracker && /usr/bin/python3 data_pipeline.py --input employee_resignation.xlsx --output processed.parquet >> refresh.log 2>&1
```

If the raw Excel changes more often (e.g. HR updates it throughout the day), tighten
the schedule, e.g. `*/30 * * * *` for every 30 minutes — the pipeline runs in well
under a second at this data size, so frequency isn't a real cost.

## Keeping this running as a live dashboard (not just local)

`streamlit run app.py` starts a local web server. For the HR team to reach it without
you keeping a terminal open:
- Streamlit Community Cloud (free, points at a GitHub repo) is the simplest option
  if the data isn't sensitive enough to need it to stay in-house.
- Otherwise, run it as a background service (`systemd` unit, or `pm2`/`supervisor`)
  on a machine that stays on, and put it behind the hospital's existing network/VPN
  rather than exposing it publicly — this file has names, departments, and notice
  periods, which shouldn't be world-readable.
