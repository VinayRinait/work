from __future__ import annotations
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
	data = df.copy()
	if "date" in data.columns:
		data["date"] = pd.to_datetime(data["date"])  # type: ignore
		data = data.set_index("date")
	close = data["close"].astype(float)
	data["sma_20"] = close.rolling(20).mean()
	data["sma_50"] = close.rolling(50).mean()
	data["sma_200"] = close.rolling(200).mean()
	# MACD
	ema12 = close.ewm(span=12, adjust=False).mean()
	ema26 = close.ewm(span=26, adjust=False).mean()
	data["macd"] = ema12 - ema26
	data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()
	# RSI
	delta = close.diff()
	gain = (delta.where(delta > 0, 0.0)).rolling(14).mean()
	loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
	rs = gain / (loss.replace(0, np.nan))
	data["rsi"] = 100 - (100 / (1 + rs))
	# Donchian breakout levels
	data["donchian_high_20"] = data["high"].rolling(20).max()
	data["donchian_low_20"] = data["low"].rolling(20).min()
	return data


def recommend_action(strategy_key: str, data: pd.DataFrame) -> Tuple[str, str, Dict[str, Any], float]:
	latest = data.dropna().iloc[-1]
	close = float(latest["close"])
	sma200 = float(latest.get("sma_200", np.nan))
	rsi = float(latest.get("rsi", np.nan))
	macd = float(latest.get("macd", np.nan))
	macd_sig = float(latest.get("macd_signal", np.nan))
	break_high = float(latest.get("donchian_high_20", np.nan))
	break_low = float(latest.get("donchian_low_20", np.nan))
	action = "HOLD"
	reason = []
	confidence = 50.0

	is_uptrend = not np.isnan(sma200) and close > sma200
	if is_uptrend:
		confidence += 10
	else:
		confidence -= 10

	if strategy_key in {"ema_trend", "sma_cross", "macd_trend"}:
		if is_uptrend and macd > macd_sig:
			action = "BUY"
			reason.append("Uptrend (close > SMA200) and MACD > Signal")
			confidence += 10
		elif (not is_uptrend) and macd < macd_sig:
			action = "SELL"
			reason.append("Downtrend (close < SMA200) and MACD < Signal")
			confidence += 5
		else:
			action = "HOLD"
			reason.append("Trend/oscillator not aligned")
	elif strategy_key == "donchian":
		if is_uptrend and close >= break_high:
			action = "BUY"
			reason.append("Breakout above 20-day high in uptrend")
			confidence += 10
		elif (not is_uptrend) and close <= break_low:
			action = "SELL"
			reason.append("Breakdown below 20-day low in downtrend")
			confidence += 5
		else:
			action = "HOLD"
			reason.append("No valid breakout setup")
	elif strategy_key == "rsi_mean":
		if is_uptrend and rsi < 35:
			action = "BUY"
			reason.append("Mean reversion: RSI oversold in uptrend")
			confidence += 10
		elif (not is_uptrend) and rsi > 65:
			action = "SELL"
			reason.append("Mean reversion: RSI overbought in downtrend")
			confidence += 5
		else:
			action = "HOLD"
			reason.append("RSI not at extreme levels")

	# Bound confidence
	confidence = max(0.0, min(95.0, confidence))
	return action, "; ".join(reasons := reason) if reason else "", {
		"close": close,
		"sma_200": sma200,
		"rsi": rsi,
		"macd": macd,
		"macd_signal": macd_sig,
		"donchian_high_20": break_high,
		"donchian_low_20": break_low,
	}, confidence