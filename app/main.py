import datetime
import logging
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
    _run_refresh()
    scheduler.add_job(_run_refresh, "interval", hours=settings.refresh_interval_hours)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="SEC 8-K Equity Monitor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


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
