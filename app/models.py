from __future__ import annotations

import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CompanyModel(Base):
    __tablename__ = "companies"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    sector: Mapped[str] = mapped_column(String(50))
    cik: Mapped[str] = mapped_column(String(10))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    filings: Mapped[list["FilingModel"]] = relationship(back_populates="company")


class FilingModel(Base):
    __tablename__ = "filings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(ForeignKey("companies.ticker"), index=True)
    accession_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    form_type: Mapped[str] = mapped_column(String(10))
    filing_date: Mapped[datetime.date] = mapped_column(Date, index=True)
    item_codes: Mapped[str] = mapped_column(String(100), default="")
    event_type: Mapped[str] = mapped_column(String(200))
    materiality: Mapped[str] = mapped_column(String(10), index=True)
    primary_doc_url: Mapped[str] = mapped_column(String(500))

    memo_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    memo_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    memo_generated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    company: Mapped["CompanyModel"] = relationship(back_populates="filings")
