from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, List, Optional
import pandas as pd
import requests
import yfinance as yf
from .config import CONFIG


class PriceProvider(Protocol):
	def fetch_daily_ohlc(self, ticker: str, days: int) -> pd.DataFrame: ...


@dataclass
class YFinanceProvider:
	def fetch_daily_ohlc(self, ticker: str, days: int) -> pd.DataFrame:
		df = yf.download(ticker, period=f"{days}d", interval="1d", progress=False)
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
		# NOTE: Replace with actual Dhan market data endpoint if available
		# Placeholder returns empty frame to not block flow
		return pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])  # noqa: E501


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
	# If user already passed a likely symbol, try it first
	q = query.strip().upper()
	if "." in q:
		return q
	# Prefer NSE symbols
	quotes = search_symbol_yahoo(q)
	for item in quotes:
		symbol = item.get("symbol") or ""
		exch = (item.get("exchDisp") or item.get("exchange") or "").upper()
		if symbol.endswith(".NS") or exch.startswith("NS") or exch == "NSE":
			return symbol if symbol.endswith(".NS") else f"{symbol}.NS"
	# Fallback to first result
	if quotes:
		sym = quotes[0].get("symbol") or ""
		if sym and not sym.endswith(".NS") and (quotes[0].get("exchDisp","")) == "NSE":
			return f"{sym}.NS"
		return sym or None
	return None