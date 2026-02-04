from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .adapter_polymarket import PolymarketAdapter
from .db import BotDB
from .market_discovery import MarketInfo
from .risk import RiskLimits, add_daily_notional, check_daily_limit, check_trade_limits
from .scanner import Opportunity


@dataclass
class ExecutionResult:
    success: bool
    message: str


def execute_opportunity(
    adapter: PolymarketAdapter,
    db: BotDB,
    opportunity: Opportunity,
    limits: RiskLimits,
    run_id: int,
    max_slippage_live_bps: float,
) -> ExecutionResult:
    notional = opportunity.yes.price + opportunity.no.price
    if not check_trade_limits(notional, 0, limits):
        return ExecutionResult(False, "risk limits exceeded")
    if not check_daily_limit(db, notional, limits):
        return ExecutionResult(False, "daily notional exceeded")

    yes_order = adapter.place_limit_buy(opportunity.market.yes_token_id, opportunity.yes.price, limits.min_order_size)
    no_order = adapter.place_limit_buy(opportunity.market.no_token_id, opportunity.no.price, limits.min_order_size)

    db.insert(
        "orders",
        {
            "run_id": run_id,
            "market_id": opportunity.market.market_id,
            "token_id": opportunity.market.yes_token_id,
            "side": "BUY",
            "price": opportunity.yes.price,
            "size": limits.min_order_size,
            "status": yes_order.status,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    db.insert(
        "orders",
        {
            "run_id": run_id,
            "market_id": opportunity.market.market_id,
            "token_id": opportunity.market.no_token_id,
            "side": "BUY",
            "price": opportunity.no.price,
            "size": limits.min_order_size,
            "status": no_order.status,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )

    time.sleep(1)
    yes_status = adapter.get_order_status(yes_order.order_id)
    no_status = adapter.get_order_status(no_order.order_id)

    yes_filled = _is_filled(yes_status)
    no_filled = _is_filled(no_status)

    if yes_filled and no_filled:
        add_daily_notional(db, notional)
        return ExecutionResult(True, "both legs filled")

    if yes_filled != no_filled:
        unfilled_order_id = no_order.order_id if yes_filled else yes_order.order_id
        adapter.cancel(unfilled_order_id)
        db.insert(
            "imbalances",
            {
                "run_id": run_id,
                "market_id": opportunity.market.market_id,
                "yes_token_id": opportunity.market.yes_token_id,
                "no_token_id": opportunity.market.no_token_id,
                "note": "partial fill - canceled remaining leg",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
        return ExecutionResult(False, "partial fill; imbalance recorded")

    max_slippage = max_slippage_live_bps / 10000
    retry_yes_price = opportunity.yes.price * (1 + max_slippage)
    retry_no_price = opportunity.no.price * (1 + max_slippage)
    adapter.place_limit_buy(opportunity.market.yes_token_id, retry_yes_price, limits.min_order_size)
    adapter.place_limit_buy(opportunity.market.no_token_id, retry_no_price, limits.min_order_size)
    db.insert(
        "imbalances",
        {
            "run_id": run_id,
            "market_id": opportunity.market.market_id,
            "yes_token_id": opportunity.market.yes_token_id,
            "no_token_id": opportunity.market.no_token_id,
            "note": "no fills - retried with slippage",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )
    return ExecutionResult(False, "no fills; retried with slippage")


def _is_filled(status_payload: Optional[object]) -> bool:
    if status_payload is None:
        return False
    if isinstance(status_payload, dict):
        status = str(status_payload.get("status") or status_payload.get("state") or "").lower()
        return status in {"filled", "complete", "completed"}
    return False
