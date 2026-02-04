from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class JsonlFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str, jsonl_enabled: bool) -> logging.Logger:
    logger = logging.getLogger("bot")
    logger.setLevel(level.upper())
    logger.handlers.clear()
    logger.propagate = False

    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level.upper())
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    if jsonl_enabled:
        json_handler = logging.FileHandler(logs_dir / "bot.jsonl", encoding="utf-8")
        json_handler.setLevel(level.upper())
        json_handler.setFormatter(JsonlFormatter())
        logger.addHandler(json_handler)

    return logger
