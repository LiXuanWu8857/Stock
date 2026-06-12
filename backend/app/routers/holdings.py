from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List
from decimal import Decimal

from app.database import get_db
from app.models.models import Holding, User
from app.schemas.schemas import (
    HoldingCreate, HoldingUpdate, HoldingResponse, PortfolioSummary
)
from app.services.stock_service import get_quotes_bulk

router = APIRouter(prefix="/api/holdings", tags=["holdings"])

DEFAULT_USER_ID = 1


async def ensure_default_user(db: AsyncSession):
    """Ensure the default user exists."""
    result = await db.execute(select(User).where(User.id == DEFAULT_USER_ID))
    user = result.scalar_one_or_none()
    if not user:
        user = User(id=DEFAULT_USER_ID, email="user@example.com", name="Portfolio Owner")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.get("", response_model=PortfolioSummary)
async def get_holdings(db: AsyncSession = Depends(get_db)):
    """Get all holdings with live prices and portfolio summary."""
    await ensure_default_user(db)

    result = await db.execute(
        select(Holding).where(Holding.user_id == DEFAULT_USER_ID, Holding.shares > 0)
    )
    holdings = result.scalars().all()

    if not holdings:
        return PortfolioSummary(
            total_invested=0.0,
            total_value=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            holdings=[],
            holding_count=0,
        )

    # Fetch live prices for all holdings
    symbols_markets = [(h.symbol, h.market) for h in holdings]
    quotes = get_quotes_bulk(symbols_markets)

    total_invested = 0.0
    total_value = 0.0
    holding_responses = []

    for holding in holdings:
        key = f"{holding.symbol}:{holding.market}"
        quote = quotes.get(key, {})

        shares = float(holding.shares)
        avg_cost = float(holding.avg_cost)
        cost_basis = shares * avg_cost
        total_invested += cost_basis

        current_price = quote.get("price")
        if current_price is not None:
            current_value = shares * current_price
            total_value += current_value
            pnl = current_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
        else:
            current_value = cost_basis
            total_value += cost_basis
            pnl = 0.0
            pnl_pct = 0.0

        holding_responses.append(
            HoldingResponse(
                id=holding.id,
                user_id=holding.user_id,
                symbol=holding.symbol,
                market=holding.market,
                shares=holding.shares,
                avg_cost=holding.avg_cost,
                created_at=holding.created_at,
                updated_at=holding.updated_at,
                current_price=current_price,
                current_value=current_value,
                cost_basis=cost_basis,
                pnl=pnl,
                pnl_pct=pnl_pct,
                weight=0.0,  # Will be computed after total_value is known
                stock_name=quote.get("name"),
                currency=quote.get("currency"),
                change=quote.get("change"),
                change_pct=quote.get("change_pct"),
            )
        )

    # Compute weight for each holding
    if total_value > 0:
        for hr in holding_responses:
            if hr.current_value is not None:
                hr.weight = round((hr.current_value / total_value) * 100, 2)

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    return PortfolioSummary(
        total_invested=round(total_invested, 2),
        total_value=round(total_value, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        holdings=holding_responses,
        holding_count=len(holding_responses),
    )


@router.post("", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
async def create_holding(
    holding_in: HoldingCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new holding or update existing one."""
    await ensure_default_user(db)

    symbol = holding_in.symbol.strip().upper()
    market = holding_in.market

    # Check if holding already exists
    result = await db.execute(
        select(Holding).where(
            Holding.user_id == DEFAULT_USER_ID,
            Holding.symbol == symbol,
            Holding.market == market,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update using weighted average cost
        old_shares = float(existing.shares)
        old_cost = float(existing.avg_cost)
        new_shares = float(holding_in.shares)
        new_cost = float(holding_in.avg_cost)

        total_shares = old_shares + new_shares
        if total_shares > 0:
            new_avg_cost = (old_shares * old_cost + new_shares * new_cost) / total_shares
        else:
            new_avg_cost = new_cost

        existing.shares = Decimal(str(total_shares))
        existing.avg_cost = Decimal(str(round(new_avg_cost, 4)))
        await db.commit()
        await db.refresh(existing)
        holding = existing
    else:
        holding = Holding(
            user_id=DEFAULT_USER_ID,
            symbol=symbol,
            market=market,
            shares=holding_in.shares,
            avg_cost=holding_in.avg_cost,
        )
        db.add(holding)
        await db.commit()
        await db.refresh(holding)

    # Fetch live price
    from app.services.stock_service import get_quote
    quote = get_quote(symbol, market)

    shares = float(holding.shares)
    avg_cost = float(holding.avg_cost)
    cost_basis = shares * avg_cost
    current_price = quote.get("price")

    if current_price is not None:
        current_value = shares * current_price
        pnl = current_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
    else:
        current_value = cost_basis
        pnl = 0.0
        pnl_pct = 0.0

    return HoldingResponse(
        id=holding.id,
        user_id=holding.user_id,
        symbol=holding.symbol,
        market=holding.market,
        shares=holding.shares,
        avg_cost=holding.avg_cost,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
        current_price=current_price,
        current_value=current_value,
        cost_basis=cost_basis,
        pnl=pnl,
        pnl_pct=pnl_pct,
        weight=None,
        stock_name=quote.get("name"),
        currency=quote.get("currency"),
        change=quote.get("change"),
        change_pct=quote.get("change_pct"),
    )


@router.put("/{holding_id}", response_model=HoldingResponse)
async def update_holding(
    holding_id: int,
    holding_in: HoldingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing holding's shares or avg_cost."""
    result = await db.execute(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.user_id == DEFAULT_USER_ID,
        )
    )
    holding = result.scalar_one_or_none()

    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holding {holding_id} not found",
        )

    if holding_in.shares is not None:
        holding.shares = holding_in.shares
    if holding_in.avg_cost is not None:
        holding.avg_cost = holding_in.avg_cost

    await db.commit()
    await db.refresh(holding)

    from app.services.stock_service import get_quote
    quote = get_quote(holding.symbol, holding.market)

    shares = float(holding.shares)
    avg_cost = float(holding.avg_cost)
    cost_basis = shares * avg_cost
    current_price = quote.get("price")

    if current_price is not None:
        current_value = shares * current_price
        pnl = current_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0.0
    else:
        current_value = cost_basis
        pnl = 0.0
        pnl_pct = 0.0

    return HoldingResponse(
        id=holding.id,
        user_id=holding.user_id,
        symbol=holding.symbol,
        market=holding.market,
        shares=holding.shares,
        avg_cost=holding.avg_cost,
        created_at=holding.created_at,
        updated_at=holding.updated_at,
        current_price=current_price,
        current_value=current_value,
        cost_basis=cost_basis,
        pnl=pnl,
        pnl_pct=pnl_pct,
        weight=None,
        stock_name=quote.get("name"),
        currency=quote.get("currency"),
        change=quote.get("change"),
        change_pct=quote.get("change_pct"),
    )


@router.delete("/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    holding_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a holding (set shares to 0 - soft delete)."""
    result = await db.execute(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.user_id == DEFAULT_USER_ID,
        )
    )
    holding = result.scalar_one_or_none()

    if not holding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Holding {holding_id} not found",
        )

    # Soft delete: set shares to 0
    holding.shares = Decimal("0")
    await db.commit()
    return None
