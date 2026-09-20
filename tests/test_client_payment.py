"""Voice receiver responsiveness for slow payment providers."""

import asyncio
import json

import client


def test_payment_call_does_not_block_barge_in(monkeypatch):
    events = []

    class FakeSpeaker:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def stop(self):
            events.append("barge-in")

        async def play(self, _message):
            events.append("audio")

    class FakeWebSocket:
        closed = False

        def __init__(self):
            self.sent = []
            self.messages = iter([
                json.dumps({
                    "type": "FunctionCallRequest",
                    "functions": [{
                        "id": "payment-1",
                        "name": "process_payment",
                        "arguments": '{"amount":4.5,"purpose":"Parking"}',
                    }],
                }),
                json.dumps({"type": "UserStartedSpeaking"}),
            ])

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.messages)
            except StopIteration:
                raise StopAsyncIteration

        async def send(self, message):
            self.sent.append(json.loads(message))

    async def slow_payment(_params):
        events.append("payment-start")
        await asyncio.sleep(0.05)
        events.append("payment-end")
        return {"status": "SIMULATED_COMPLETED", "demo_illustrative": True}

    async def exercise():
        monkeypatch.setattr(client, "Speaker", FakeSpeaker)
        monkeypatch.setattr(client, "is_conversation_active", lambda: True)
        monkeypatch.setitem(client.FUNCTION_MAP, "process_payment", slow_payment)
        agent = client.VoiceAgent()
        agent.ws = FakeWebSocket()
        await agent.receiver()
        assert "barge-in" in events
        assert "payment-end" not in events
        await asyncio.gather(*agent._background_calls)
        assert events.index("barge-in") < events.index("payment-end")
        assert any(message.get("id") == "payment-1" for message in agent.ws.sent)

    asyncio.run(exercise())
