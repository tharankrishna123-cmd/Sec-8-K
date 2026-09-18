import datetime
import json
import logging
import os
import time
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import ingest, memo
from app.companies import SECTORS
from app.config import settings
from app.db import get_session, init_db
from app.models import CompanyModel, FilingModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["css_version"] = str(int(time.time()))
scheduler = BackgroundScheduler()

MATERIALITIES = ["High", "Medium", "Low"]
_last_refresh: datetime.datetime | None = None


def _run_refresh() -> None:
    global _last_refresh
    try:
        result = ingest.refresh_all()
        _last_refresh = datetime.datetime.utcnow()
        logger.info("Scheduled refresh done: %s", result)
    except Exception:  # noqa: BLE001 - a failed refresh shouldn't crash the scheduler
        logger.exception("Scheduled refresh failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = get_session()
    try:
        needs_seed = db.query(FilingModel.id).first() is None
    finally:
        db.close()
    if needs_seed:
        _run_refresh()
    if not os.environ.get("VERCEL"):
        scheduler.add_job(_run_refresh, "interval", hours=settings.refresh_interval_hours)
        scheduler.start()
    yield
    if not os.environ.get("VERCEL"):
        scheduler.shutdown(wait=False)


app = FastAPI(title="SEC 8-K Equity Monitor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


_SECTOR_COLORS = {
    "Financial Services": "#60a5fa",
    "Energy": "#fb923c",
    "Technology": "#a78bfa",
    "Industrials": "#2dd4bf",
}


def _sector_trend_data(db) -> str:
    """Monthly filing counts per sector for the last 6 months, as JSON for Chart.js."""
    today = datetime.date.today()
    month_keys: list[str] = []
    for i in range(5, -1, -1):
        m, y = today.month - i, today.year
        while m <= 0:
            m += 12
            y -= 1
        month_keys.append(f"{y}-{m:02d}")

    cutoff = datetime.date(int(month_keys[0][:4]), int(month_keys[0][5:7]), 1)
    rows = (
        db.query(FilingModel.filing_date, CompanyModel.sector)
        .join(CompanyModel)
        .filter(FilingModel.filing_date >= cutoff)
        .all()
    )

    counts: dict[str, dict[str, int]] = {
        s: {m: 0 for m in month_keys} for s in SECTORS
    }
    for filing_date, sector in rows:
        mk = filing_date.strftime("%Y-%m")
        if sector in counts and mk in counts[sector]:
            counts[sector][mk] += 1

    labels = [
        datetime.date(int(m[:4]), int(m[5:7]), 1).strftime("%b %Y")
        for m in month_keys
    ]
    datasets = [
        {"label": s, "data": list(counts[s].values()), "color": _SECTOR_COLORS[s]}
        for s in SECTORS
    ]
    return json.dumps({"labels": labels, "datasets": datasets})


def _filtered_filings(db, sector: str, materiality: str) -> list[FilingModel]:
    query = db.query(FilingModel).join(CompanyModel)
    if sector:
        query = query.filter(CompanyModel.sector == sector)
    if materiality:
        query = query.filter(FilingModel.materiality == materiality)
    return query.order_by(FilingModel.filing_date.desc(), FilingModel.id.desc()).all()


@app.get("/", response_class=HTMLResponse)
def index(request: Request, sector: str = "", materiality: str = ""):
    db = get_session()
    try:
        filings = _filtered_filings(db, sector, materiality)
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "filings": filings,
                "sectors": SECTORS,
                "materialities": MATERIALITIES,
                "selected_sector": sector,
                "selected_materiality": materiality,
                "last_refresh": _last_refresh,
                "trend_data": _sector_trend_data(db),
            },
        )
    finally:
        db.close()


@app.get("/filings-table", response_class=HTMLResponse)
def filings_table(request: Request, sector: str = "", materiality: str = ""):
    db = get_session()
    try:
        filings = _filtered_filings(db, sector, materiality)
        return templates.TemplateResponse(
            request,
            "_filings_table.html",
            {
                "filings": filings,
                "sectors": SECTORS,
                "materialities": MATERIALITIES,
                "selected_sector": sector,
                "selected_materiality": materiality,
            },
        )
    finally:
        db.close()


@app.get("/filings/{filing_id}", response_class=HTMLResponse)
def filing_detail(request: Request, filing_id: int):
    db = get_session()
    try:
        filing = db.get(FilingModel, filing_id)
        if filing is None:
            raise HTTPException(status_code=404, detail="Filing not found")
        return templates.TemplateResponse(
            request, "_filing_detail.html", {"filing": filing}
        )
    finally:
        db.close()


@app.get("/empty", response_class=HTMLResponse)
def empty():
    return HTMLResponse("")


@app.post("/filings/{filing_id}/memo", response_class=HTMLResponse)
def generate_memo(request: Request, filing_id: int):
    db = get_session()
    try:
        filing = db.get(FilingModel, filing_id)
        if filing is None:
            raise HTTPException(status_code=404, detail="Filing not found")
        try:
            memo_dict = memo.get_or_generate_memo(db, filing)
        except Exception:
            logger.exception("Memo generation failed for filing %s", filing_id)
            return HTMLResponse(
                '<p class="memo-error">Couldn\'t generate the memo just now — try again in a moment.</p>',
                status_code=200,
            )
        return templates.TemplateResponse(
            request, "_memo.html", {"memo": memo_dict}
        )
    finally:
        db.close()


@app.post("/admin/refresh")
def admin_refresh(token: str):
    if token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid token")
    global _last_refresh
    result = ingest.refresh_all()
    _last_refresh = datetime.datetime.utcnow()
    return result


@app.post("/admin/cron-refresh")
def cron_refresh(request: Request):
    auth = request.headers.get("Authorization", "")
    if not settings.cron_secret or auth != f"Bearer {settings.cron_secret}":
        raise HTTPException(status_code=403, detail="Forbidden")
    global _last_refresh
    result = ingest.refresh_all()
    _last_refresh = datetime.datetime.utcnow()
    return result
