"""
Portfolio performance tracking.

Net profit formula (避免被入金干擾):
    net_profit = total_asset - invested_amount + withdrawn_amount

Cash flows are derived from the transactions table:
    invested_amount  = cumulative BUY  (price * shares)
    withdrawn_amount = cumulative SELL (price * shares)

TWR (Time-Weighted Return) removes the distortion caused by the size and
timing of deposits, chaining daily sub-period returns:
    r_t = (MV_t - MV_{t-1} - F_t) / (MV_{t-1} + F_t)
    TWR = prod(1 + r_t) - 1
where F_t is the net external flow (buys - sells) on day t.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import DailySnapshot, Holding, Transaction
from app.services.stock_service import _build_ticker_symbol, get_quotes_bulk

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = 1


async def compute_current_snapshot(db: AsyncSession) -> Dict[str, float]:
    """Compute today's snapshot from live quotes and the transaction ledger."""
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == DEFAULT_USER_ID)
    )
    transactions = result.scalars().all()

    invested = 0.0
    withdrawn = 0.0
    for tx in transactions:
        amount = float(tx.price) * float(tx.shares)
        if tx.action == "BUY":
            invested += amount
        else:
            withdrawn += amount

    result = await db.execute(
        select(Holding).where(
            Holding.user_id == DEFAULT_USER_ID, Holding.shares > 0
        )
    )
    holdings = result.scalars().all()

    market_value = 0.0
    if holdings:
        quotes = get_quotes_bulk([(h.symbol, h.market) for h in holdings])
        for h in holdings:
            quote = quotes.get(f"{h.symbol}:{h.market}", {})
            price = quote.get("price")
            if price is None:
                price = float(h.avg_cost)
            market_value += float(h.shares) * price

    cash = 0.0  # MVP does not track a cash account yet
    total_asset = market_value + cash
    net_profit = total_asset - invested + withdrawn

    return {
        "invested_amount": round(invested, 4),
        "withdrawn_amount": round(withdrawn, 4),
        "market_value": round(market_value, 4),
        "cash": cash,
        "total_asset": round(total_asset, 4),
        "net_profit": round(net_profit, 4),
    }


async def upsert_snapshot(
    db: AsyncSession, snap_date: date, data: Dict[str, float]
) -> None:
    """Insert or update the snapshot row for the given date."""
    result = await db.execute(
        select(DailySnapshot).where(
            DailySnapshot.user_id == DEFAULT_USER_ID,
            DailySnapshot.date == snap_date,
        )
    )
    snapshot = result.scalar_one_or_none()

    if snapshot:
        for field, value in data.items():
            setattr(snapshot, field, Decimal(str(value)))
    else:
        snapshot = DailySnapshot(
            user_id=DEFAULT_USER_ID,
            date=snap_date,
            **{k: Decimal(str(v)) for k, v in data.items()},
        )
        db.add(snapshot)

    await db.commit()


def _fetch_close_history(
    symbols_markets: List[Tuple[str, str]], start: date, end: date
) -> Optional[pd.DataFrame]:
    """
    Download daily close prices for all symbols, reindexed to a full calendar
    so weekends/holidays carry the last known close (forward-fill).
    Columns are keyed by "SYMBOL:MARKET".
    """
    ticker_to_key = {
        _build_ticker_symbol(sym, mkt): f"{sym}:{mkt}"
        for sym, mkt in symbols_markets
    }
    tickers = list(ticker_to_key.keys())

    try:
        data = yf.download(
            " ".join(tickers),
            start=start - timedelta(days=10),
            end=end + timedelta(days=1),
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        logger.error(f"Failed to download price history: {e}")
        return None

    if data is None or data.empty:
        return None

    close = data["Close"]
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers[0])

    close.index = pd.to_datetime(close.index).tz_localize(None)
    calendar = pd.date_range(start=start, end=end, freq="D")
    close = close.reindex(close.index.union(calendar)).ffill().bfill()
    close = close.reindex(calendar)
    close = close.rename(columns=ticker_to_key)
    return close


