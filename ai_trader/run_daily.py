from datetime import datetime
import pandas as pd
from .config import CONFIG
from .storage import init_db, get_conn, upsert_decision
from .data_collect import collect_prices, collect_global_indices, collect_sentiment_from_texts, collect_sentiment_from_pdf
from .news import collect_perplexity_news
from .selector import select_best_strategy
from .execution import notify_signal
from .planner import generate_daily_plans, evaluate_open_plans


def load_ticker_df(ticker: str) -> pd.DataFrame:
	with get_conn() as conn:
		df = pd.read_sql_query(
			"SELECT date, open, high, low, close, volume FROM price_bars WHERE ticker=? ORDER BY date ASC",
			conn,
			params=(ticker,),
		)
		df["date"] = pd.to_datetime(df["date"])  # type: ignore
		return df


def featurize_market() -> dict:
	# Placeholder features
	return {"bias": 1.0}


def main() -> None:
	init_db()
	# Collect for both default_tickers (UI suggestions) and planner_tickers (universe)
	universe = list(dict.fromkeys((CONFIG.planner_tickers or []) + (CONFIG.default_tickers or []))) or (CONFIG.default_tickers or [])
	collect_prices(universe, days=365)
	collect_global_indices(days=7)
	collect_sentiment_from_texts([
		"Markets rally as inflation cools",
		"Investors cautious amid global uncertainty",
	])
	# Optional: Perplexity news -> sentiment
	collect_perplexity_news(topic="Indian stock market", count=10)
	# Example: if you have a PDF of a report/newsletter, ingest it too
	# collect_sentiment_from_pdf("/workspace/sample_report.pdf")

	asof = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
	features = featurize_market()

	for ticker in CONFIG.default_tickers:
		df = load_ticker_df(ticker)
		if df.empty or len(df) < 80:
			continue
		best = select_best_strategy(features, df, ticker=ticker, asof=asof)
		if best is None:
			continue
		action = "BUY" if best.return_pct >= 0 else "SELL"
		entry = float(df["close"].iloc[-1])
		stop = None
		target = None
		upsert_decision(asof, ticker, best.strategy_name, action, entry, stop, target, meta=None)
		notify_signal(ticker, best.strategy_name, action, entry, stop, target)

	# --- Planner: generate new plans and evaluate open ones ---
	generate_daily_plans(CONFIG.planner_tickers or CONFIG.default_tickers)
	evaluate_open_plans()


if __name__ == "__main__":
	main()