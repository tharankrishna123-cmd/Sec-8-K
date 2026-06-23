"""SEC EDGAR client: list recent 8-K/6-K filings per company, fetch filing text.

SEC requires a descriptive User-Agent on every request and asks that you stay
well under 10 requests/second. We track only 30 companies and refresh every
few hours, so a small fixed delay between requests is more than enough.
"""

import re
import time

import httpx
from bs4 import BeautifulSoup

from app.config import settings

TRACKED_FORMS = {"8-K", "6-K"}
REQUEST_DELAY_SECONDS = 0.2
MAX_FILING_TEXT_CHARS = 15_000


def _headers() -> dict[str, str]:
    return {"User-Agent": settings.sec_user_agent}


def fetch_recent_filings(cik: str) -> list[dict]:
    """Return recent 8-K/6-K filings for one company's CIK, newest first."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = httpx.get(url, headers=_headers(), timeout=30)
    time.sleep(REQUEST_DELAY_SECONDS)
    resp.raise_for_status()
    recent = resp.json()["filings"]["recent"]

    count = len(recent["form"])
    items_list = recent.get("items", [""] * count)

    filings = []
    for i in range(count):
        form = recent["form"][i]
        if form not in TRACKED_FORMS:
            continue
        filings.append(
            {
                "form_type": form,
                "filing_date": recent["filingDate"][i],
                "accession_number": recent["accessionNumber"][i],
                "item_codes": items_list[i] or "",
                "primary_document": recent["primaryDocument"][i],
            }
        )
    return filings


def filing_document_url(cik: str, accession_number: str, primary_document: str) -> str:
    cik_no_zeros = str(int(cik))
    accession_no_dashes = accession_number.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/"
        f"{cik_no_zeros}/{accession_no_dashes}/{primary_document}"
    )


def fetch_filing_text(doc_url: str) -> str:
    """Fetch a filing's primary document and return cleaned, truncated text."""
    resp = httpx.get(doc_url, headers=_headers(), timeout=30)
    time.sleep(REQUEST_DELAY_SECONDS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Modern EDGAR filings embed an Inline XBRL cover-page facts block that's
    # visually hidden (display:none) but still shows up in get_text(). Drop it.
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        tag.decompose()
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

    # Cover-page boilerplate before the actual narrative is rarely useful;
    # start from the standard header line when present.
    marker = "SECURITIES AND EXCHANGE COMMISSION"
    idx = text.upper().find(marker)
    if idx > 0:
        text = text[idx:]

    return text[:MAX_FILING_TEXT_CHARS]
