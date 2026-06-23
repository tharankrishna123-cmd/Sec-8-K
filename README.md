# SEC 8-K Equity Monitor

Tracks material SEC filings (Form 8-K, and Form 6-K for foreign private issuers) across
30 North American companies in four sectors, scores each filing's materiality, and
generates an on-demand AI analyst memo for any filing.

## How it works

- **Ingestion** (`app/ingest.py`, `app/edgar.py`): a background job polls SEC EDGAR's
  submissions API for each tracked company every `REFRESH_INTERVAL_HOURS` (default 3),
  pulls any new 8-K/6-K filings from the last 365 days, and stores them. Filings are
  deduplicated by accession number, so re-running the refresh is always safe.
- **Materiality scoring** (`app/materiality.py`): deterministic, rule-based mapping from
  Form 8-K item codes to High/Medium/Low, computed instantly at ingestion time — not an
  LLM call. A filing with multiple item codes is scored at the highest tier among them.
  **Form 6-K has no item-code taxonomy** (foreign private issuers just attach a press
  release), so 6-K filings default uniformly to Medium; the AI memo is where the real
  nuance comes in for those.
- **AI analyst memo** (`app/memo.py`): generated only when you click into a filing, via
  the Anthropic API (Claude Opus 4.8 by default). The filing's actual text is fetched
  from EDGAR and given to the model with instructions to write for an equity analyst
  audience. Results are cached in the database — every view after the first is instant
  and free.
- **Frontend**: server-rendered Jinja2 templates + htmx. Filtering and click-to-expand
  happen via small HTML swaps, no JS build step.

## Tracked companies

Defined in [`app/companies.py`](app/companies.py) — 30 tickers across Financial
Services, Energy, Technology, and Industrials. To add or remove a company, edit that
file and redeploy (or wait for the next scheduled refresh); no migration needed.

One note baked into the list: **Pioneer Natural Resources (PXD)** was fully absorbed
into ExxonMobil on May 3, 2024, and hasn't filed independently since. It's marked
`active=False` with an explanatory note that shows on its filing detail pages; it will
naturally drop out of the table once its historical filings age past the 365-day
lookback window.

Six tickers (TD, BNS, SU, CNQ, ENB, TRP) are Canadian foreign private issuers that file
Form 6-K instead of 8-K. The ingestion pulls both form types for every company
generically — there's no hardcoded "this one is Canadian" logic.

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then fill in ANTHROPIC_API_KEY at minimum
uvicorn app.main:app --reload
```

The app creates a local `sec8k.db` SQLite file on first run and triggers an immediate
filing refresh on startup, so the dashboard has real data within a few seconds.

### Triggering a refresh manually

The scheduled job runs automatically, but you can force one (e.g. to verify the
scheduler config) with:

```bash
curl -X POST "http://127.0.0.1:8000/admin/refresh?token=YOUR_ADMIN_TOKEN"
```

## Deployment (Render)

This repo includes a `render.yaml` blueprint that provisions one web service and one
PostgreSQL database.

1. Push this repo to GitHub.
2. In the Render dashboard: **New > Blueprint**, point it at the repo.
3. Render will prompt for the one secret not stored in the blueprint:
   `ANTHROPIC_API_KEY` (create one at [console.anthropic.com](https://console.anthropic.com)
   — billing must be enabled, since memo generation calls the API). Everything else
   (`DATABASE_URL`, `ADMIN_TOKEN`) is generated or linked automatically.
4. Deploy. The live URL will be `https://sec8k-monitor.onrender.com` (or whatever
   Render assigns) — both services are on the Starter tier (~$13-14/mo combined),
   chosen specifically because they're always-on, which the in-process scheduler needs
   to fire reliably (a free/sleeping tier would let the scheduler die between requests).

## Known limitations / future improvements

- **No Alembic migrations.** The schema is small and stable; tables are created via
  `Base.metadata.create_all()` on startup. Add Alembic if the schema ever needs to
  evolve with existing production data in place.
- **6-K filings score uniformly as Medium** since there's no item-code taxonomy to
  triage on — see Materiality scoring above.
- **No prompt caching** on the memo system prompt — it's short enough, and usage low
  enough, that cache hits would be rare. Worth adding if usage scales up significantly.
- **CIKs are hardcoded** in `app/companies.py` rather than looked up at runtime, since
  they never change for a given company.
