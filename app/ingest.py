"""Refresh job: pull recent EDGAR filings for every tracked company and
upsert any that aren't already in the database (deduped by accession number).
"""

import datetime
import logging

from app import edgar, materiality
from app.companies import COMPANIES
from app.db import get_session
from app.models import FilingModel

logger = logging.getLogger(__name__)

# Foreign private issuers (6-K filers) often disclose far more frequently than
# domestic 8-K filers, and 6-K carries no item-code taxonomy to triage on (see
# materiality.py). Without a lookback cap, a handful of FPIs flood the
# dashboard with years of uniformly "Medium" backlog. A monitor should show
# what's current, not the full archive.
LOOKBACK_DAYS = 365


def refresh_all() -> dict:
    added = 0
    errors: list[str] = []
    cutoff = datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)

    with get_session() as db:
        existing_accessions = {row[0] for row in db.query(FilingModel.accession_number).all()}

        for company in COMPANIES:
            try:
                filings = edgar.fetch_recent_filings(company.cik)
            except Exception as exc:  # noqa: BLE001 - one bad company shouldn't kill the refresh
                logger.warning("Failed to fetch filings for %s: %s", company.ticker, exc)
                errors.append(f"{company.ticker}: {exc}")
                continue

            for f in filings:
                if f["accession_number"] in existing_accessions:
                    continue
                if datetime.date.fromisoformat(f["filing_date"]) < cutoff:
                    continue

                materiality_tier, event_type = materiality.score_filing(
                    f["form_type"], f["item_codes"]
                )
                doc_url = edgar.filing_document_url(
                    company.cik, f["accession_number"], f["primary_document"]
                )

                db.add(
                    FilingModel(
                        ticker=company.ticker,
                        accession_number=f["accession_number"],
                        form_type=f["form_type"],
                        filing_date=datetime.date.fromisoformat(f["filing_date"]),
                        item_codes=f["item_codes"],
                        event_type=event_type,
                        materiality=materiality_tier,
                        primary_doc_url=doc_url,
                    )
                )
                existing_accessions.add(f["accession_number"])
                added += 1

            db.commit()

    logger.info("Refresh complete: %d new filings, %d errors", added, len(errors))
    return {"added": added, "errors": errors}
