from typing import Optional
from .config import CONFIG


def place_order_dhan(ticker: str, side: str, qty: int, price: Optional[float] = None) -> str:
	# TODO: integrate with Dhan API
	mode = CONFIG.trading_mode
	return f"{mode}-order:{ticker}:{side}:{qty}@{price if price is not None else 'mkt'}"


def notify_signal(ticker: str, strategy: str, action: str, entry: float, stop: Optional[float], target: Optional[float]) -> None:
	print(f"Signal {ticker} | {strategy} | {action} | entry={entry} stop={stop} target={target}")