from __future__ import annotations
from typing import Dict, Any, Tuple, List
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
	# Donchian
	data["donchian_high_20"] = data["high"].rolling(20).max()
	data["donchian_low_20"] = data["low"].rolling(20).min()
	# Resistance breakout (recent swing highs)
	data["resistance_20"] = data["high"].rolling(20).max()
	data["breakout"] = (data["close"] > data["resistance_20"]).astype(int)
	# Candle patterns
	patt = detect_candle_patterns(data)
	for k, v in patt.items():
		data[k] = v
	return data


def detect_candle_patterns(data: pd.DataFrame) -> Dict[str, pd.Series]:
	open_ = data.get("open", pd.Series(index=data.index, dtype=float)).astype(float)
	high = data.get("high", pd.Series(index=data.index, dtype=float)).astype(float)
	low = data.get("low", pd.Series(index=data.index, dtype=float)).astype(float)
	close = data.get("close", pd.Series(index=data.index, dtype=float)).astype(float)
	body = (close - open_)
	rng = (high - low).replace(0, np.nan)
	upper_shadow = (high - close).where(body >= 0, high - open_)
	lower_shadow = (open_ - low).where(body >= 0, close - low)
	# Hammer: small body, long lower shadow
	hammer = ((body.abs() <= 0.3 * rng) & (lower_shadow >= 2 * body.abs())).astype(int)
	# Engulfing: bullish if today's body engulfs yesterday's and is positive
	prev_open = open_.shift(1)
	prev_close = close.shift(1)
	bull_engulf = ((close > open_) & (prev_close < prev_open) & (close >= prev_open) & (open_ <= prev_close)).astype(int)
	bear_engulf = ((close < open_) & (prev_close > prev_open) & (close <= prev_open) & (open_ >= prev_close)).astype(int)
	return {"pat_hammer": hammer.fillna(0), "pat_bull_engulf": bull_engulf.fillna(0), "pat_bear_engulf": bear_engulf.fillna(0)}


def recommend_action(strategy_key: str, data: pd.DataFrame) -> Tuple[str, str, Dict[str, Any], float]:
	latest = data.dropna().iloc[-1]
	close = float(latest["close"])
	sma200 = float(latest.get("sma_200", np.nan))
	rsi = float(latest.get("rsi", np.nan))
	macd = float(latest.get("macd", np.nan))
	macd_sig = float(latest.get("macd_signal", np.nan))
	break_high = float(latest.get("donchian_high_20", np.nan))
	breakout = int(latest.get("breakout", 0))
	pat_hammer = int(latest.get("pat_hammer", 0))
	pat_bull = int(latest.get("pat_bull_engulf", 0))
	pat_bear = int(latest.get("pat_bear_engulf", 0))
	action = "HOLD"
	reason: List[str] = []
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
		if is_uptrend and (close >= break_high or breakout == 1):
			action = "BUY"
			reason.append("Resistance breakout in uptrend")
			confidence += 12
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

	# Candles boost
	if action == "BUY" and (pat_hammer == 1 or pat_bull == 1):
		reason.append("Bullish candle pattern (hammer/engulfing)")
		confidence += 5
	if action == "SELL" and pat_bear == 1:
		reason.append("Bearish engulfing pattern")
		confidence += 5

	confidence = max(0.0, min(95.0, confidence))
	return action, "; ".join(reasons := reason) if reason else "", {
		"close": close,
		"sma_200": sma200,
		"rsi": rsi,
		"macd": macd,
		"macd_signal": macd_sig,
		"donchian_high_20": break_high,
		"breakout": breakout,
		"pat_hammer": pat_hammer,
		"pat_bull_engulf": pat_bull,
		"pat_bear_engulf": pat_bear,
	}, confidence