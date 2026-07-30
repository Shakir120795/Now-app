"""Payment gateway interface. Region-pluggable — India adapters implement this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class IntentResult:
    provider: str
    provider_ref: str          # gateway order id
    amount: int
    currency: str
    extra: dict                # client-side params (key_id, callback url, etc.)


class PaymentGateway(ABC):
    name: str

    @abstractmethod
    async def create_intent(self, *, order_number: str, amount: int, currency: str) -> IntentResult:
        """Create a gateway order/intent and return client params."""

    @abstractmethod
    def verify_callback(self, data: dict, raw_body: bytes, signature: str) -> bool:
        """Verify a client verify payload or webhook signature."""
