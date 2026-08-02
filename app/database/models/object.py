from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Object(Base):
    __tablename__ = "objects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    engineer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    monthly_day: Mapped[int] = mapped_column(nullable=False)
    next_inspection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    semiannual_service: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invoice_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    engineer: Mapped["User"] = relationship(foreign_keys=[engineer_id])
