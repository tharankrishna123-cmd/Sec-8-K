"""Static registry of the 30 tracked companies.

CIKs are resolved once from SEC's company_tickers.json and hardcoded here since
they never change. To add or remove a company, edit this list and restart the
app (or wait for the next scheduled refresh) — no migration needed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    sector: str
    cik: str
    active: bool = True
    note: str | None = None


SECTORS = ["Financial Services", "Energy", "Technology", "Industrials"]

COMPANIES: list[Company] = [
    # Financial Services
    Company("JPM", "JPMorgan Chase", "Financial Services", "0000019617"),
    Company("GS", "Goldman Sachs", "Financial Services", "0000886982"),
    Company("MS", "Morgan Stanley", "Financial Services", "0000895421"),
    Company("BAC", "Bank of America", "Financial Services", "0000070858"),
    Company("C", "Citigroup", "Financial Services", "0000831001"),
    Company("WFC", "Wells Fargo", "Financial Services", "0000072971"),
    Company("TD", "TD Bank", "Financial Services", "0000947263"),
    Company("BNS", "Scotiabank", "Financial Services", "0000009631"),
    # Energy
    Company("XOM", "ExxonMobil", "Energy", "0000034088"),
    Company("CVX", "Chevron", "Energy", "0000093410"),
    Company("COP", "ConocoPhillips", "Energy", "0001163165"),
    Company("SU", "Suncor", "Energy", "0000311337"),
    Company("CNQ", "Canadian Natural Resources", "Energy", "0001017413"),
    Company("ENB", "Enbridge", "Energy", "0000895728"),
    Company("TRP", "TC Energy", "Energy", "0001232384"),
    Company(
        "PXD",
        "Pioneer Natural Resources",
        "Energy",
        "0001038357",
        active=False,
        note="Acquired by ExxonMobil (XOM) on May 3, 2024 — no longer files independently.",
    ),
    # Technology
    Company("AAPL", "Apple", "Technology", "0000320193"),
    Company("MSFT", "Microsoft", "Technology", "0000789019"),
    Company("GOOGL", "Alphabet", "Technology", "0001652044"),
    Company("META", "Meta", "Technology", "0001326801"),
    Company("AMZN", "Amazon", "Technology", "0001018724"),
    Company("NVDA", "Nvidia", "Technology", "0001045810"),
    Company("CRM", "Salesforce", "Technology", "0001108524"),
    # Industrials
    Company("TFII", "TFI International", "Industrials", "0001588823"),
    Company("XPO", "XPO Logistics", "Industrials", "0001166003"),
    Company("FDX", "FedEx", "Industrials", "0001048911"),
    Company("UPS", "UPS", "Industrials", "0001090727"),
    Company("CAT", "Caterpillar", "Industrials", "0000018230"),
    Company("HON", "Honeywell", "Industrials", "0000773840"),
    Company("DE", "Deere & Co", "Industrials", "0000315189"),
]

COMPANIES_BY_TICKER: dict[str, Company] = {c.ticker: c for c in COMPANIES}
