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

    backtest_cash: float = float(os.getenv("BACKTEST_CASH", "100000"))
    backtest_commission: float = float(os.getenv("BACKTEST_COMMISSION", "0.0005"))
    backtest_window_days: int = int(os.getenv("BACKTEST_WINDOW_DAYS", "240"))
    sentiment_lookback_days: int = int(os.getenv("SENTIMENT_LOOKBACK_DAYS", "2"))

    def __post_init__(self):
        self.default_tickers = _get_list(
            "DEFAULT_TICKERS", "RELIANCE.NS,TCS.NS,HDFCBANK.NS"
        )


CONFIG = Config()