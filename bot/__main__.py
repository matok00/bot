from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from .adapter_polymarket import PolymarketAdapter
from .config import load_config, load_env_creds
from .db import BotDB
from .executor import execute_opportunity
from .logger import setup_logging
from .market_discovery import discover_markets
from .risk import RiskLimits
from .scanner import scan_market


LOCK_PATH = Path("data") / "bot.lock"


def _write_lock() -> None:
    if LOCK_PATH.exists():
        raise RuntimeError("Lock file exists: data/bot.lock. Another instance may be running.")
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")


def _remove_lock() -> None:
    if LOCK_PATH.exists():
        LOCK_PATH.unlink()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Polymarket YES/NO arbitrage bot")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument("--live", action="store_true", help="Enable live trading")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    logger = setup_logging(config.logging.level, config.logging.jsonl)

    try:
        _write_lock()
    except RuntimeError as exc:
        logger.error(str(exc))
        return 1

    def _shutdown(*_: object) -> None:
        if config.trading.cancel_on_shutdown:
            logger.info("Shutdown requested. Cancel-on-shutdown enabled.")
        _remove_lock()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    creds = load_env_creds()
    has_creds = bool(creds.get("api_key") and creds.get("api_secret") and creds.get("api_passphrase"))
    if args.live and not has_creds:
        logger.error("Live mode requires POLYMARKET_API_KEY/SECRET/PASSPHRASE")
        _remove_lock()
        return 1

    try:
        adapter = PolymarketAdapter(config.clob.host, config.clob.chain_id, creds if has_creds else None)
    except Exception as exc:
        if not args.live:
            logger.error("need creds to read books: %s", exc)
            _remove_lock()
            return 1
        raise

    db = BotDB(Path("data") / "bot.db")
    run_id = db.insert(
        "runs",
        {
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "live" if args.live else "dry-run",
        },
    )

    markets = discover_markets(config.discovery, adapter=adapter, host=config.clob.host)
    logger.info("Discovered %d markets", len(markets))

    limits = RiskLimits(
        max_notional_per_trade=config.trading.max_notional_per_trade,
        max_daily_notional=config.trading.max_daily_notional,
        max_open_orders=config.trading.max_open_orders,
        min_order_size=config.trading.min_order_size,
    )

    for market in markets:
        try:
            yes_book = adapter.get_order_book(market.yes_token_id)
            no_book = adapter.get_order_book(market.no_token_id)
        except Exception as exc:
            logger.warning("Failed to load order book for %s: %s", market.market_id, exc)
            continue

        opportunity = scan_market(
            market,
            yes_book,
            no_book,
            config.trading.fee_bps,
            config.trading.slippage_bps,
            config.trading.min_order_size,
        )
        if opportunity is None:
            continue
        if opportunity.edge_bps < config.trading.min_edge_bps:
            continue

        db.insert(
            "opportunities",
            {
                "run_id": run_id,
                "market_id": market.market_id,
                "yes_token_id": market.yes_token_id,
                "no_token_id": market.no_token_id,
                "yes_ask": opportunity.yes.price,
                "no_ask": opportunity.no.price,
                "edge_bps": opportunity.edge_bps,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
        logger.info(
            "Opportunity %s edge=%.2f bps cost=%.4f", market.market_id, opportunity.edge_bps, opportunity.all_in_cost
        )

        if args.live:
            result = execute_opportunity(
                adapter,
                db,
                opportunity,
                limits,
                run_id,
                config.trading.max_slippage_live_bps,
            )
            logger.info("Execution result: %s", result.message)
        else:
            logger.info("Dry run - no orders placed")

        time.sleep(config.trading.cooldown_ms_per_market / 1000)

    _remove_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
