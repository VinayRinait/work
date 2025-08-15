# AI-Powered Trading Assistant (India)

A modular swing-trading assistant for the Indian market. It:

- Collects end-of-day price data (free Yahoo Finance by default)
- Computes sentiment (VADER, with optional PDF/news ingestion)
- Backtests multiple strategies using `backtesting.py`
- Learns which strategy fits current market conditions
- Generates swing-trade suggestions and a dashboard to review signals

## Features
- Strategy pack: EMA Trend, SMA Crossover, RSI Mean Reversion, Donchian Breakout, MACD Trend
- Selector chooses best strategy based on recent performance
- Swing suggestion engine with SMA200 trend filter, RSI, MACD, Donchian
- Dashboard (Flask): home with suggestions, signals, recent evals; analyze page to search by ticker
- SQLite persistence for prices, sentiment, global indices, decisions, strategy evaluations

## Quickstart

1. Python 3.10+
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Create `.env` (see `.env.example`):
```ini
TRADING_MODE=paper
DB_PATH=/workspace/trader.db
DEFAULT_TICKERS=RELIANCE.NS,TCS.NS,HDFCBANK.NS
DATA_PROVIDERS=YFINANCE
ENABLE_EXECUTION=false
```
4. Populate data and generate signals
```bash
python3 -m ai_trader.run_daily
```
5. Start the dashboard
```bash
python3 -m ai_trader.web_app
```
Visit http://127.0.0.1:8000

## Analyze a ticker
Open http://127.0.0.1:8000/analyze?ticker=RELIANCE.NS to see:
- BUY/SELL/HOLD suggestion
- Strategy applied
- Confidence and reason
- Key indicators snapshot (close, SMA200, RSI, MACD)

## Configuration
- `DATA_PROVIDERS`: ordered list of providers (default `YFINANCE`). You can later add `DHAN` or other providers.
- `ENABLE_EXECUTION=false`: dashboard is read-only; no orders are placed.
- Global features fetched via Yahoo: `^DJI`, `INR=X`, `CL=F`.

## Notes & Safety
- Free sources may change or rate-limit; provider fallback is implemented.
- Past performance does not guarantee future results. For research only.
- Keep API keys secret. Rotate any keys shared publicly.

## Roadmap
- Add NSE/Breeze/EODHD providers
- Intraday intervals and live charts
- Model-based selector (meta-learning), position sizing & risk
- Portfolio view and PnL tracking