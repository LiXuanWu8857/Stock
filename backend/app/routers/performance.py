from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import DailySnapshot
from app.schemas.schemas import PerformanceHistory, PerformancePoint
from app.services.performance_service import (
    DEFAULT_USER_ID,
    backfill_snapshots,
    compute_current_snapshot,
    compute_series,
    max_drawdown_pct,
    slice_and_rebase,
    upsert_snapshot,
)

router = APIRouter(prefix="/api/performance", tags=["performance"])

RANGE_DAYS = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "ALL": None}


@router.get("", response_model=PerformanceHistory)
async def get_performance(
    range: str = Query("ALL", description="1M, 3M, 6M, 1Y, or ALL"),
    db: AsyncSession = Depends(get_db),
):
    """
    Performance history for charting: net profit, total asset, ROI and TWR
    per day, plus max drawdown within the selected range.
    Today's snapshot is refreshed with live prices on every call.
    """
    range_key = range.upper()
    days = RANGE_DAYS.get(range_key, None)
    if range_key not in RANGE_DAYS:
        range_key = "ALL"

    # Keep today's point live so the curve always ends at "now"
    current = await compute_current_snapshot(db)
    await upsert_snapshot(db, date.today(), current)

    result = await db.execute(
        select(DailySnapshot)
        .where(DailySnapshot.user_id == DEFAULT_USER_ID)
        .order_by(DailySnapshot.date.asc())
    )
    snapshots = result.scalars().all()

    full_series = compute_series(snapshots)
    ranged = slice_and_rebase(full_series, days)
    drawdown = max_drawdown_pct(ranged)

    points = [
        PerformancePoint(**{k: v for k, v in p.items() if k != "_wealth"})
        for p in ranged
    ]

    return PerformanceHistory(
        points=points,
        max_drawdown_pct=drawdown,
        range=range_key,
    )


@router.post("/snapshot")
async def take_snapshot(db: AsyncSession = Depends(get_db)):
    """Manually record today's snapshot (e.g. from a cron job after close)."""
    current = await compute_current_snapshot(db)
    await upsert_snapshot(db, date.today(), current)
    return {"status": "ok", "date": date.today().isoformat(), **current}


@router.post("/backfill")
async def backfill(db: AsyncSession = Depends(get_db)):
    """
    Rebuild the full snapshot history from the transaction ledger using
    historical closing prices. Overwrites existing snapshots.
    """
    count = await backfill_snapshots(db)
    return {"status": "ok", "snapshots_written": count}
