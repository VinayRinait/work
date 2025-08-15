from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from backtesting import Backtest
from .strategies import ALL_STRATEGIES
from .config import CONFIG
from .storage import upsert_strategy_evals


@dataclass
class StrategyResult:
	strategy_name: str
	return_pct: float
	win_rate: float


def _run_backtest(df: pd.DataFrame, strategy) -> StrategyResult:
	data = df.copy()
	if "date" in data.columns:
		data["date"] = pd.to_datetime(data["date"])  # type: ignore
		data = data.set_index("date")
	data = data.rename(columns={
		"open": "Open",
		"high": "High",
		"low": "Low",
		"close": "Close",
		"volume": "Volume",
	})
	bt = Backtest(
		data,
		strategy,
		cash=CONFIG.backtest_cash,
		commission=CONFIG.backtest_commission,
		trade_on_close=True,
		finalize_trades=True,
	)
	stats = bt.run()
	ret = float(stats.get("Return [%]", 0.0))
	wr = float(stats.get("Win Rate [%]", 0.0))
	return StrategyResult(strategy.__name__, ret, wr)


def evaluate_strategies(df: pd.DataFrame) -> List[StrategyResult]:
	results: List[StrategyResult] = []
	for name, strat in ALL_STRATEGIES.items():
		try:
			res = _run_backtest(df.tail(CONFIG.backtest_window_days), strat)
			results.append(res)
		except Exception:
			continue
	return results


def select_best_strategy(features: Dict[str, Any], df: pd.DataFrame, ticker: str | None = None, asof: str | None = None) -> StrategyResult | None:
	results = evaluate_strategies(df)
	if not results:
		return None
	results.sort(key=lambda r: (r.return_pct, r.win_rate), reverse=True)
	best = results[0]
	if ticker and asof:
		rows = [(asof, ticker, r.strategy_name, r.return_pct, r.win_rate) for r in results]
		upsert_strategy_evals(rows)
	return best