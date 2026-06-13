from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from typing import Optional, List
import asyncio
import json
import logging

from app.services.stock_service import get_quote, get_quotes_bulk, detect_market

router = APIRouter(tags=["quotes"])

logger = logging.getLogger(__name__)


@router.get("/api/quotes/{symbol}")
async def get_live_quote(
    symbol: str,
    market: Optional[str] = Query(None, description="Market: TW or US. Auto-detected if not provided."),
):
    """
    Get a live quote for a stock symbol.
    If market is not provided, it will be auto-detected.
    """
    clean_symbol = symbol.strip().upper()

    if market is None:
        market = detect_market(clean_symbol)
    else:
        market = market.upper()
        if market not in ("TW", "US"):
            market = detect_market(clean_symbol)

    quote = get_quote(clean_symbol, market)
    return quote


@router.websocket("/ws/quotes")
async def websocket_quotes(websocket: WebSocket):
    """
    WebSocket endpoint for live quote streaming.

    Client sends JSON: {"symbols": ["2330:TW", "AAPL:US"]}
    Server pushes updates every 30 seconds.

    Message format from server:
    {
        "type": "quotes",
        "data": {
            "2330:TW": {"symbol": "2330", "market": "TW", "price": 850.0, ...},
            "AAPL:US": {"symbol": "AAPL", "market": "US", "price": 195.0, ...}
        }
    }
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    subscribed_symbols: List[tuple] = []
    update_interval = 30  # seconds

    async def send_quotes():
        if not subscribed_symbols:
            return
        try:
            quotes = get_quotes_bulk(subscribed_symbols)
            await websocket.send_json({
                "type": "quotes",
                "data": quotes,
            })
        except Exception as e:
            logger.error(f"Error sending quotes via WebSocket: {e}")

    try:
        while True:
            # Use wait_for to allow periodic updates while waiting for client messages
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=update_interval)
                try:
                    message = json.loads(raw)
                    symbols_raw = message.get("symbols", [])

                    # Parse symbols like "2330:TW" or "AAPL:US"
                    parsed = []
                    for s in symbols_raw:
                        if ":" in s:
                            parts = s.split(":", 1)
                            sym = parts[0].strip().upper()
                            mkt = parts[1].strip().upper()
                            if mkt in ("TW", "US"):
                                parsed.append((sym, mkt))
                        else:
                            sym = s.strip().upper()
                            mkt = detect_market(sym)
                            parsed.append((sym, mkt))

                    subscribed_symbols = parsed

                    # Send immediate update after subscription change
                    await send_quotes()

                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})

            except asyncio.TimeoutError:
                # Timeout reached - send periodic update
                await send_quotes()

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
