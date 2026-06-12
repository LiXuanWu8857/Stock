import yfinance as yf
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


def detect_market(symbol: str) -> str:
    """
    Detect market based on symbol.
    If symbol is all digits (e.g., '2330', '00878'), it's TW market.
    Otherwise it's US market (e.g., 'AAPL', 'TSLA').
    """
    clean = symbol.strip().upper()
    if clean.isdigit():
        return "TW"
    return "US"


def _build_ticker_symbol(symbol: str, market: str) -> str:
    """
    Build the yfinance ticker symbol.
    Taiwan stocks: append .TW suffix (e.g., 2330 -> 2330.TW)
    US stocks: use symbol directly (e.g., AAPL)
    """
    sym = symbol.strip().upper()
    if market == "TW":
        if not sym.endswith(".TW"):
            return f"{sym}.TW"
        return sym
    return sym


def get_quote(symbol: str, market: str) -> Dict:
    """
    Fetch live quote for a single stock.
    Returns dict with price, change, change_pct, name, currency.
    Returns None values if symbol not found or error occurs.
    """
    ticker_symbol = _build_ticker_symbol(symbol, market)
    result = {
        "symbol": symbol.strip().upper(),
        "market": market,
        "price": None,
        "change": None,
        "change_pct": None,
        "name": symbol.strip().upper(),
        "currency": "TWD" if market == "TW" else "USD",
        "error": None,
    }

    try:
        ticker = yf.Ticker(ticker_symbol)
        fast_info = ticker.fast_info

        price = None
        # Try multiple attributes for current price
        try:
            price = fast_info.last_price
        except Exception:
            pass

        if price is None or price == 0:
            try:
                price = fast_info.regular_market_price
            except Exception:
                pass

        if price is None or price == 0:
            # Fallback to history
            hist = ticker.history(period="2d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])

        if price is None or price == 0:
            result["error"] = f"No price data for {ticker_symbol}"
            return result

        result["price"] = float(price)

        # Try to get previous close for change calculation
        prev_close = None
        try:
            prev_close = fast_info.previous_close
        except Exception:
            pass

        if prev_close is None or prev_close == 0:
            try:
                prev_close = fast_info.regular_market_previous_close
            except Exception:
                pass

        if prev_close and prev_close > 0:
            change = float(price) - float(prev_close)
            change_pct = (change / float(prev_close)) * 100
            result["change"] = round(change, 4)
            result["change_pct"] = round(change_pct, 2)
        else:
            result["change"] = 0.0
            result["change_pct"] = 0.0

        # Get stock name
        try:
            info = ticker.info
            name = info.get("longName") or info.get("shortName") or symbol.strip().upper()
            result["name"] = name
            currency = info.get("currency")
            if currency:
                result["currency"] = currency
        except Exception:
            pass

        return result

    except Exception as e:
        logger.error(f"Error fetching quote for {ticker_symbol}: {e}")
        result["error"] = str(e)
        return result


def get_quotes_bulk(symbols_markets: List[Tuple[str, str]]) -> Dict[str, Dict]:
    """
    Fetch live quotes for multiple stocks efficiently.
    symbols_markets: list of (symbol, market) tuples
    Returns dict mapping "SYMBOL:MARKET" -> quote dict
    """
    results = {}

    if not symbols_markets:
        return results

    # Build ticker symbols for batch download
    ticker_map = {}  # ticker_symbol -> (symbol, market)
    for symbol, market in symbols_markets:
        ticker_sym = _build_ticker_symbol(symbol, market)
        key = f"{symbol.strip().upper()}:{market}"
        ticker_map[ticker_sym] = (symbol.strip().upper(), market, key)

    # Try batch download first for efficiency
    if len(ticker_map) > 1:
        try:
            ticker_symbols = list(ticker_map.keys())
            tickers_str = " ".join(ticker_symbols)
            data = yf.download(tickers_str, period="2d", progress=False, auto_adjust=True)

            if not data.empty:
                for ticker_sym, (symbol, market, key) in ticker_map.items():
                    result = {
                        "symbol": symbol,
                        "market": market,
                        "price": None,
                        "change": None,
                        "change_pct": None,
                        "name": symbol,
                        "currency": "TWD" if market == "TW" else "USD",
                        "error": None,
                    }
                    try:
                        if len(ticker_symbols) == 1:
                            close_data = data["Close"]
                        else:
                            close_data = data["Close"][ticker_sym]

                        if not close_data.empty and len(close_data) >= 1:
                            price = float(close_data.iloc[-1])
                            result["price"] = price

                            if len(close_data) >= 2:
                                prev_close = float(close_data.iloc[-2])
                                if prev_close > 0:
                                    change = price - prev_close
                                    change_pct = (change / prev_close) * 100
                                    result["change"] = round(change, 4)
                                    result["change_pct"] = round(change_pct, 2)
                                else:
                                    result["change"] = 0.0
                                    result["change_pct"] = 0.0
                            else:
                                result["change"] = 0.0
                                result["change_pct"] = 0.0
                    except Exception as e:
                        result["error"] = str(e)

                    results[key] = result

                # Fill in missing results individually
                missing = [(s, m) for s, m, k in ticker_map.values() if k not in results or results[k]["price"] is None]
                for symbol, market in missing:
                    key = f"{symbol}:{market}"
                    results[key] = get_quote(symbol, market)

                return results
        except Exception as e:
            logger.warning(f"Batch download failed, falling back to individual: {e}")

    # Individual fetch fallback
    for symbol, market in symbols_markets:
        key = f"{symbol.strip().upper()}:{market}"
        results[key] = get_quote(symbol, market)

    return results
