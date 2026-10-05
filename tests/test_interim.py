"""Live user captions from the parallel Flux STT stream."""

import asyncio
import json
from urllib.parse import parse_qs, urlparse

import client
from common import interim_transcripts as it


def _turn(event, text, turn=0):
    return {"type": "TurnInfo", "event": event, "transcript": text, "turn_index": turn}


def test_caption_event_maps_flux_turninfo():
    """Shapes captured from a live /v2/listen stream, 2026-10-05."""
    assert it.caption_event(_turn("Update", "systems on")) == {"turn": 0, "text": "systems on", "final": False}
    assert it.caption_event(_turn("EndOfTurn", "Systems online.", 3))["final"] is True
    assert it.caption_event({"type": "Connected", "request_id": "x"}) is None


def test_url_carries_model_audio_format_and_every_keyterm():
    q = parse_qs(urlparse(it.interim_url(["Hey Eve", "Eve"], 16000)).query)
    assert q["model"] == ["flux-general-en"]
    assert q["encoding"] == ["linear16"] and q["sample_rate"] == ["16000"]
    assert q["keyterm"] == ["Hey Eve", "Eve"]


def test_agent_listen_uses_the_same_flux_model_as_captions():
    """Different models cut turns differently and the caption would not match."""
    listen = client.build_settings()["agent"]["listen"]["provider"]
    assert listen["model"] == it.FLUX_STT_MODEL
    assert listen["version"] == "v2"
    assert "Hey Eve" in listen["keyterms"]


class _FakeFluxSocket:
    closed = False

    def __init__(self, frames):
        self.frames = iter(json.dumps(f) for f in frames)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.frames)
        except StopIteration:
            raise StopAsyncIteration


def test_unchanged_updates_are_not_re_emitted_but_end_of_turn_always_is():
    emitted = []
    tr = it.InterimTranscriber(emitted.append)
    tr._ws = _FakeFluxSocket([
        _turn("Update", "systems"), _turn("Update", "systems"),
        _turn("Update", "systems online"), _turn("EndOfTurn", "systems online"),
    ])
    asyncio.run(tr._receive())
    assert [(e["text"], e["final"]) for e in emitted] == [
        ("systems", False), ("systems online", False), ("systems online", True),
    ]


def test_connect_failure_is_swallowed_and_send_is_a_noop(monkeypatch):
    async def refuse(*_a, **_k):
        raise OSError("refused")

    monkeypatch.setattr(it.websockets, "connect", refuse)

    async def exercise():
        tr = it.InterimTranscriber(lambda _e: None)
        await tr.start("key", ["Eve"], 16000)  # must not raise
        await tr.send(b"\x00" * 640)           # must not raise
        await tr.close()

    asyncio.run(exercise())


def test_sender_feeds_mic_audio_to_agent_and_captions():
    class _Sink:
        closed = False

        def __init__(self):
            self.got = []

        async def send(self, data):
            self.got.append(data)

    async def exercise():
        agent = client.VoiceAgent()
        agent.ws = _Sink()
        captions = _Sink()
        agent.interim._ws = captions
        agent.is_running = True
        task = asyncio.create_task(agent.sender())
        await agent.mic_audio_queue.put(b"pcm")
        await asyncio.sleep(0.01)
        agent.is_running = False
        task.cancel()
        assert agent.ws.got == [b"pcm"]
        assert captions.got == [b"pcm"]

    asyncio.run(exercise())
