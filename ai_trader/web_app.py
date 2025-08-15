from __future__ import annotations
from flask import Flask, render_template, send_from_directory, request
import sqlite3
from .config import CONFIG
import os
from .services import analyze_ticker


def get_db_conn():
	conn = sqlite3.connect(CONFIG.db_path)
	conn.row_factory = sqlite3.Row
	return conn


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def index():
	suggestions = []
	recent_news = []
	insights = {
		"best_strategy": None,
		"action_mix": {},
		"avg_sentiment": None,
		"globals": None,
	}
	with get_db_conn() as conn:
		decisions = conn.execute(
			"""
			SELECT asof, ticker, strategy, action, entry, stop, target
			FROM decisions ORDER BY asof DESC LIMIT 50
			"""
		).fetchall()
		latest_evals = conn.execute(
			"""
			SELECT asof, ticker, strategy, return_pct, win_rate
			FROM strategy_evals
			ORDER BY asof DESC LIMIT 200
			"""
		).fetchall()
		recent_news = conn.execute(
			"""
			SELECT asof, headline, score, source FROM sentiment
			ORDER BY asof DESC LIMIT 15
			"""
		).fetchall()
		# Insights
		best = conn.execute(
			"""
			SELECT strategy, AVG(return_pct) avg_ret, AVG(win_rate) avg_wr
			FROM strategy_evals
			WHERE asof >= datetime('now','-30 day')
			GROUP BY strategy
			ORDER BY avg_ret DESC
			LIMIT 1
			"""
		).fetchone()
		if best:
			insights["best_strategy"] = {"strategy": best["strategy"], "avg_ret": best["avg_ret"], "avg_wr": best["avg_wr"]}
		actions = conn.execute(
			"""
			SELECT action, COUNT(*) cnt
			FROM decisions
			WHERE asof >= datetime('now','-7 day')
			GROUP BY action
			"""
		).fetchall()
		insights["action_mix"] = {row["action"]: row["cnt"] for row in actions}
		avg_sent = conn.execute(
			"""
			SELECT AVG(score) avg_score FROM sentiment
			WHERE asof >= datetime('now','-2 day')
			"""
		).fetchone()
		if avg_sent and avg_sent["avg_score"] is not None:
			insights["avg_sentiment"] = float(avg_sent["avg_score"])
		g = conn.execute(
			"""
			SELECT asof, dji, usdinr, cl FROM global_indices ORDER BY asof DESC LIMIT 1
			"""
		).fetchone()
		if g:
			insights["globals"] = {"asof": g["asof"], "dji": g["dji"], "usdinr": g["usdinr"], "cl": g["cl"]}
		for t in (CONFIG.default_tickers or [])[:5]:
			try:
				res = analyze_ticker(t)
				if "error" not in res:
					suggestions.append(res)
			except Exception:
				continue
	return render_template("index.html", decisions=decisions, evals=latest_evals, suggestions=suggestions, news=recent_news, insights=insights)


@app.route("/analyze")
def analyze():
	t = request.args.get("ticker", "").strip()
	res = None
	if t:
		try:
			res = analyze_ticker(t)
		except Exception as e:
			res = {"ticker": t, "error": str(e)}
	return render_template("analyze.html", result=res)


@app.route("/about")
def about():
	return render_template("about.html")


@app.route("/static/<path:path>")
def static_proxy(path: str):
	return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), path)


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8000, debug=True)