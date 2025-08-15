from __future__ import annotations
from typing import Optional, Dict, Any, List
import requests
from .config import CONFIG


class DhanClient:
	def __init__(self, access_token: Optional[str] = None, base_url: Optional[str] = None) -> None:
		self.access_token = access_token or CONFIG.dhan_access_token
		self.base_url = (base_url or CONFIG.dhan_base_url).rstrip("/")
		self.session = requests.Session()
		self.session.headers.update({
			"access-token": self.access_token or "",
			"Content-Type": "application/json",
		})

	def _fmt_symbol(self, yf_symbol: str) -> Optional[str]:
		# Map Yahoo symbol like RELIANCE.NS -> NSE:RELIANCE
		if not yf_symbol:
			return None
		sym = yf_symbol.upper()
		if sym.endswith(".NS"):
			return f"NSE:{sym[:-3]}"
		return f"NSE:{sym}"

	def get_quote(self, yf_symbol: str) -> Optional[Dict[str, Any]]:
		if not self.access_token:
			return None
		symbol = self._fmt_symbol(yf_symbol)
		if not symbol:
			return None
		url = f"{self.base_url}/v2/market/quotes"
		try:
			resp = self.session.post(url, json={"symbols": [symbol]}, timeout=8)
			resp.raise_for_status()
			data = resp.json()
			if isinstance(data, dict) and data.get("data"):
				quotes = data["data"]
				return quotes[0] if quotes else None
			return None
		except Exception:
			return None

	def get_quotes(self, yf_symbols: List[str]) -> List[Dict[str, Any]]:
		if not self.access_token:
			return []
		symbols = [self._fmt_symbol(s) for s in yf_symbols if s]
		symbols = [s for s in symbols if s]
		if not symbols:
			return []
		url = f"{self.base_url}/v2/market/quotes"
		try:
			resp = self.session.post(url, json={"symbols": symbols}, timeout=8)
			resp.raise_for_status()
			data = resp.json()
			return data.get("data", []) if isinstance(data, dict) else []
		except Exception:
			return []