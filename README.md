# AI-Powered Trading Assistant (India)

This project is a modular trading assistant for the Indian market. It:

- Collects market and sentiment data
- Backtests multiple strategies using `backtesting.py`
- Learns which strategy to use given current conditions
- Generates trade signals and can execute via Dhan (stubbed)

## Quickstart

1. Create a Python 3.10+ environment
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the repo root:

```ini
TRADING_MODE=paper  # or live
DB_PATH=/workspace/trader.db
DEFAULT_TICKERS=RELIANCE.NS,TCS.NS,HDFCBANK.NS
DATA_PROVIDERS=YFINANCE
ENABLE_EXECUTION=false
DHAN_API_KEY=your_key_if_any
DHAN_ACCESS_TOKEN=your_access_token_if_any
DHAN_BASE_URL=https://api.dhan.co
PERPLEXITY_API_KEY=optional
```

4. Run a daily scan and signal generation:

```bash
python3 -m ai_trader.run_daily
```

## Notes
- Dhan execution is stubbed. Live trading requires implementing endpoints and credentials.
- News/sentiment uses VADER. Perplexity/other news APIs are optional.
- Global features: Dow Jones `^DJI`, USD/INR `INR=X`, Crude `CL=F` via Yahoo Finance.
- Data is persisted to SQLite at `DB_PATH`.