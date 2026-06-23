"""Deterministic, rule-based materiality scoring from 8-K/6-K item codes.

This is intentionally not an LLM call: it needs to be instant and free for
every filing in the list, every refresh cycle. The AI memo (generated only on
click) is where nuanced judgment comes in — this just sorts the list.
"""

HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"

# (tier, human-readable label) for each standard Form 8-K item code.
ITEM_INFO: dict[str, tuple[str, str]] = {
    "1.01": (HIGH, "Entry into Material Agreement"),
    "1.02": (HIGH, "Termination of Material Agreement"),
    "1.03": (HIGH, "Bankruptcy or Receivership"),
    "1.04": (MEDIUM, "Mine Safety Reporting"),
    "2.01": (HIGH, "Completion of Acquisition or Disposition"),
    "2.02": (MEDIUM, "Results of Operations"),
    "2.03": (HIGH, "Direct Financial Obligation Created"),
    "2.04": (HIGH, "Triggering Event on Financial Obligation"),
    "2.05": (MEDIUM, "Exit or Disposal Costs"),
    "2.06": (HIGH, "Material Impairment"),
    "3.01": (HIGH, "Delisting / Listing Rule Failure"),
    "3.02": (MEDIUM, "Unregistered Equity Sales"),
    "3.03": (MEDIUM, "Modification to Security Holder Rights"),
    "4.01": (HIGH, "Auditor Change"),
    "4.02": (HIGH, "Non-Reliance on Prior Financials"),
    "5.01": (HIGH, "Change in Control"),
    "5.02": (MEDIUM, "Officer/Director Change"),
    "5.03": (LOW, "Bylaw Amendment / Fiscal Year Change"),
    "5.04": (LOW, "Trading Suspension Under Benefit Plan"),
    "5.05": (LOW, "Code of Ethics Amendment"),
    "5.06": (MEDIUM, "Shell Company Status Change"),
    "5.07": (LOW, "Shareholder Vote Results"),
    "5.08": (LOW, "Shareholder Director Nominations"),
    "6.01": (MEDIUM, "ABS Informational Material"),
    "6.02": (MEDIUM, "ABS Informational Material"),
    "6.03": (MEDIUM, "ABS Informational Material"),
    "6.04": (MEDIUM, "ABS Informational Material"),
    "6.05": (MEDIUM, "ABS Informational Material"),
    "7.01": (MEDIUM, "Regulation FD Disclosure"),
    "8.01": (MEDIUM, "Other Events"),
    "9.01": (LOW, "Financial Statements and Exhibits"),
}

TIER_RANK = {LOW: 0, MEDIUM: 1, HIGH: 2}


def score_filing(form_type: str, item_codes: str) -> tuple[str, str]:
    """Return (materiality_tier, event_type_label) for one filing."""
    codes = [c.strip() for c in item_codes.split(",") if c.strip()]

    if form_type == "6-K" or not codes:
        return MEDIUM, "Foreign Issuer Report (6-K)" if form_type == "6-K" else "Other Events"

    known = [ITEM_INFO[c] for c in codes if c in ITEM_INFO]
    if not known:
        return MEDIUM, f"Item {codes[0]}"

    best = max(known, key=lambda pair: TIER_RANK[pair[0]])
    primary_code = codes[0]
    primary_label = ITEM_INFO.get(primary_code, best)[1]
    label = f"{primary_code} — {primary_label}"
    return best[0], label
