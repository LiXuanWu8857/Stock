from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class HoldingCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    market: str = Field(..., pattern="^(TW|US)$")
    shares: Decimal = Field(..., gt=0)
    avg_cost: Decimal = Field(..., gt=0)


class HoldingUpdate(BaseModel):
    shares: Optional[Decimal] = Field(None, gt=0)
    avg_cost: Optional[Decimal] = Field(None, gt=0)


class HoldingResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    market: str
    shares: Decimal
    avg_cost: Decimal
    created_at: datetime
    updated_at: datetime
    # Computed fields from live data
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    cost_basis: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    weight: Optional[float] = None
    stock_name: Optional[str] = None
    currency: Optional[str] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    market: str = Field(..., pattern="^(TW|US)$")
    action: str = Field(..., pattern="^(BUY|SELL)$")
    price: Decimal = Field(..., gt=0)
    shares: Decimal = Field(..., gt=0)
    date: date
    note: Optional[str] = None


class TransactionResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    market: str
    action: str
    price: Decimal
    shares: Decimal
    date: date
    note: Optional[str] = None
    created_at: datetime
    total_amount: Optional[float] = None

    class Config:
        from_attributes = True


class DividendCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    market: str = Field(..., pattern="^(TW|US)$")
    amount_per_share: Decimal = Field(..., gt=0)
    shares_at_time: Decimal = Field(..., gt=0)
    total_amount: Decimal = Field(..., gt=0)
    ex_date: date
    pay_date: Optional[date] = None


class DividendResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    market: str
    amount_per_share: Decimal
    shares_at_time: Decimal
    total_amount: Decimal
    ex_date: date
    pay_date: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_invested: float
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    holdings: List[HoldingResponse]
    holding_count: int


class PerformancePoint(BaseModel):
    date: date
    invested_amount: float
    withdrawn_amount: float
    market_value: float
    cash: float
    total_asset: float
    net_profit: float
    roi_pct: float
    twr_pct: float


class PerformanceHistory(BaseModel):
    points: List[PerformancePoint]
    max_drawdown_pct: float
    range: str


class QuoteResponse(BaseModel):
    symbol: str
    market: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    name: Optional[str] = None
    currency: Optional[str] = None
    error: Optional[str] = None
    is_extended: bool = False  # True when price is pre/post-market
