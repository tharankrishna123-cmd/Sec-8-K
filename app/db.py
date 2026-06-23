from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.companies import COMPANIES
from app.config import settings
from app.models import Base, CompanyModel

# Render (and some other hosts) hand out "postgres://" URLs, but SQLAlchemy 2.x
# requires the "postgresql://" scheme for the same driver.
_db_url = settings.database_url
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
engine = create_engine(_db_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _sync_companies()


def _sync_companies() -> None:
    """Upsert the static company registry into the database."""
    with SessionLocal() as db:
        for c in COMPANIES:
            existing = db.get(CompanyModel, c.ticker)
            if existing is None:
                db.add(
                    CompanyModel(
                        ticker=c.ticker,
                        name=c.name,
                        sector=c.sector,
                        cik=c.cik,
                        active=c.active,
                        note=c.note,
                    )
                )
            else:
                existing.name = c.name
                existing.sector = c.sector
                existing.cik = c.cik
                existing.active = c.active
                existing.note = c.note
        db.commit()


def get_session() -> Session:
    return SessionLocal()
