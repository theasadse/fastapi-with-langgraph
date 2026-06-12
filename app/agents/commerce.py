from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Protocol
from uuid import uuid4


class OrderGateway(Protocol):
    mode: str

    def place_order(
        self,
        cart: dict[str, Any],
        shipping: dict[str, str],
    ) -> dict[str, Any]:
        """Place an order through the configured commerce provider."""


class DemoOrderGateway:
    mode = "demo"

    def place_order(
        self,
        cart: dict[str, Any],
        shipping: dict[str, str],
    ) -> dict[str, Any]:
        return {
            "order_id": f"DEMO-{uuid4().hex[:10].upper()}",
            "status": "simulated_placed",
            "mode": self.mode,
            "item_count": sum(
                int(item.get("quantity", 1))
                for item in cart.get("items", [])
            ),
            "shipping_destination": {
                "city": shipping["city"],
                "region": shipping["region"],
                "country": shipping["country"],
            },
            "contact_email": _mask_email(shipping["contact_email"]),
            "placed_at": datetime.now(UTC).isoformat(),
            "message": (
                "The demo order was placed after explicit confirmation. "
                "No retailer or payment processor was charged."
            ),
        }


@lru_cache(maxsize=1)
def get_order_gateway() -> OrderGateway:
    return DemoOrderGateway()


def _mask_email(email: str) -> str:
    local, separator, domain = email.partition("@")
    if not separator:
        return "***"
    visible = local[:1] if local else ""
    return f"{visible}***@{domain}"
