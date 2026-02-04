from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from .config import DiscoveryConfig


@dataclass
class MarketInfo:
    market_id: str
    question: str
    yes_token_id: str
    no_token_id: str
    volume: Optional[float]
    liquidity: Optional[float]
    category: Optional[str]


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _extract_tokens(market: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    yes_token_id = market.get("yes_token_id") or market.get("yesTokenId")
    no_token_id = market.get("no_token_id") or market.get("noTokenId")

    if yes_token_id and no_token_id:
        return str(yes_token_id), str(no_token_id)

    token_collections = []
    for key in ("tokens", "outcomes", "outcomeTokens", "outcome_tokens"):
        value = market.get(key)
        if isinstance(value, list):
            token_collections.append(value)

    for collection in token_collections:
        for token in collection:
            outcome = _normalize_text(token.get("outcome") or token.get("name") or token.get("title"))
            token_id = token.get("token_id") or token.get("tokenId") or token.get("id")
            if not token_id:
                continue
            if outcome in {"yes", "true"}:
                yes_token_id = str(token_id)
            if outcome in {"no", "false"}:
                no_token_id = str(token_id)

    return (str(yes_token_id) if yes_token_id else None, str(no_token_id) if no_token_id else None)


def _matches_filters(market: Dict[str, Any], config: DiscoveryConfig) -> bool:
    question = _normalize_text(market.get("question") or market.get("title") or market.get("name"))
    if config.include_keywords:
        if not any(keyword.lower() in question for keyword in config.include_keywords):
            return False
    if config.exclude_keywords:
        if any(keyword.lower() in question for keyword in config.exclude_keywords):
            return False
    category = _normalize_text(market.get("category") or market.get("categoryLabel"))
    if config.categories:
        if category not in {c.lower() for c in config.categories}:
            return False
    if config.only_active:
        active = market.get("active")
        if active is not None and active is not True:
            return False
    volume = market.get("volume") or market.get("volume_usd") or market.get("volumeUsd")
    if volume is not None:
        try:
            if float(volume) < config.min_volume_usd:
                return False
        except (TypeError, ValueError):
            pass
    liquidity = market.get("liquidity") or market.get("liquidity_usd") or market.get("liquidityUsd")
    if liquidity is not None:
        try:
            if float(liquidity) < config.min_liquidity:
                return False
        except (TypeError, ValueError):
            pass
    return True


def _parse_markets(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "markets", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def discover_markets(
    config: DiscoveryConfig,
    adapter: Optional[Any] = None,
    host: str = "https://clob.polymarket.com",
) -> List[MarketInfo]:
    markets: List[Dict[str, Any]] = []
    if adapter is not None:
        response = adapter.get_markets({"active": True, "limit": config.max_markets})
        if response is not None:
            markets = list(_parse_markets(response))

    if not markets:
        params = {"active": "true" if config.only_active else "false", "limit": config.max_markets}
        endpoints = [
            f"{host}/markets",
            f"{host}/markets/active",
        ]
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, params=params, timeout=10)
                response.raise_for_status()
                payload = response.json()
                markets = list(_parse_markets(payload))
                if markets:
                    break
            except requests.RequestException:
                continue

    results: List[MarketInfo] = []
    for market in markets:
        if not isinstance(market, dict):
            continue
        if not _matches_filters(market, config):
            continue
        yes_token_id, no_token_id = _extract_tokens(market)
        if not yes_token_id or not no_token_id:
            continue
        question = market.get("question") or market.get("title") or market.get("name") or ""
        volume = market.get("volume") or market.get("volume_usd") or market.get("volumeUsd")
        liquidity = market.get("liquidity") or market.get("liquidity_usd") or market.get("liquidityUsd")
        category = market.get("category") or market.get("categoryLabel")
        market_id = str(market.get("id") or market.get("market_id") or market.get("marketId") or question)
        results.append(
            MarketInfo(
                market_id=market_id,
                question=str(question),
                yes_token_id=yes_token_id,
                no_token_id=no_token_id,
                volume=float(volume) if volume is not None else None,
                liquidity=float(liquidity) if liquidity is not None else None,
                category=str(category) if category is not None else None,
            )
        )
        if len(results) >= config.max_markets:
            break
    return results
