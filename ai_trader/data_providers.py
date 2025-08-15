from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, List
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