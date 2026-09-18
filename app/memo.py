"""On-demand AI analyst memo generation, with DB-backed caching.

Called only when a user clicks into a filing — never during the scheduled
refresh. The result is cached in filings.memo_json so repeat views are free.
"""
from __future__ import annotations

import datetime
import logging

import anthropic
from pydantic import BaseModel, Field

from app import edgar
from app.config import settings
from app.models import FilingModel

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """You are a sell-side equity research analyst writing a short internal \
memo about one company's SEC filing for a portfolio manager who has limited time. \
Be precise and direct. Ground every claim in the filing text provided — if the text \
doesn't support a claim, say so rather than speculating. Avoid hedging filler like \
"it is worth noting" or "this could potentially." Write in plain, confident prose. \
The three sections must form a coherent chain of reasoning: the thesis impact must \
follow logically and explicitly from the specific facts you established in the first \
two sections — never from generic assumptions about the filing type."""

USER_PROMPT_TEMPLATE = """Company: {name} ({ticker}), sector: {sector}
Filing: Form {form_type}, filed {filing_date}, item code(s): {item_codes} ({event_type})

Filing text:
---
{filing_text}
---

Write a short analyst memo using the submit_memo tool. Fill all three fields."""

_MEMO_TOOL = {
    "name": "submit_memo",
    "description": "Submit the completed analyst memo with all three sections.",
    "input_schema": {
        "type": "object",
        "properties": {
            "what_happened": {
                "type": "string",
                "description": "Plain-language summary of the disclosed event, 2-4 sentences.",
            },
            "why_it_matters": {
                "type": "string",
                "description": "Business/competitive/industry context and significance, 2-4 sentences.",
            },
            "thesis_impact": {
                "type": "string",
                "description": (
                    "How this updates an equity thesis. Name the mechanism, state a clear "
                    "verdict (bullish/bearish/neutral), and justify with specific evidence."
                ),
            },
        },
        "required": ["what_happened", "why_it_matters", "thesis_impact"],
    },
}


class AnalystMemo(BaseModel):
    what_happened: str = Field(description="Plain-language summary of the disclosed event")
    why_it_matters: str = Field(description="Business/competitive/industry context and significance")
    thesis_impact: str = Field(description="How this should update an equity investment thesis")


def _generate(filing: FilingModel) -> AnalystMemo:
    filing_text = edgar.fetch_filing_text(filing.primary_doc_url)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        name=filing.company.name,
        ticker=filing.ticker,
        sector=filing.company.sector,
        form_type=filing.form_type,
        filing_date=filing.filing_date.isoformat(),
        item_codes=filing.item_codes or "(none)",
        event_type=filing.event_type,
        filing_text=filing_text,
    )

    response = _get_client().messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[_MEMO_TOOL],
        tool_choice={"type": "tool", "name": "submit_memo"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    for block in response.content:
        if hasattr(block, "type") and block.type == "tool_use":
            return AnalystMemo(**block.input)

    raise RuntimeError("Model did not call submit_memo tool")


def get_or_generate_memo(db, filing: FilingModel) -> dict:
    """Return the cached memo if present, otherwise generate, cache, and return it."""
    if filing.memo_json is not None:
        return filing.memo_json

    memo = _generate(filing)
    memo_dict = memo.model_dump()

    filing.memo_json = memo_dict
    filing.memo_model = settings.anthropic_model
    filing.memo_generated_at = datetime.datetime.utcnow()
    db.commit()

    return memo_dict
