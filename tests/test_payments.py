"""Reusable payment-provider contract and Eve integration tests."""

import asyncio
from decimal import Decimal

import pytest

from common.payments import (
    PaymentRequest,
    PaymentResult,
    SQUARE_SUCCESS_DEVICE_ID,
    SquareTerminalPaymentProvider,
    parse_payment_request,
    process_payment,
)
from saga.definitions import SAGA_FUNCTION_DEFINITIONS
from saga.functions import SAGA_FUNCTION_MAP


class RecordingProvider:
    def __init__(self):
        self.request = None

    def charge(self, request):
        self.request = request
        return PaymentResult(
            provider="Test provider",
            mode="test",
            status="COMPLETED",
            amount=f"{request.amount:.2f}",
            currency=request.currency,
            purpose=request.purpose,
            checkout_id="checkout-1",
            transaction_id="payment-1",
            payment_method="Test card",
            demo_illustrative=True,
        )


def test_payment_request_validation_and_normalization():
    request = parse_payment_request({"amount": "4.5", "currency": "usd", "purpose": " Marina parking "})
    assert request == PaymentRequest(Decimal("4.50"), "USD", "Marina parking")

    with pytest.raises(ValueError, match="greater than zero"):
        parse_payment_request({"amount": 0, "purpose": "invalid"})
    with pytest.raises(ValueError, match="greater than zero"):
        parse_payment_request({"amount": "NaN", "purpose": "invalid"})
    with pytest.raises(ValueError, match="supports USD only"):
        parse_payment_request({"amount": 100, "currency": "JPY", "purpose": "invalid"})
    with pytest.raises(ValueError, match="purpose is required"):
        parse_payment_request({"amount": 1, "purpose": "  "})


def test_provider_contract_is_replaceable():
    provider = RecordingProvider()
    result = process_payment(
        {"amount": 6.25, "currency": "USD", "purpose": "Podway day pass"},
        provider=provider,
    )
    assert provider.request == PaymentRequest(Decimal("6.25"), "USD", "Podway day pass")
    assert result["status"] == "COMPLETED"
    assert result["demo_illustrative"] is True


def test_no_credentials_uses_clear_square_simulation(monkeypatch):
    monkeypatch.delenv("SQUARE_SANDBOX_ACCESS_TOKEN", raising=False)
    result = SquareTerminalPaymentProvider(access_token=None).charge(
        PaymentRequest(Decimal("4.50"), "USD", "Harbour City parking")
    )
    assert result.provider == "Square Terminal Sandbox"
    assert result.mode == "simulated"
    assert result.status == "SIMULATED_COMPLETED"
    assert result.payment_method == "Sandbox test card"
    assert result.demo_illustrative is True


def test_square_sandbox_payload_uses_success_device(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"checkout": {"id": "sq-checkout", "status": "COMPLETED", "payment_ids": ["sq-payment"]}}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr("common.payments.requests.post", fake_post)
    result = SquareTerminalPaymentProvider(access_token="sandbox-token").charge(
        PaymentRequest(Decimal("7.50"), "USD", "Transit ticket")
    )

    checkout = captured["json"]["checkout"]
    assert captured["url"].endswith("/v2/terminals/checkouts")
    assert checkout["device_options"]["device_id"] == SQUARE_SUCCESS_DEVICE_ID
    assert checkout["amount_money"] == {"amount": 750, "currency": "USD"}
    assert result.mode == "sandbox_api"
    assert result.transaction_id == "sq-payment"


def test_square_sandbox_polls_through_in_progress(monkeypatch):
    statuses = iter([
        {"id": "sq-checkout", "status": "IN_PROGRESS"},
        {"id": "sq-checkout", "status": "COMPLETED", "payment_ids": ["sq-payment"]},
    ])

    class Response:
        def __init__(self, checkout):
            self.checkout = checkout

        def raise_for_status(self):
            return None

        def json(self):
            return {"checkout": self.checkout}

    monkeypatch.setattr(
        "common.payments.requests.post",
        lambda *args, **kwargs: Response({"id": "sq-checkout", "status": "PENDING"}),
    )
    monkeypatch.setattr(
        "common.payments.requests.get", lambda *args, **kwargs: Response(next(statuses))
    )
    monkeypatch.setattr("common.payments.time.sleep", lambda _seconds: None)

    result = SquareTerminalPaymentProvider(access_token="sandbox-token").charge(
        PaymentRequest(Decimal("7.50"), "USD", "Transit ticket")
    )
    assert result.status == "COMPLETED"
    assert result.transaction_id == "sq-payment"


def test_incomplete_checkout_has_no_transaction_id(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"checkout": {"id": "sq-checkout", "status": "CANCELED"}}

    monkeypatch.setattr("common.payments.requests.post", lambda *args, **kwargs: Response())
    result = SquareTerminalPaymentProvider(access_token="sandbox-token").charge(
        PaymentRequest(Decimal("7.50"), "USD", "Transit ticket")
    )
    assert result.status == "CANCELED"
    assert result.transaction_id is None


def test_eve_registers_and_executes_payment_tool(monkeypatch):
    definition_names = {definition["name"] for definition in SAGA_FUNCTION_DEFINITIONS}
    assert "process_payment" in definition_names

    monkeypatch.delenv("SQUARE_SANDBOX_ACCESS_TOKEN", raising=False)
    result = asyncio.run(
        SAGA_FUNCTION_MAP["process_payment"](
            {"amount": 5, "currency": "USD", "purpose": "Marina parking"}
        )
    )
    assert result["provider"] == "Square Terminal Sandbox"
    assert result["status"] == "SIMULATED_COMPLETED"
