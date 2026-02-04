# Polymarket CLOB YES/NO Arbitrage Bot (Educational)

> **Disclaimer**: This repository is an educational reference implementation. It is **not** financial advice. Use at your own risk and respect Polymarket terms of service.

This bot discovers active Polymarket CLOB markets, extracts YES/NO token pairs, scans order books for cross-outcome arbitrage, and can optionally place hedged YES+NO limit buy orders.

## Features

- **Automatic discovery**: pulls markets from the CLOB API without a manual list.
- **Multi-shape parsing**: handles varying market JSON structures.
- **Order book scan**: finds opportunities when YES_ask + NO_ask + fees + slippage < 1.0.
- **Dry-run by default**: safe mode with no orders.
- **Live mode**: enable with `--live` and required env vars.
- **Risk controls**: per-trade and daily limits, cooldowns, minimum size.
- **SQLite logging**: tracks runs, opportunities, orders, fills, imbalances.

## Quick Start (Windows)

```powershell
# 1) Create venv
python -m venv .venv

# 2) Activate (allow scripts if needed)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1

# 3) Install deps
pip install -r requirements.txt

# 4) Create config & env
copy config.example.yaml config.yaml
copy .env.example .env

# 5) Dry-run
python -m bot --config config.yaml
```

## Quick Start (macOS/Linux)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
cp .env.example .env
python -m bot --config config.yaml
```

## Live Trading

> **Warning**: Live mode places real orders.

Set environment variables in `.env`:

```
POLYMARKET_API_KEY=
POLYMARKET_API_SECRET=
POLYMARKET_API_PASSPHRASE=
POLYMARKET_PRIVATE_KEY=
```

Then run:

```bash
python -m bot --config config.yaml --live
```

If credentials are missing, the bot exits with a clear message.

## Configuration

Key sections in `config.yaml`:

- `discovery`: market filters
  - `max_markets`: limit results
  - `min_volume_usd`: minimum 24h volume (if API supplies it)
  - `exclude_keywords` / `include_keywords`
  - `categories` (if API supplies it)
  - `min_liquidity` (if API supplies it)
- `trading`:
  - `fee_bps`, `slippage_bps`, `min_edge_bps`
  - `min_order_size`, `max_notional_per_trade`, `max_daily_notional`
  - `cooldown_ms_per_market`

The bot **does not require** manual token IDs—market discovery handles that automatically.

## How Discovery Works

1. Tries `py_clob_client` market listing (if available in SDK).
2. Falls back to HTTP endpoints:
   - `GET https://clob.polymarket.com/markets?active=true&limit=...`
3. Parses outcomes for YES/NO tokens even if fields are nested.

Markets without a valid YES/NO pair are skipped.

## Project Layout

```
bot/
  __main__.py
  adapter_polymarket.py
  market_discovery.py
  scanner.py
  executor.py
  risk.py
  db.py
  config.py
  logger.py
config.example.yaml
.env.example
requirements.txt
tests/
```

## Notes

- The bot uses `py_clob_client==0.34.5` and initializes `ClobClient` via `ApiCreds`.
- Order book access is compatible with both `get_order_book` and `get_orderbook`.

## Tests

```bash
pytest
```
