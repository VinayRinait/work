import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv


load_dotenv()


def _get_list(env_name: str, default: str) -> List[str]:
    value = os.getenv(env_name, default)
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Config:
    trading_mode: str = os.getenv("TRADING_MODE", "paper").lower()
    db_path: str = os.getenv("DB_PATH", "/workspace/trader.db")
    default_tickers: List[str] | None = None
    perplexity_api_key: str | None = os.getenv("PERPLEXITY_API_KEY")

    dhan_api_key: str | None = os.getenv("DHAN_API_KEY")
    dhan_access_token: str | None = os.getenv("DHAN_ACCESS_TOKEN")
    dhan_base_url: str = os.getenv("DHAN_BASE_URL", "https://api.dhan.co")

    data_providers: List[str] | None = None
    enable_execution: bool = os.getenv("ENABLE_EXECUTION", "false").lower() in {"1", "true", "yes", "y"}

    backtest_cash: float = float(os.getenv("BACKTEST_CASH", "100000"))
    backtest_commission: float = float(os.getenv("BACKTEST_COMMISSION", "0.0005"))
    backtest_window_days: int = int(os.getenv("BACKTEST_WINDOW_DAYS", "240"))
    sentiment_lookback_days: int = int(os.getenv("SENTIMENT_LOOKBACK_DAYS", "2"))

    # Planner
    planner_horizons: List[str] | None = None  # e.g., ["1D", "3D", "5D", "1M"]
    planner_tickers: List[str] | None = None  # up to ~50 tickers for planner universe

    def __post_init__(self):
        self.default_tickers = _get_list(
            "DEFAULT_TICKERS", "RELIANCE.NS,TCS.NS,HDFCBANK.NS"
        )
        self.data_providers = [p.upper() for p in _get_list("DATA_PROVIDERS", "YFINANCE")]
        self.planner_horizons = _get_list("PLANNER_HORIZONS", "1D,3D,5D,1M")
        self.planner_tickers = _get_list(
            "PLANNER_TICKERS",
            ",".join([
                "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS",
                "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","BAJFINANCE.NS",
                "KOTAKBANK.NS","LT.NS","HCLTECH.NS","ASIANPAINT.NS","AXISBANK.NS",
                "MARUTI.NS","SUNPHARMA.NS","NESTLEIND.NS","TITAN.NS","ULTRACEMCO.NS",
                "TATAMOTORS.NS","TATASTEEL.NS","WIPRO.NS","M&M.NS","HDFCLIFE.NS",
                "ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","POWERGRID.NS","TECHM.NS",
                "GRASIM.NS","TATACONSUM.NS","COALINDIA.NS","JSWSTEEL.NS","HINDALCO.NS",
                "ONGC.NS","NTPC.NS","BPCL.NS","IOC.NS","BRITANNIA.NS",
                "CIPLA.NS","DRREDDY.NS","DIVISLAB.NS","EICHERMOT.NS","HEROMOTOCO.NS",
                "BAJAJ-AUTO.NS","TATAPOWER.NS","UPL.NS","SHREECEM.NS","INDUSINDBK.NS",
            ])
        )


CONFIG = Config()