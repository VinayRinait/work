from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Tuple


def apply_triple_barrier(
	close: pd.Series,
	horizon: int = 10,
	pt_mult: float = 2.0,
	sl_mult: float = 1.0,
	vol: pd.Series | None = None,
) -> pd.DataFrame:
	"""
	Compute triple-barrier labels for each time t:
	- Upper barrier: entry * (1 + pt_mult * vol_t)
	- Lower barrier: entry * (1 - sl_mult * vol_t)
	- Time barrier: t + horizon
	Labels: +1 if upper hit first; -1 if lower hit first; 0 if neither by horizon.
	"""
	data = pd.DataFrame({"close": close})
	if vol is None:
		vol = close.pct_change().rolling(20).std().fillna(method="bfill").fillna(0.01)
	data["vol"] = vol
	pt = (1 + pt_mult * data["vol"]).values
	sl = (1 - sl_mult * data["vol"]).values
	labels = np.zeros(len(data), dtype=int)
	ttm = np.full(len(data), horizon, dtype=int)
	for i in range(len(data)):
		entry = data["close"].iat[i]
		if np.isnan(entry):
			continue
		ub = entry * pt[i]
		lb = entry * sl[i]
		end = min(len(data) - 1, i + horizon)
		path = data["close"].iloc[i + 1 : end + 1].values
		if path.size == 0:
			continue
		hit_upper = np.argmax(path >= ub)
		hit_lower = np.argmax(path <= lb)
		upper_hit = path[hit_upper] >= ub if hit_upper != 0 or path[0] >= ub else False
		lower_hit = path[hit_lower] <= lb if hit_lower != 0 or path[0] <= lb else False
		if upper_hit and lower_hit:
			labels[i] = 1 if hit_upper < hit_lower else -1
			ttm[i] = min(hit_upper, hit_lower) + 1
		elif upper_hit:
			labels[i] = 1
			ttm[i] = hit_upper + 1
		elif lower_hit:
			labels[i] = -1
			ttm[i] = hit_lower + 1
		else:
			labels[i] = 0
			ttm[i] = end - i
	return pd.DataFrame({"label": labels, "ttm": ttm}, index=data.index)