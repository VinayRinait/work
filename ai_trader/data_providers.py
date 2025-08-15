from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, List, Optional
import pandas as pd
import requests
import yfinance as yf
from .config import CONFIG
from .dhan_client import DhanClient


class PriceProvider(Protocol):
	def fetch_daily_ohlc(self, ticker: str, days: int) -> pd.DataFrame: ...


@dataclass
class YFinanceProvider:
	def fetch_daily_ohlc(self, ticker: str, days: int) -> pd.DataFrame:
		df = yf.download(ticker, period=f"{days}d", interval="1d", progress=False, auto_adjust=False)
		if df.empty:
			return df
		df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
		df.index = pd.to_datetime(df.index)
		df["date"] = df.index.date.astype(str)
		df["ticker"] = ticker
		return df[["ticker", "date", "open", "high", "low", "close", "volume"]]


@dataclass
class DhanProvider:
	headers: dict

	def fetch_daily_ohlc(self, ticker: str, days: int) -> pd.DataFrame:
		client = DhanClient()
		q = client.get_quote(ticker)
		if not q:
			return pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])  # noqa: E501
		# Dhan quote fields vary; try to map close/ltp
		close = q.get("close") or q.get("closePrice") or q.get("prevClose") or q.get("lastPrice") or q.get("ltp")
		if close is None:
			return pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])  # noqa: E501
		from datetime import datetime
		asof = datetime.utcnow().strftime("%Y-%m-%d")
		row = {
			"ticker": ticker,
			"date": asof,
			"open": float(close),
			"high": float(close),
			"low": float(close),
			"close": float(close),
			"volume": float(q.get("volume") or 0),
		}
		return pd.DataFrame([row])


def get_providers() -> List[PriceProvider]:
	providers: List[PriceProvider] = []
	for name in CONFIG.data_providers or ["YFINANCE"]:
		if name == "YFINANCE":
			providers.append(YFinanceProvider())
		elif name == "DHAN":
			headers = {
				"access-token": CONFIG.dhan_access_token or "",
				"Content-Type": "application/json",
			}
			providers.append(DhanProvider(headers=headers))
	return providers


def fetch_with_fallback(ticker: str, days: int) -> pd.DataFrame:
	for provider in get_providers():
		df = provider.fetch_daily_ohlc(ticker, days)
		if not df.empty:
			return df
	return pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])  # noqa: E501


# --- Symbol search/resolution (Yahoo) ---

def search_symbol_yahoo(query: str, count: int = 5) -> List[dict]:
	try:
		resp = requests.get(
			"https://query1.finance.yahoo.com/v1/finance/search",
			params={"q": query, "quotesCount": count, "newsCount": 0},
			timeout=10,
		)
		resp.raise_for_status()
		data = resp.json()
		return data.get("quotes", [])
	except Exception:
		return []


def resolve_symbol(query: str) -> Optional[str]:
	# Normalize
	q = (query or "").strip()
	if not q:
		return None
	# If typed a symbol w/ suffix
	if "." in q:
		return q.upper()
	# Try full query first
	quotes = search_symbol_yahoo(q)
	# If failed, try without common stopwords and join
	if not quotes:
		stop = {"of", "the", "ltd", "limited", "company", "bank"}
		parts = [p for p in q.split() if p.lower() not in stop]
		alt = " ".join(parts) if parts else q
		quotes = search_symbol_yahoo(alt)
	# Prefer NSE
	for item in quotes:
		symbol = item.get("symbol") or ""
		exch = (item.get("exchDisp") or item.get("exchange") or "").upper()
		if symbol.endswith(".NS") or exch.startswith("NS") or exch == "NSE":
			return symbol if symbol.endswith(".NS") else f"{symbol}.NS"
	if quotes:
		sym = quotes[0].get("symbol") or ""
		if sym and not sym.endswith(".NS"):
			return f"{sym}.NS"
		return sym or None
	return None