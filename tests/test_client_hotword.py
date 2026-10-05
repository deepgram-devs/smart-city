"""Hotword activation inside one user turn: one filler, no re-run instruction."""

import asyncio
import json

import client
from common import agent_functions


class _FakeSpeaker:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def stop(self):
        pass

    async def play(self, _message):
        pass


class _FakeWebSocket:
    closed = False

    def __init__(self, frames):
        self.sent = []
        self.messages = iter(json.dumps(f) for f in frames)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, message):
        self.sent.append(json.loads(message))


def _user(text):
    return {"type": "ConversationText", "role": "user", "content": text}


def _call(fn_id, name, arguments):
    return {"type": "FunctionCallRequest",
            "functions": [{"id": fn_id, "name": name, "arguments": json.dumps(arguments)}]}


def _run(monkeypatch, frames):
    monkeypatch.setattr(client, "Speaker", _FakeSpeaker)
    agent_functions.set_hotword("Hey Eve")
    agent = client.VoiceAgent()
    agent.voice = client.VoiceSettings(model="flux-sienna-en")
    agent._base_think = {"provider": {"type": "open_ai", "model": "m"}, "prompt": "BASE"}
    agent.ws = _FakeWebSocket(frames)
    asyncio.run(agent.receiver())
    return agent.ws.sent


def _fillers(sent):
    return [m for m in sent if m["type"] == "InjectAgentMessage"]


def _response(sent, fn_id):
    return json.loads(next(m["content"] for m in sent if m.get("id") == fn_id))


def test_model_check_hotword_after_auto_activation_is_not_a_second_activation(monkeypatch):
    """Observed live 2026-10-05: 'One moment.' then 'Pulling that up now.' and
    update_voice called twice, because the same utterance activated twice."""
    utterance = "Hey, Eve. Can you speak with a little bit more expressiveness?"
    sent = _run(monkeypatch, [
        _user(utterance),
        _call("v1", "update_voice", {"expressivity": 1}),       # model skipped check_hotword
        _call("h1", "check_hotword", {"transcript": utterance}),  # ...then called it anyway
    ])
    assert len(_fillers(sent)) == 1
    hotword = _response(sent, "h1")
    assert hotword["freshly_activated"] is False
    assert "Do not repeat" in hotword["instruction"]


def test_model_calling_check_hotword_twice_in_one_turn_fills_once(monkeypatch):
    utterance = "Hey Eve, how is the grid?"
    sent = _run(monkeypatch, [
        _user(utterance),
        _call("h1", "check_hotword", {"transcript": utterance}),
        _call("h2", "check_hotword", {"transcript": utterance}),
    ])
    assert len(_fillers(sent)) == 1
    assert _response(sent, "h1")["freshly_activated"] is True
    assert _response(sent, "h2")["freshly_activated"] is False


def test_next_utterance_with_hotword_activates_normally(monkeypatch):
    sent = _run(monkeypatch, [
        _user("Hey Eve, be more expressive"),
        _call("v1", "update_voice", {"expressivity": 1}),
        _user("Hey Eve, how is the grid?"),
        _call("h2", "check_hotword", {"transcript": "Hey Eve, how is the grid?"}),
    ])
    assert len(_fillers(sent)) == 2  # one per turn
    assert _response(sent, "h2")["freshly_activated"] is True
