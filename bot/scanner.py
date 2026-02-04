from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .market_discovery import MarketInfo


@dataclass
class OrderBookTop:
    price: float
    size: float


@dataclass
class Opportunity:
    market: MarketInfo
    yes: OrderBookTop
    no: OrderBookTop
    edge_bps: float
    all_in_cost: float


def _parse_top_ask(order_book: Dict[str, Any]) -> Optional[OrderBookTop]:
    asks = order_book.get("asks") or order_book.get("ask") or []
    if not asks:
        return None
    top = asks[0]
    if isinstance(top, dict):
        price = float(top.get("price") or top.get("p") or 0)
        size = float(top.get("size") or top.get("s") or 0)
    else:
        price, size = top
    if price <= 0 or size <= 0:
        return None
    return OrderBookTop(price=price, size=size)


def compute_edge_bps(
    yes_price: float,
    no_price: float,
    fee_bps: float,
    slippage_bps: float,
) -> float:
    cost = yes_price + no_price
    fees = cost * fee_bps / 10000
    slippage = cost * slippage_bps / 10000
    all_in = cost + fees + slippage
    edge = (1.0 - all_in) * 10000
    return edge


def scan_market(
    market: MarketInfo,
    yes_book: Dict[str, Any],
    no_book: Dict[str, Any],
    fee_bps: float,
    slippage_bps: float,
    min_order_size: float,
) -> Optional[Opportunity]:
    yes_top = _parse_top_ask(yes_book)
    no_top = _parse_top_ask(no_book)
    if yes_top is None or no_top is None:
        return None
    if yes_top.size < min_order_size or no_top.size < min_order_size:
        return None
    edge = compute_edge_bps(yes_top.price, no_top.price, fee_bps, slippage_bps)
    all_in = yes_top.price + no_top.price + (yes_top.price + no_top.price) * (fee_bps + slippage_bps) / 10000
    return Opportunity(market=market, yes=yes_top, no=no_top, edge_bps=edge, all_in_cost=all_in)
