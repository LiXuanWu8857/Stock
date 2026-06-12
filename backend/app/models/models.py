from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, Date, Text,
    ForeignKey, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    holdings = relationship("Holding", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    dividends = relationship("Dividend", back_populates="user")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    symbol = Column(String(20), nullable=False)
    market = Column(String(5), nullable=False)
    shares = Column(Numeric(15, 4), nullable=False, default=0)
    avg_cost = Column(Numeric(15, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("market IN ('TW', 'US')", name="check_holding_market"),
        UniqueConstraint("user_id", "symbol", "market", name="uq_user_symbol_market"),
    )

    user = relationship("User", back_populates="holdings")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    symbol = Column(String(20), nullable=False)
    market = Column(String(5), nullable=False)
    action = Column(String(10), nullable=False)
    price = Column(Numeric(15, 4), nullable=False)
    shares = Column(Numeric(15, 4), nullable=False)
    date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("market IN ('TW', 'US')", name="check_transaction_market"),
        CheckConstraint("action IN ('BUY', 'SELL')", name="check_transaction_action"),
    )

    user = relationship("User", back_populates="transactions")


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    date = Column(Date, nullable=False)
    invested_amount = Column(Numeric(18, 4), nullable=False, default=0)
    withdrawn_amount = Column(Numeric(18, 4), nullable=False, default=0)
    market_value = Column(Numeric(18, 4), nullable=False, default=0)
    cash = Column(Numeric(18, 4), nullable=False, default=0)
    total_asset = Column(Numeric(18, 4), nullable=False, default=0)
    net_profit = Column(Numeric(18, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_snapshot_user_date"),
    )

    user = relationship("User")


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    symbol = Column(String(20), nullable=False)
    market = Column(String(5), nullable=False)
    amount_per_share = Column(Numeric(15, 6), nullable=False)
    shares_at_time = Column(Numeric(15, 4), nullable=False)
    total_amount = Column(Numeric(15, 4), nullable=False)
    ex_date = Column(Date, nullable=False)
    pay_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("market IN ('TW', 'US')", name="check_dividend_market"),
    )

    user = relationship("User", back_populates="dividends")
