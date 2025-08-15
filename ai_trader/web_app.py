from __future__ import annotations
from flask import Flask, render_template, send_from_directory
import sqlite3
from .config import CONFIG
import os


def get_db_conn():
	conn = sqlite3.connect(CONFIG.db_path)
	conn.row_factory = sqlite3.Row
	return conn


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def index():
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
	return render_template("index.html", decisions=decisions, evals=latest_evals)


@app.route("/static/<path:path>")
def static_proxy(path: str):
	return send_from_directory(os.path.join(os.path.dirname(__file__), "static"), path)


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=8000, debug=True)