async def backfill_snapshots(db: AsyncSession) -> int:
    """
    Rebuild all daily snapshots from the transaction ledger using historical
    closing prices. Returns the number of snapshot rows written.
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == DEFAULT_USER_ID)
        .order_by(Transaction.date.asc(), Transaction.created_at.asc())
    )
    transactions = result.scalars().all()
    if not transactions:
        return 0

    start = transactions[0].date
    today = date.today()

    symbols_markets = sorted({(tx.symbol, tx.market) for tx in transactions})
    prices = _fetch_close_history(symbols_markets, start, today)

    # Replace any previous backfill so the curve stays consistent
    await db.execute(
        delete(DailySnapshot).where(DailySnapshot.user_id == DEFAULT_USER_ID)
    )

    shares: Dict[str, float] = {}
    invested = 0.0
    withdrawn = 0.0
    tx_idx = 0
    count = 0

    current = start
    while current <= today:
        while tx_idx < len(transactions) and transactions[tx_idx].date <= current:
            tx = transactions[tx_idx]
            key = f"{tx.symbol}:{tx.market}"
            amount = float(tx.price) * float(tx.shares)
            if tx.action == "BUY":
                shares[key] = shares.get(key, 0.0) + float(tx.shares)
                invested += amount
            else:
                shares[key] = shares.get(key, 0.0) - float(tx.shares)
                withdrawn += amount
            tx_idx += 1

        market_value = 0.0
        ts = pd.Timestamp(current)
        for key, qty in shares.items():
            if qty <= 0:
                continue
            price = None
            if prices is not None and key in prices.columns and ts in prices.index:
                value = prices.at[ts, key]
                if pd.notna(value):
                    price = float(value)
            if price is None:
                price = 0.0
            market_value += qty * price

        total_asset = market_value
        net_profit = total_asset - invested + withdrawn

        db.add(
            DailySnapshot(
                user_id=DEFAULT_USER_ID,
                date=current,
                invested_amount=Decimal(str(round(invested, 4))),
                withdrawn_amount=Decimal(str(round(withdrawn, 4))),
                market_value=Decimal(str(round(market_value, 4))),
                cash=Decimal("0"),
                total_asset=Decimal(str(round(total_asset, 4))),
                net_profit=Decimal(str(round(net_profit, 4))),
            )
        )
        count += 1
        current += timedelta(days=1)

    await db.commit()
    return count


def compute_series(snapshots: List[DailySnapshot]) -> List[Dict]:
    """
    Convert snapshot rows (sorted by date asc) into chart points with
    cumulative ROI and TWR. Each point carries `_wealth` (the TWR wealth
    index, prod of 1+r) so callers can rebase TWR for a sub-range.
    """
    points: List[Dict] = []
    wealth = 1.0
    prev_mv: Optional[float] = None
    prev_invested = 0.0
    prev_withdrawn = 0.0

    for snap in snapshots:
        invested = float(snap.invested_amount)
        withdrawn = float(snap.withdrawn_amount)
        mv = float(snap.market_value)
        net_profit = float(snap.net_profit)

        flow = (invested - prev_invested) - (withdrawn - prev_withdrawn)
        base = (prev_mv if prev_mv is not None else 0.0) + flow
        if base > 0:
            r = (mv - (prev_mv if prev_mv is not None else 0.0) - flow) / base
        else:
            r = 0.0
        wealth *= 1.0 + r

        roi_pct = (net_profit / invested * 100) if invested > 0 else 0.0

        points.append(
            {
                "date": snap.date,
                "invested_amount": invested,
                "withdrawn_amount": withdrawn,
                "market_value": mv,
                "cash": float(snap.cash),
                "total_asset": float(snap.total_asset),
                "net_profit": net_profit,
                "roi_pct": round(roi_pct, 4),
                "twr_pct": round((wealth - 1.0) * 100, 4),
                "_wealth": wealth,
            }
        )

        prev_mv = mv
        prev_invested = invested
        prev_withdrawn = withdrawn

    return points


def slice_and_rebase(points: List[Dict], days: Optional[int]) -> List[Dict]:
    """
    Keep only the last `days` days (None = ALL) and rebase TWR so the range
    starts at 0%, using the wealth index of the point just before the range.
    """
    if not points:
        return []

    if days is None:
        selected = points
        base_wealth = 1.0
    else:
        cutoff = date.today() - timedelta(days=days)
        start_idx = next(
            (i for i, p in enumerate(points) if p["date"] >= cutoff), len(points)
        )
        selected = points[start_idx:]
        base_wealth = points[start_idx - 1]["_wealth"] if start_idx > 0 else 1.0

    rebased = []
    for p in selected:
        q = dict(p)
        q["twr_pct"] = round((p["_wealth"] / base_wealth - 1.0) * 100, 4)
        rebased.append(q)
    return rebased


def max_drawdown_pct(points: List[Dict]) -> float:
    """Max peak-to-trough decline of the TWR wealth index within the range."""
    peak = 0.0
    max_dd = 0.0
    for p in points:
        w = p["_wealth"]
        if w > peak:
            peak = w
        if peak > 0:
            dd = (w - peak) / peak
            if dd < max_dd:
                max_dd = dd
    return round(max_dd * 100, 4)
