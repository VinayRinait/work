from __future__ import annotations
from typing import List, Dict, Any
import os
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from .config import CONFIG
from .storage import upsert_sentiment


_analyzer = SentimentIntensityAnalyzer()


def fetch_perplexity_news(topic: str = "Indian stock market", count: int = 10, timeout: int = 15) -> List[str]:
	api_key = CONFIG.perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")
	if not api_key:
		return []
	url = "https://api.perplexity.ai/chat/completions"
	headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
	prompt = (
		f"Give {count} concise, up-to-date news headlines with sources about {topic}. "
		"Return each headline on a new line, prefix with a dash and include the source domain in parentheses."
	)
	payload: Dict[str, Any] = {
		"model": "sonar-small-online",
		"messages": [
			{"role": "system", "content": "You are a helpful assistant."},
			{"role": "user", "content": prompt},
		],
	}
	try:
		resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
		resp.raise_for_status()
		data = resp.json()
		content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
		lines = [l.strip(" -\t") for l in content.split("\n") if l.strip()]
		# Keep top count
		return lines[:count]
	except Exception:
		return []


def collect_perplexity_news(topic: str = "Indian stock market", count: int = 10) -> None:
	headlines = fetch_perplexity_news(topic, count)
	if not headlines:
		return
	from datetime import datetime
	asof = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
	rows = []
	for h in headlines:
		score = _analyzer.polarity_scores(h).get("compound", 0.0)
		rows.append((asof, h, score, "perplexity"))
	if rows:
		upsert_sentiment(rows)