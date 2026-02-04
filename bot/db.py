from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


class BotDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                mode TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                market_id TEXT,
                yes_token_id TEXT,
                no_token_id TEXT,
                yes_ask REAL,
                no_ask REAL,
                edge_bps REAL,
                created_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                market_id TEXT,
                token_id TEXT,
                side TEXT,
                price REAL,
                size REAL,
                status TEXT,
                created_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                token_id TEXT,
                price REAL,
                size REAL,
                filled_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS imbalances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                market_id TEXT,
                yes_token_id TEXT,
                no_token_id TEXT,
                note TEXT,
                created_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_notional (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT,
                notional REAL
            )
            """
        )
        self.conn.commit()

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())
        cursor = self.conn.cursor()
        cursor.execute(
            f"INSERT INTO {table} ({keys}) VALUES ({placeholders})",
            values,
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def fetch_one(self, query: str, params: Iterable[Any]) -> Optional[sqlite3.Row]:
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()

    def execute(self, query: str, params: Iterable[Any]) -> None:
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
