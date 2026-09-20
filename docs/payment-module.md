# Reusable payment module

`common/payments.py` isolates the payment provider from Eve, Flask, and the
Deepgram Voice Agent. It can therefore be copied into another Python demo or
replaced behind the `PaymentProvider` protocol.

By default it performs a clearly labelled Square Terminal simulation: no card,
money, or credentials are involved. Set `SQUARE_SANDBOX_ACCESS_TOKEN` to make
the same `process_payment()` call create a real Square Sandbox Terminal
checkout using Square's successful test device ID. Square's Sandbox device
approves USD test payments up to $25.
The shared demo contract intentionally accepts USD only so zero-decimal
currencies cannot be converted with the wrong minor unit.

The returned dictionary has one stable shape in both modes: provider, mode,
status, amount, currency, purpose, checkout and transaction IDs, payment
method, and `demo_illustrative: true`.

Source checked 2026-09-20:
https://developer.squareup.com/docs/devtools/sandbox/testing#terminal-api-checkouts
