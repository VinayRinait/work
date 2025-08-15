from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, Any
from ..storage import get_conn


def build_features(ticker: str) -> pd.DataFrame:
	with get_conn() as conn:
		px = pd.read_sql_query(
			"SELECT date, open, high, low, close, volume FROM price_bars WHERE ticker=? ORDER BY date ASC",
			conn,
			params=(ticker,),
		)
		px["date"] = pd.to_datetime(px["date"])  # type: ignore
		px = px.set_index("date").astype(float)
	# technicals
	px["ret_1"] = px["close"].pct_change()
	px["ret_5"] = px["close"].pct_change(5)
	px["vol_20"] = px["ret_1"].rolling(20).std()
	px["sma_20"] = px["close"].rolling(20).mean()
	px["sma_50"] = px["close"].rolling(50).mean()
	px["sma_200"] = px["close"].rolling(200).mean()
	px["sma_20_slope"] = px["sma_20"].diff()
	px["donchian_hi"] = px["high"].rolling(20).max()
	px["donchian_lo"] = px["low"].rolling(20).min()
	# RSI
	delta = px["close"].diff()
	gain = delta.clip(lower=0).rolling(14).mean()
	loss = (-delta.clip(upper=0)).rolling(14).mean()
	rs = gain / (loss.replace(0, np.nan))
	px["rsi"] = 100 - (100 / (1 + rs))
	# sentiment (recent avg)
	px["sentiment"] = px.index.to_series().map(lambda d: recent_sentiment(d))
	# macro snapshot
	macro = recent_globals()
	px["usd_inr"] = macro.get("usdinr", np.nan)
	px["crude"] = macro.get("cl", np.nan)
	# dropna later in pipeline
	return px


def recent_sentiment(asof_ts: pd.Timestamp) -> float:
	try:
		with get_conn() as conn:
			asof = asof_ts.strftime("%Y-%m-%d %H:%M:%S")
			df = pd.read_sql_query(
				"SELECT AVG(score) AS s FROM sentiment WHERE asof >= datetime(?, '-2 day')",
				conn,
				params=(asof,),
			)
			val = df["s"].iloc[0]
			return float(val) if val is not None else np.nan
	except Exception:
		return np.nan


def recent_globals() -> Dict[str, Any]:
	try:
		with get_conn() as conn:
			df = pd.read_sql_query(
				"SELECT asof, dji, usdinr, cl FROM global_indices ORDER BY asof DESC LIMIT 1",
				conn,
			)
			if df.empty:
				return {}
			row = df.iloc[0].to_dict()
			return {"dji": row.get("dji"), "usdinr": row.get("usdinr"), "cl": row.get("cl")}
	except Exception:
		return {}