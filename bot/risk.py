from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict

from .db import BotDB


@dataclass
class RiskLimits:
    max_notional_per_trade: float
    max_daily_notional: float
    max_open_orders: int
    min_order_size: float


def check_trade_limits(notional: float, open_orders: int, limits: RiskLimits) -> bool:
    if notional > limits.max_notional_per_trade:
        return False
    if open_orders >= limits.max_open_orders:
        return False
    return True


def get_daily_notional(db: BotDB) -> float:
    day = datetime.utcnow().strftime("%Y-%m-%d")
    row = db.fetch_one("SELECT notional FROM daily_notional WHERE day = ?", [day])
    if row:
        return float(row["notional"])
    return 0.0


def add_daily_notional(db: BotDB, amount: float) -> None:
    day = datetime.utcnow().strftime("%Y-%m-%d")
    current = get_daily_notional(db)
    if current == 0:
        db.insert("daily_notional", {"day": day, "notional": amount})
    else:
        db.execute("UPDATE daily_notional SET notional = ? WHERE day = ?", [current + amount, day])


def check_daily_limit(db: BotDB, amount: float, limits: RiskLimits) -> bool:
    return get_daily_notional(db) + amount <= limits.max_daily_notional
