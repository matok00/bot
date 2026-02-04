from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import os
import yaml
from dotenv import load_dotenv


@dataclass
class ClobConfig:
    host: str
    chain_id: int


@dataclass
class DiscoveryConfig:
    max_markets: int
    min_volume_usd: float
    exclude_keywords: List[str]
    include_keywords: List[str]
    categories: List[str]
    min_liquidity: float
    only_active: bool


@dataclass
class TradingConfig:
    fee_bps: float
    slippage_bps: float
    min_edge_bps: float
    min_order_size: float
    max_notional_per_trade: float
    max_daily_notional: float
    max_open_orders: int
    cooldown_ms_per_market: int
    max_slippage_live_bps: float
    cancel_on_shutdown: bool


@dataclass
class LoggingConfig:
    level: str
    jsonl: bool


@dataclass
class AppConfig:
    clob: ClobConfig
    discovery: DiscoveryConfig
    trading: TradingConfig
    logging: LoggingConfig


DEFAULT_CONFIG = {
    "clob": {"host": "https://clob.polymarket.com", "chain_id": 137},
    "discovery": {
        "max_markets": 200,
        "min_volume_usd": 0,
        "exclude_keywords": [],
        "include_keywords": [],
        "categories": [],
        "min_liquidity": 0,
        "only_active": True,
    },
    "trading": {
        "fee_bps": 100,
        "slippage_bps": 50,
        "min_edge_bps": 0,
        "min_order_size": 1,
        "max_notional_per_trade": 100,
        "max_daily_notional": 1000,
        "max_open_orders": 10,
        "cooldown_ms_per_market": 30000,
        "max_slippage_live_bps": 150,
        "cancel_on_shutdown": True,
    },
    "logging": {"level": "INFO", "jsonl": True},
}


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: Optional[str]) -> AppConfig:
    load_dotenv()
    config_data: Dict[str, Any] = DEFAULT_CONFIG
    if path:
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        with config_path.open("r", encoding="utf-8") as handle:
            file_data = yaml.safe_load(handle) or {}
        config_data = _merge_dict(DEFAULT_CONFIG, file_data)

    clob = config_data["clob"]
    discovery = config_data["discovery"]
    trading = config_data["trading"]
    logging_cfg = config_data["logging"]

    return AppConfig(
        clob=ClobConfig(host=clob["host"], chain_id=int(clob["chain_id"])),
        discovery=DiscoveryConfig(
            max_markets=int(discovery["max_markets"]),
            min_volume_usd=float(discovery.get("min_volume_usd", 0)),
            exclude_keywords=list(discovery.get("exclude_keywords", [])),
            include_keywords=list(discovery.get("include_keywords", [])),
            categories=list(discovery.get("categories", [])),
            min_liquidity=float(discovery.get("min_liquidity", 0)),
            only_active=bool(discovery.get("only_active", True)),
        ),
        trading=TradingConfig(
            fee_bps=float(trading["fee_bps"]),
            slippage_bps=float(trading["slippage_bps"]),
            min_edge_bps=float(trading["min_edge_bps"]),
            min_order_size=float(trading["min_order_size"]),
            max_notional_per_trade=float(trading["max_notional_per_trade"]),
            max_daily_notional=float(trading["max_daily_notional"]),
            max_open_orders=int(trading["max_open_orders"]),
            cooldown_ms_per_market=int(trading["cooldown_ms_per_market"]),
            max_slippage_live_bps=float(trading["max_slippage_live_bps"]),
            cancel_on_shutdown=bool(trading.get("cancel_on_shutdown", True)),
        ),
        logging=LoggingConfig(level=logging_cfg["level"], jsonl=bool(logging_cfg["jsonl"])),
    )


def load_env_creds() -> Dict[str, Optional[str]]:
    return {
        "api_key": os.getenv("POLYMARKET_API_KEY"),
        "api_secret": os.getenv("POLYMARKET_API_SECRET"),
        "api_passphrase": os.getenv("POLYMARKET_API_PASSPHRASE"),
        "private_key": os.getenv("POLYMARKET_PRIVATE_KEY"),
    }
