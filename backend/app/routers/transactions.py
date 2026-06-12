from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from decimal import Decimal
import datetime

from app.database import get_db
from app.models.models import Transaction, Holding, User
from app.schemas.schemas import TransactionCreate, TransactionResponse

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

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


async def _update_holding_after_transaction(
    db: AsyncSession,
    symbol: str,
    market: str,
    action: str,
    price: Decimal,
    shares: Decimal,
):
    """
    Update the holdings table after a BUY or SELL transaction.
    BUY: weighted average cost recalculation
    SELL: reduce shares (avg_cost stays the same)
    """
    result = await db.execute(
        select(Holding).where(
            Holding.user_id == DEFAULT_USER_ID,
            Holding.symbol == symbol,
            Holding.market == market,
        )
    )
    holding = result.scalar_one_or_none()

    if action == "BUY":
        if holding:
            old_shares = float(holding.shares)
            old_cost = float(holding.avg_cost)
            new_shares = float(shares)
            new_price = float(price)

            total_shares = old_shares + new_shares
            if total_shares > 0:
                weighted_avg = (old_shares * old_cost + new_shares * new_price) / total_shares
            else:
                weighted_avg = new_price

            holding.shares = Decimal(str(round(total_shares, 6)))
            holding.avg_cost = Decimal(str(round(weighted_avg, 6)))
        else:
            holding = Holding(
                user_id=DEFAULT_USER_ID,
                symbol=symbol,
                market=market,
                shares=shares,
                avg_cost=price,
            )
            db.add(holding)

    elif action == "SELL":
        if holding:
            new_shares = float(holding.shares) - float(shares)
            if new_shares < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot sell {shares} shares of {symbol}: only {holding.shares} shares held",
                )
            holding.shares = Decimal(str(round(max(new_shares, 0), 6)))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot sell {symbol}: no holdings found",
            )


@router.get("", response_model=List[TransactionResponse])
async def list_transactions(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all transactions, optionally filtered by symbol."""
    await ensure_default_user(db)

    query = select(Transaction).where(Transaction.user_id == DEFAULT_USER_ID)

    if symbol:
        query = query.where(Transaction.symbol == symbol.strip().upper())

    query = query.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    transactions = result.scalars().all()

    responses = []
    for tx in transactions:
        total_amount = float(tx.price) * float(tx.shares)
        if tx.action == "SELL":
            total_amount = -total_amount

        responses.append(
            TransactionResponse(
                id=tx.id,
                user_id=tx.user_id,
                symbol=tx.symbol,
                market=tx.market,
                action=tx.action,
                price=tx.price,
                shares=tx.shares,
                date=tx.date,
                note=tx.note,
                created_at=tx.created_at,
                total_amount=round(total_amount, 4),
            )
        )

    return responses


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    tx_in: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a new transaction (BUY or SELL).
    Automatically updates the corresponding holding's shares and avg_cost.
    """
    await ensure_default_user(db)

    symbol = tx_in.symbol.strip().upper()
    market = tx_in.market

    # Update holdings based on the transaction
    await _update_holding_after_transaction(
        db=db,
        symbol=symbol,
        market=market,
        action=tx_in.action,
        price=tx_in.price,
        shares=tx_in.shares,
    )

    # Create the transaction record
    transaction = Transaction(
        user_id=DEFAULT_USER_ID,
        symbol=symbol,
        market=market,
        action=tx_in.action,
        price=tx_in.price,
        shares=tx_in.shares,
        date=tx_in.date,
        note=tx_in.note,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    total_amount = float(transaction.price) * float(transaction.shares)
    if transaction.action == "SELL":
        total_amount = -total_amount

    return TransactionResponse(
        id=transaction.id,
        user_id=transaction.user_id,
        symbol=transaction.symbol,
        market=transaction.market,
        action=transaction.action,
        price=transaction.price,
        shares=transaction.shares,
        date=transaction.date,
        note=transaction.note,
        created_at=transaction.created_at,
        total_amount=round(total_amount, 4),
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction record."""
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == DEFAULT_USER_ID,
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found",
        )

    await db.delete(transaction)
    await db.commit()
    return None
