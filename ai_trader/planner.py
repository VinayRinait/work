from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Tuple
import pandas as pd
from .config import CONFIG
from .storage import get_conn, insert_trade_plan, update_trade_plan_status, fetch_trade_plans
from .services import analyze_ticker


@dataclass
class Levels:
    entry: float
    stop: float
    target: float
    rr: float


def _parse_horizon_days(h: str) -> int:
    h = (h or "").upper().strip()
    if h.endswith("D"):
        return int(h[:-1] or "1")
    if h.endswith("W"):
        return int(h[:-1] or "1") * 5
    if h.endswith("M"):
        return int(h[:-1] or "1") * 20
    return 5


def _level_factors(days: int) -> Tuple[float, float]:
    # (tp%, sl%) for BUY; for SELL reverse direction
    if days <= 1:
        return 0.02, 0.01
    if days <= 3:
        return 0.04, 0.02
    if days <= 5:
        return 0.06, 0.03
    return 0.10, 0.05


def _compute_levels(action: str, entry: float, horizon_days: int) -> Levels:
    tp_pct, sl_pct = _level_factors(horizon_days)
    if action == "BUY":
        target = entry * (1 + tp_pct)
        stop = entry * (1 - sl_pct)
    else:  # SELL
        target = entry * (1 - tp_pct)
        stop = entry * (1 + sl_pct)
    rr = abs((target - entry) / (entry - stop)) if (entry - stop) != 0 else 0.0
    return Levels(entry=entry, stop=float(stop), target=float(target), rr=float(rr))


def _latest_price_row(ticker: str) -> Tuple[str, float]:
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT date, close FROM price_bars WHERE ticker=? ORDER BY date DESC LIMIT 1",
            conn,
            params=(ticker,),
        )
        if df.empty:
            now = datetime.utcnow().strftime("%Y-%m-%d")
            return now, float("nan")
        row = df.iloc[0]
        return str(row["date"]), float(row["close"])


def _avg_sentiment() -> float | None:
    with get_conn() as conn:
        row = pd.read_sql_query(
            "SELECT AVG(score) AS s FROM sentiment WHERE asof >= datetime('now', ?)",
            conn,
            params=(f"-{CONFIG.sentiment_lookback_days} day",),
        )
        val = row["s"].iloc[0] if not row.empty else None
        return float(val) if val is not None else None


def generate_daily_plans(tickers: List[str]) -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    horizons = CONFIG.planner_horizons or ["3D", "5D"]
    for t in tickers:
        analysis = analyze_ticker(t)
        if "error" in analysis or analysis.get("action") == "HOLD":
            continue
        action = str(analysis["action"]).upper()
        strategy = analysis.get("strategy") or ""
        reason = analysis.get("reason") or ""
        confidence = float(analysis.get("confidence") or 0.0)
        snapshot = analysis.get("snapshot") or {}
        entry_date, entry = _latest_price_row(analysis["ticker"])
        if not entry or pd.isna(entry):
            continue
        sent = _avg_sentiment()
        for h in horizons:
            days = _parse_horizon_days(h)
            levels = _compute_levels(action, entry, days)
            rationale = {
                "strategy": strategy,
                "reason": reason,
                "confidence": confidence,
                "snapshot": snapshot,
                "sentiment": sent,
                "horizon_days": days,
            }
            insert_trade_plan(
                created_at=now,
                ticker=analysis["ticker"],
                horizon=h,
                entry_date=entry_date,
                entry=levels.entry,
                stop=levels.stop,
                target=levels.target,
                status="PLANNED",
                strategy=strategy,
                action=action,
                reason=reason,
                confidence=confidence,
                sentiment=sent,
                rationale=json.dumps(rationale),
                risk_reward=levels.rr,
            )


def _path_since(ticker: str, start_date: str) -> pd.DataFrame:
    with get_conn() as conn:
        df = pd.read_sql_query(
            """
            SELECT date, open, high, low, close FROM price_bars
            WHERE ticker=? AND date >= ?
            ORDER BY date ASC
            """,
            conn,
            params=(ticker, start_date),
        )
        df["date"] = pd.to_datetime(df["date"])  # type: ignore
        return df


def _evaluate_plan_row(plan: Dict[str, Any]) -> Tuple[str | None, str | None, float | None, int | None]:
    """
    Returns (new_status, outcome, pnl_pct, ttm_days) if terminal; otherwise (None, None, None, None)
    """
    action = (plan.get("action") or "BUY").upper()
    entry = float(plan["entry"])
    stop = float(plan["stop"])
    target = float(plan["target"])
    h = _parse_horizon_days(str(plan["horizon"] or "5D"))
    path = _path_since(plan["ticker"], plan["entry_date"])
    if path.empty:
        return None, None, None, None
    start_idx = 1 if len(path) > 1 else 0  # next bar after entry
    sub = path.iloc[start_idx:]
    # iterate bars to find first hit
    for i, row in enumerate(sub.itertuples(index=False), start=1):
        hi = float(row.high)
        lo = float(row.low)
        cl = float(row.close)
        # BUY: TP if high>=target, SL if low<=stop
        # SELL: TP if low<=target, SL if high>=stop
        if action == "BUY":
            if hi >= target:
                pnl = (target - entry) / entry * 100.0
                return "HIT_TP", "HIT_TP", pnl, i
            if lo <= stop:
                pnl = (stop - entry) / entry * 100.0
                return "HIT_SL", "HIT_SL", pnl, i
        else:  # SELL
            if lo <= target:
                pnl = (entry - target) / entry * 100.0
                return "HIT_TP", "HIT_TP", pnl, i
            if hi >= stop:
                pnl = (entry - stop) / entry * 100.0
                return "HIT_SL", "HIT_SL", pnl, i
        # time barrier
        if i >= h:
            # expire with mark-to-market pnl
            mtm = (cl - entry) / entry * 100.0
            mtm = -mtm if action == "SELL" else mtm
            return "EXPIRED", "EXPIRED", mtm, i
    return None, None, None, None


def evaluate_open_plans() -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    plans = fetch_trade_plans(limit=1000)
    for p in plans:
        if str(p.get("status")) not in {"PLANNED", "ACTIVE"}:
            continue
        new_status, outcome, pnl_pct, ttm = _evaluate_plan_row(p)
        if new_status:
            update_trade_plan_status(
                plan_id=int(p["id"]),
                status=new_status,
                closed_at=now,
                outcome=outcome,
                pnl_pct=pnl_pct,
                ttm_days=ttm,
            )
        else:
            # mark PLANNED -> ACTIVE after first evaluation pass
            if str(p.get("status")) == "PLANNED":
                update_trade_plan_status(plan_id=int(p["id"]), status="ACTIVE")

