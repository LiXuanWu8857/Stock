"""
Stock quote service.

Taiwan stocks  → TWSE/TPEX official API (primary)
               Primary source is the Taiwan Stock Exchange MIS API which returns
               real-time prices during market hours and the last close otherwise.
               OTC/TPEx ETFs (5-digit codes starting with "00") use the otc_ prefix.
               yfinance is used as a fallback.

US stocks      → yfinance with pre/post-market support.
               is_extended=True is set when the returned price is from
               pre-market or after-hours trading.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import httpx
import yfinance as yf

logger = logging.getLogger(__name__)

TWSE_MIS_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
_HTTP_HEADERS = {
    "Referer": "https://mis.twse.com.tw/",
    "User-Agent": "Mozilla/5.0",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect_market(symbol: str) -> str:
    return "TW" if symbol.strip().upper().isdigit() else "US"


def _build_ticker_symbol(symbol: str, market: str) -> str:
    sym = symbol.strip().upper()
    if market == "TW":
        return sym if sym.endswith(".TW") else f"{sym}.TW"
    return sym


def _is_otc(symbol: str) -> bool:
    """ETFs like 00878, 00919 trade on TPEx (上櫃), not the main TSE board."""
    sym = symbol.strip()
    return len(sym) == 5 and sym.startswith("00")


def _make_result(symbol: str, market: str) -> Dict:
    return {
        "symbol": symbol.strip().upper(),
        "market": market,
        "price": None,
        "change": None,
        "change_pct": None,
        "name": symbol.strip().upper(),
        "currency": "TWD" if market == "TW" else "USD",
        "error": None,
        "is_extended": False,
    }


# ---------------------------------------------------------------------------
# Taiwan stocks — TWSE/TPEX MIS API
# ---------------------------------------------------------------------------

def _twse_ex_ch(symbol: str) -> str:
    sym = symbol.strip().upper()
    prefix = "otc" if _is_otc(sym) else "tse"
    return f"{prefix}_{sym.lower()}.tw"


def _get_tw_quote_twse(symbol: str) -> Optional[Dict]:
    """Fetch quote from Taiwan Stock Exchange MIS API."""
    ex_ch = _twse_ex_ch(symbol)
    url = f"{TWSE_MIS_URL}?ex_ch={ex_ch}&_={int(time.time() * 1000)}"
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url, headers=_HTTP_HEADERS)
            data = resp.json()

        items = data.get("msgArray", [])
        if not items:
            return None

        item = items[0]
        price_str = item.get("z", "-")
        if not price_str or price_str == "-":
            # Market closed — fall back to previous close
            price_str = item.get("y", "-")
        if not price_str or price_str == "-":
            return None

        price = float(price_str)
        prev_close = float(item.get("y") or 0)
        change = round(price - prev_close, 2) if prev_close > 0 else 0.0
        change_pct = round(change / prev_close * 100, 2) if prev_close > 0 else 0.0

        return {
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "name": item.get("n", symbol.strip().upper()),
            "currency": "TWD",
            "is_extended": False,
        }
    except Exception as e:
        logger.warning(f"TWSE API failed for {symbol}: {e}")
        return None


def _get_tw_quote_yfinance(symbol: str) -> Optional[Dict]:
    """Fallback: fetch Taiwan quote via yfinance."""
    try:
        ticker = yf.Ticker(_build_ticker_symbol(symbol, "TW"))
        hist = ticker.history(period="5d")
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change = round(price - prev_close, 2)
        change_pct = round(change / prev_close * 100, 2) if prev_close > 0 else 0.0
        name = symbol.strip().upper()
        try:
            name = ticker.info.get("longName") or ticker.info.get("shortName") or name
        except Exception:
            pass
        return {
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "name": name,
            "currency": "TWD",
            "is_extended": False,
        }
    except Exception as e:
        logger.warning(f"yfinance TW fallback failed for {symbol}: {e}")
        return None


# ---------------------------------------------------------------------------
# US stocks — yfinance with pre/post-market
# ---------------------------------------------------------------------------

def _get_us_quote_yfinance(symbol: str) -> Optional[Dict]:
    """Fetch US quote; prefer pre/post-market price when available."""
    try:
        ticker = yf.Ticker(symbol.strip().upper())
        fi = ticker.fast_info

        price: Optional[float] = None
        is_extended = False

        # Pre-market
        try:
            p = fi.pre_market_price
            if p and p > 0:
                price = float(p)
                is_extended = True
        except Exception:
            pass

        # Post-market
        if price is None:
            try:
                p = fi.post_market_price
                if p and p > 0:
                    price = float(p)
                    is_extended = True
            except Exception:
                pass

        # Regular market
        if price is None:
            for attr in ("last_price", "regular_market_price"):
                try:
                    p = getattr(fi, attr)
                    if p and p > 0:
                        price = float(p)
                        break
                except Exception:
                    pass

        # History fallback
        if price is None:
            hist = ticker.history(period="5d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        if price is None:
            return None

        prev_close: Optional[float] = None
        for attr in ("previous_close", "regular_market_previous_close"):
            try:
                pc = getattr(fi, attr)
                if pc and pc > 0:
                    prev_close = float(pc)
                    break
            except Exception:
                pass

        change = round(price - prev_close, 4) if prev_close else 0.0
        change_pct = round(change / prev_close * 100, 2) if prev_close else 0.0

        name = symbol.strip().upper()
        try:
            info = ticker.info
            name = info.get("longName") or info.get("shortName") or name
        except Exception:
            pass

        return {
            "price": round(price, 4),
            "change": change,
            "change_pct": change_pct,
            "name": name,
            "currency": "USD",
            "is_extended": is_extended,
        }
    except Exception as e:
        logger.error(f"yfinance US failed for {symbol}: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_quote(symbol: str, market: str) -> Dict:
    sym = symbol.strip().upper()
    result = _make_result(sym, market)

    if market == "TW":
        data = _get_tw_quote_twse(sym) or _get_tw_quote_yfinance(sym)
    else:
        data = _get_us_quote_yfinance(sym)

    if data:
        result.update(data)
    else:
        result["error"] = f"No price data for {sym}"

    return result


def get_quotes_bulk(symbols_markets: List[Tuple[str, str]]) -> Dict[str, Dict]:
    """
    Fetch quotes for multiple stocks.
    Taiwan stocks: batch via TWSE MIS API (supports pipe-separated ex_ch).
    US stocks: fetched individually via yfinance.
    """
    if not symbols_markets:
        return {}

    results: Dict[str, Dict] = {}
    tw_symbols = [(s, m) for s, m in symbols_markets if m == "TW"]
    us_symbols = [(s, m) for s, m in symbols_markets if m == "US"]

    # --- Taiwan batch ---
    if tw_symbols:
        ex_ch_list = "|".join(_twse_ex_ch(s) for s, _ in tw_symbols)
        url = f"{TWSE_MIS_URL}?ex_ch={ex_ch_list}&_={int(time.time() * 1000)}"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=_HTTP_HEADERS)
                data = resp.json()

            items_by_code = {}
            for item in data.get("msgArray", []):
                code = item.get("c", "").upper()
                items_by_code[code] = item

            for sym, market in tw_symbols:
                key = f"{sym}:{market}"
                result = _make_result(sym, market)
                item = items_by_code.get(sym.upper())

                if item:
                    price_str = item.get("z", "-")
                    if not price_str or price_str == "-":
                        price_str = item.get("y", "-")
                    if price_str and price_str != "-":
                        price = float(price_str)
                        prev_close = float(item.get("y") or 0)
                        change = round(price - prev_close, 2) if prev_close > 0 else 0.0
                        change_pct = round(change / prev_close * 100, 2) if prev_close > 0 else 0.0
                        result.update({
                            "price": price,
                            "change": change,
                            "change_pct": change_pct,
                            "name": item.get("n", sym),
                            "currency": "TWD",
                        })
                    else:
                        result["error"] = f"No price data for {sym}"
                else:
                    # Symbol not in batch response, try individually
                    individual = _get_tw_quote_twse(sym) or _get_tw_quote_yfinance(sym)
                    if individual:
                        result.update(individual)
                    else:
                        result["error"] = f"No price data for {sym}"

                results[key] = result

        except Exception as e:
            logger.warning(f"TWSE batch failed: {e}, falling back to individual")
            for sym, market in tw_symbols:
                key = f"{sym}:{market}"
                results[key] = get_quote(sym, market)

    # --- US individual ---
    for sym, market in us_symbols:
        key = f"{sym}:{market}"
        results[key] = get_quote(sym, market)

    return results
