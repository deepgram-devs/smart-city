"""Reusable payment providers for voice demos.

The agent-facing function in :mod:`saga.functions` depends on this small
provider contract rather than on Square directly.  Other demos can reuse the
module, replace the provider, or exercise the deterministic simulation without
bringing any Voice Agent or Flask code with them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
import time
from typing import Protocol
from uuid import uuid4

import requests


SQUARE_SANDBOX_BASE_URL = "https://connect.squareupsandbox.com"
SQUARE_SUCCESS_DEVICE_ID = "9fa747a2-25ff-48ee-b078-04381f7c828f"
SQUARE_SANDBOX_APPROVAL_LIMIT_USD = 25


@dataclass(frozen=True)
class PaymentRequest:
    amount: Decimal
    currency: str
    purpose: str


@dataclass(frozen=True)
class PaymentResult:
    provider: str
    mode: str
    status: str
    amount: str
    currency: str
    purpose: str
    checkout_id: str
    transaction_id: str | None
    payment_method: str
    demo_illustrative: bool

    def to_dict(self) -> dict:
        return asdict(self)


class PaymentProvider(Protocol):
    def charge(self, request: PaymentRequest) -> PaymentResult: ...


def parse_payment_request(params: dict) -> PaymentRequest:
    try:
        amount = Decimal(str(params.get("amount", "4.50"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("amount must be a valid number") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("amount must be greater than zero")

    currency = str(params.get("currency", "USD")).upper().strip()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("currency must be a three-letter ISO code")
    # This demo's Square success device and $25 approval guarantee are USD-only.
    # Restricting the reusable contract avoids silently treating zero-decimal
    # currencies such as JPY as though they had cents.
    if currency != "USD":
        raise ValueError("this demo payment provider supports USD only")

    purpose = str(params.get("purpose", "Harbour City service")).strip()
    if not purpose:
        raise ValueError("purpose is required")
    return PaymentRequest(amount=amount, currency=currency, purpose=purpose)


class SquareTerminalPaymentProvider:
    """Square Terminal Sandbox with a deterministic no-credential simulation.

    Set ``SQUARE_SANDBOX_ACCESS_TOKEN`` to create a real Square Sandbox
    Terminal checkout.  Without it, the provider returns the same stable,
    visibly simulated result shape so a demo never needs a real card or money.
    """

    def __init__(self, access_token: str | None = None, timeout_seconds: float = 8):
        self.access_token = access_token or os.getenv("SQUARE_SANDBOX_ACCESS_TOKEN")
        self.timeout_seconds = timeout_seconds

    def charge(self, request: PaymentRequest) -> PaymentResult:
        if self.access_token:
            return self._sandbox_checkout(request)
        return self._simulated_checkout(request)

    def _simulated_checkout(self, request: PaymentRequest) -> PaymentResult:
        suffix = uuid4().hex[:10].upper()
        return PaymentResult(
            provider="Square Terminal Sandbox",
            mode="simulated",
            status="SIMULATED_COMPLETED",
            amount=f"{request.amount:.2f}",
            currency=request.currency,
            purpose=request.purpose,
            checkout_id=f"DEMO-CHECKOUT-{suffix}",
            transaction_id=f"DEMO-PAY-{suffix}",
            payment_method="Sandbox test card",
            demo_illustrative=True,
        )

    def _sandbox_checkout(self, request: PaymentRequest) -> PaymentResult:
        if request.currency == "USD" and request.amount > SQUARE_SANDBOX_APPROVAL_LIMIT_USD:
            raise ValueError("Square's successful Sandbox device approves USD payments up to $25")

        idempotency_key = str(uuid4())
        response = requests.post(
            f"{SQUARE_SANDBOX_BASE_URL}/v2/terminals/checkouts",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json={
                "idempotency_key": idempotency_key,
                "checkout": {
                    "amount_money": {
                        "amount": int(request.amount * 100),
                        "currency": request.currency,
                    },
                    "device_options": {"device_id": SQUARE_SUCCESS_DEVICE_ID},
                    "note": request.purpose,
                },
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        checkout = response.json()["checkout"]
        # Terminal creation is asynchronous, including in Sandbox. Poll the
        # checkout briefly so the voice turn reports the simulated buyer's
        # completed result instead of narrating the initial PENDING envelope.
        for _ in range(10):
            if checkout.get("status") in {"COMPLETED", "CANCELED"}:
                break
            time.sleep(0.3)
            status_response = requests.get(
                f"{SQUARE_SANDBOX_BASE_URL}/v2/terminals/checkouts/{checkout['id']}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=self.timeout_seconds,
            )
            status_response.raise_for_status()
            checkout = status_response.json()["checkout"]
        payment_ids = checkout.get("payment_ids") or []
        return PaymentResult(
            provider="Square Terminal Sandbox",
            mode="sandbox_api",
            status=str(checkout.get("status", "UNKNOWN")),
            amount=f"{request.amount:.2f}",
            currency=request.currency,
            purpose=request.purpose,
            checkout_id=str(checkout["id"]),
            transaction_id=str(payment_ids[0]) if payment_ids else None,
            payment_method="Square Sandbox test card",
            demo_illustrative=True,
        )


def payment_provider() -> PaymentProvider:
    return SquareTerminalPaymentProvider()


def process_payment(params: dict, provider: PaymentProvider | None = None) -> dict:
    request = parse_payment_request(params)
    return (provider or payment_provider()).charge(request).to_dict()
