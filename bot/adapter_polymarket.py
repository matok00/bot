from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import ApiCreds
except ImportError:  # pragma: no cover - dependency optional in tests
    ClobClient = None
    ApiCreds = None


@dataclass
class OrderResult:
    order_id: str
    status: str


class PolymarketAdapter:
    def __init__(self, host: str, chain_id: int, creds: Optional[Dict[str, str]] = None) -> None:
        if ClobClient is None:
            raise RuntimeError("py_clob_client is not installed")
        if creds:
            api_creds = ApiCreds(creds["api_key"], creds["api_secret"], creds["api_passphrase"])
        else:
            api_creds = None
        if api_creds is not None:
            self.client = ClobClient(host=host, chain_id=chain_id, creds=api_creds)
        else:
            self.client = ClobClient(host=host, chain_id=chain_id)

    def get_markets(self, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        if hasattr(self.client, "get_markets"):
            return self.client.get_markets(params or {})
        return None

    def get_order_book(self, token_id: str) -> Any:
        if hasattr(self.client, "get_order_book"):
            return self.client.get_order_book(token_id)
        if hasattr(self.client, "get_orderbook"):
            return self.client.get_orderbook(token_id)
        raise AttributeError("ClobClient missing get_order_book/get_orderbook")

    def place_limit_buy(self, token_id: str, price: float, size: float) -> OrderResult:
        response = self.client.create_order(
            {
                "token_id": token_id,
                "price": str(price),
                "size": str(size),
                "side": "BUY",
                "type": "LIMIT",
            }
        )
        order_id = response.get("order_id") or response.get("id") or "unknown"
        status = response.get("status") or "submitted"
        return OrderResult(order_id=order_id, status=status)

    def cancel(self, order_id: str) -> Any:
        return self.client.cancel(order_id)

    def get_order_status(self, order_id: str) -> Any:
        if hasattr(self.client, "get_order"):
            return self.client.get_order(order_id)
        if hasattr(self.client, "get_order_status"):
            return self.client.get_order_status(order_id)
        raise AttributeError("ClobClient missing get_order/get_order_status")
