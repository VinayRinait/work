from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pypdf import PdfReader
from .config import CONFIG
from .storage import upsert_price_bars, upsert_sentiment, upsert_global


_analyzer = SentimentIntensityAnalyzer()

def fetch_price_history(ticker: str, days: int = 365) -> pd.DataFrame:
	end = datetime.utcnow()
	start = end - timedelta(days=days)
	df = yf.download(ticker, start=start, end=end, interval="1d", progress=False)
	if df.empty:
		return df
	df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
	df.index = pd.to_datetime(df.index)
	df["date"] = df.index.date.astype(str)
	df["ticker"] = ticker
	return df[["ticker", "date", "open", "high", "low", "close", "volume"]]


def collect_prices(tickers: List[str], days: int = 365) -> None:
	rows = []
	for t in tickers:
		df = fetch_price_history(t, days)
		if not df.empty:
			rows.extend(df.itertuples(index=False, name=None))
	if rows:
		upsert_price_bars(rows)


def analyze_headlines(headlines: List[str]) -> List[Dict[str, Any]]:
	res = []
	asof = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
	for h in headlines:
		score = _analyzer.polarity_scores(h)["compound"]
		res.append({"asof": asof, "headline": h, "score": score, "source": "local"})
	return res


def collect_sentiment_from_texts(headlines: List[str]) -> None:
	items = analyze_headlines(headlines)
	rows = [(i["asof"], i["headline"], i["score"], i["source"]) for i in items]
	if rows:
		upsert_sentiment(rows)


def collect_global_indices(days: int = 7) -> None:
	end = datetime.utcnow()
	start = end - timedelta(days=days)
	series = {}
	for sym, key in [("^DJI", "dji"), ("INR=X", "usdinr"), ("CL=F", "cl")]:
		df = yf.download(sym, start=start, end=end, interval="1d", progress=False)
		if df.empty:
			continue
		series[key] = df["Close"].dropna()
	if not series:
		return
	asof = max(s.index.max() for s in series.values()).strftime("%Y-%m-%d")
	dji = float(series.get("dji", pd.Series(dtype=float)).tail(1).values[0]) if "dji" in series else 0.0
	usdinr = float(series.get("usdinr", pd.Series(dtype=float)).tail(1).values[0]) if "usdinr" in series else 0.0
	cl = float(series.get("cl", pd.Series(dtype=float)).tail(1).values[0]) if "cl" in series else 0.0
	upsert_global(asof, dji, usdinr, cl)


def extract_text_from_pdf(path: str, max_pages: int = 5) -> List[str]:
	try:
		reader = PdfReader(path)
		texts: List[str] = []
		for idx, page in enumerate(reader.pages[:max_pages]):
			content = page.extract_text() or ""
			chunks = [c.strip() for c in content.split("\n") if len(c.strip()) > 20]
			texts.extend(chunks[:50])
		return texts
	except Exception:
		return []


def collect_sentiment_from_pdf(path: str) -> None:
	texts = extract_text_from_pdf(path)
	if not texts:
		return
	collect_sentiment_from_texts(texts[:50])