import sqlite3
from contextlib import contextmanager
from typing import Iterable, Tuple, Any
from .config import CONFIG


@contextmanager
def get_conn():
	conn = sqlite3.connect(CONFIG.db_path)
	try:
		yield conn
	finally:
		conn.commit()
		conn.close()


def init_db() -> None:
	with get_conn() as conn:
		c = conn.cursor()
		c.execute(
			"""
			CREATE TABLE IF NOT EXISTS price_bars (
				ticker TEXT,
				date TEXT,
				open REAL,
				high REAL,
				low REAL,
				close REAL,
				volume REAL,
				PRIMARY KEY (ticker, date)
			)
			"""
		)
		c.execute(
			"""
			CREATE TABLE IF NOT EXISTS sentiment (
				asof TEXT PRIMARY KEY,
				headline TEXT,
				score REAL,
				source TEXT
			)
			"""
		)
		c.execute(
			"""
			CREATE TABLE IF NOT EXISTS global_indices (
				asof TEXT PRIMARY KEY,
				dji REAL,
				usdinr REAL,
				cl REAL
			)
			"""
		)
		c.execute(
			"""
			CREATE TABLE IF NOT EXISTS decisions (
				asof TEXT,
				ticker TEXT,
				strategy TEXT,
				action TEXT,
				entry REAL,
				stop REAL,
				target REAL,
				meta TEXT,
				PRIMARY KEY (asof, ticker)
			)
			"""
		)
		c.execute(
			"""
			CREATE TABLE IF NOT EXISTS strategy_evals (
				asof TEXT,
				ticker TEXT,
				strategy TEXT,
				return_pct REAL,
				win_rate REAL,
				PRIMARY KEY (asof, ticker, strategy)
			)
			"""
		)


def upsert_price_bars(rows: Iterable[Tuple[Any, ...]]) -> None:
	with get_conn() as conn:
		conn.executemany(
			"""
			INSERT INTO price_bars (ticker, date, open, high, low, close, volume)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			ON CONFLICT(ticker, date) DO UPDATE SET
				open=excluded.open,
				high=excluded.high,
				low=excluded.low,
				close=excluded.close,
				volume=excluded.volume
			""",
			list(rows),
		)


def upsert_sentiment(rows: Iterable[Tuple[Any, ...]]) -> None:
	with get_conn() as conn:
		conn.executemany(
			"""
			INSERT INTO sentiment (asof, headline, score, source)
			VALUES (?, ?, ?, ?)
			ON CONFLICT(asof) DO UPDATE SET
				headline=excluded.headline,
				score=excluded.score,
				source=excluded.source
			""",
			list(rows),
		)


def upsert_global(asof: str, dji: float, usdinr: float, cl: float) -> None:
	with get_conn() as conn:
		conn.execute(
			"""
			INSERT INTO global_indices (asof, dji, usdinr, cl)
			VALUES (?, ?, ?, ?)
			ON CONFLICT(asof) DO UPDATE SET
				dji=excluded.dji,
				usdinr=excluded.usdinr,
				cl=excluded.cl
			""",
			(asof, dji, usdinr, cl),
		)


def upsert_decision(asof: str, ticker: str, strategy: str, action: str, entry: float, stop: float | None, target: float | None, meta: str | None) -> None:
	with get_conn() as conn:
		conn.execute(
			"""
			INSERT INTO decisions (asof, ticker, strategy, action, entry, stop, target, meta)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			ON CONFLICT(asof, ticker) DO UPDATE SET
				strategy=excluded.strategy,
				action=excluded.action,
				entry=excluded.entry,
				stop=excluded.stop,
				target=excluded.target,
				meta=excluded.meta
			""",
			(asof, ticker, strategy, action, entry, stop, target, meta),
		)


def upsert_strategy_evals(rows: Iterable[Tuple[Any, ...]]) -> None:
	with get_conn() as conn:
		conn.executemany(
			"""
			INSERT INTO strategy_evals (asof, ticker, strategy, return_pct, win_rate)
			VALUES (?, ?, ?, ?, ?)
			ON CONFLICT(asof, ticker, strategy) DO UPDATE SET
				return_pct=excluded.return_pct,
				win_rate=excluded.win_rate
			""",
			list(rows),
		)