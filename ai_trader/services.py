from __future__ import annotations
from typing import Dict, Any, Optional
import pandas as pd
import sqlite3
from .config import CONFIG
from .selector import select_best_strategy
from .analysis import compute_indicators, recommend_action
from .storage import get_conn


def load_df_for(ticker: str) -> pd.DataFrame:
	with get_conn() as conn:
		df = pd.read_sql_query(
			"SELECT date, open, high, low, close, volume FROM price_bars WHERE ticker=? ORDER BY date ASC",
			conn,
			params=(ticker,),
		)
		df["date"] = pd.to_datetime(df["date"])  # type: ignore
		return df


def analyze_ticker(ticker: str) -> Dict[str, Any]:
	df = load_df_for(ticker)
	if df.empty or len(df) < 200:
		return {"ticker": ticker, "error": "Not enough data"}
	ind = compute_indicators(df)
	# use selector to decide which strategy is best recently
	best = select_best_strategy({"bias": 1.0}, df)
	strategy_key = None
	if best is not None:
		name = best.strategy_name
		strategy_key = {
			"EMATrend": "ema_trend",
			"SMACrossover": "sma_cross",
			"RSIMeanReversion": "rsi_mean",
			"DonchianBreakout": "donchian",
			"MACDTrend": "macd_trend",
		}.get(name, None)
	if strategy_key is None:
		strategy_key = "sma_cross"
	action, reason, snapshot, confidence = recommend_action(strategy_key, ind)
	return {
		"ticker": ticker,
		"strategy": strategy_key,
		"action": action,
		"reason": reason,
		"confidence": confidence,
		"snapshot": snapshot,
	}