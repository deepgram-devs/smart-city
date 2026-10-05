"""Live voice control: speak routing, clamping, and the UpdateSpeak/UpdateThink wire.

Clamping is the load-bearing part: Deepgram closes the socket with no error on
an out-of-range expressivity (live-verified 2026-10-05), so these assert
literal bounds rather than the module's constants.
"""

import asyncio
import json
from pathlib import Path

import pytest

import client
from saga.voice import (
    EXPRESSIVITY_LABELS,
    FLUX_VOICES,
    STYLE_BY_EXPRESSIVITY,
    UPDATE_VOICE_DEFINITION,
    VoiceSettings,
    apply_voice_update,
    speak_provider,
    think_with_style,
    voice_summary,
)

BASE = VoiceSettings(model="flux-sienna-en")


def test_flux_routes_to_speak_v2_with_controls():
    assert speak_provider(BASE) == {
        "type": "deepgram", "version": "v2", "model": "flux-sienna-en",
        "speed": 1.0, "expressivity": 0,
    }


def test_aura_routes_to_speak_v1_without_flux_controls():
    assert speak_provider(VoiceSettings(model="aura-2-pandora-en")) == {
        "type": "deepgram", "version": "v1", "model": "aura-2-pandora-en",
    }


def test_settings_send_configured_voice_and_voice_tool():
    cfg = json.loads((Path(client.__file__).parent / "configs" / "saga.json").read_text())
    settings = client.build_settings()
    assert settings["agent"]["speak"]["provider"] == speak_provider(VoiceSettings(model=cfg["voiceModel"]))
    names = [f["name"] for f in settings["agent"]["think"]["functions"]]
    assert "update_voice" in names
    assert "update_voice" in settings["agent"]["think"]["prompt"]


@pytest.mark.parametrize("raw, expected", [
    (1, 1), (2, 2), (-2, -2), (5, 2), (-9, -2), (1.4, 1), ("2", 2), ("loud", 0), (None, 0),
    (float("inf"), 0), (float("-inf"), 0), (float("nan"), 0),
])
def test_expressivity_clamped_to_documented_range(raw, expected):
    assert apply_voice_update(BASE, {"expressivity": raw}).expressivity == expected


@pytest.mark.parametrize("raw, expected", [
    (1.25, 1.25), (3, 1.5), (0.1, 0.5), (1.12, 1.1), (1.13, 1.15), ("fast", 1.0),
    (float("inf"), 1.0), (float("nan"), 1.0),
])
def test_speed_clamped_and_snapped_to_005_steps(raw, expected):
    assert apply_voice_update(BASE, {"speed": raw}).speed == expected


def test_infinity_from_model_json_does_not_escape():
    """json.loads accepts Infinity; round(inf) raised OverflowError and ended the session."""
    params = json.loads('{"speed": Infinity, "expressivity": -Infinity}')
    assert apply_voice_update(BASE, params) == BASE


def test_voice_switch_only_to_known_flux_voices():
    assert apply_voice_update(BASE, {"voice": "Gemma"}).model == "flux-gemma-en"
    assert apply_voice_update(BASE, {"voice": "nonexistent"}).model == "flux-sienna-en"
    assert apply_voice_update(BASE, {}) == BASE


def test_schema_offers_exactly_the_clamped_ranges_and_known_voices():
    props = UPDATE_VOICE_DEFINITION["parameters"]["properties"]
    assert (props["expressivity"]["minimum"], props["expressivity"]["maximum"]) == (-2, 2)
    assert set(props["voice"]["enum"]) == set(FLUX_VOICES)
    assert "sienna" in FLUX_VOICES  # the configured voice must be switchable back to


def test_every_level_has_a_label_and_a_writing_style():
    assert set(EXPRESSIVITY_LABELS) == set(STYLE_BY_EXPRESSIVITY) == {-2, -1, 0, 1, 2}


def test_no_numeric_param_in_any_tool_uses_enum():
    """Class guard: Gemini rejects the whole function list ("Failed to think",
    live 2026-10-05) when an integer/number parameter has an enum."""
    functions = client.build_settings()["agent"]["think"]["functions"]
    assert len(functions) > 20  # the real list loaded, not an empty one
    bad = [
        (f["name"], name)
        for f in functions
        for name, spec in f.get("parameters", {}).get("properties", {}).items()
        if spec.get("type") in ("integer", "number") and "enum" in spec
    ]
    assert bad == []


def test_style_rebuilds_from_base_prompt_so_sections_never_stack():
    base = {"provider": {"type": "open_ai", "model": "m"}, "prompt": "BASE", "functions": [1]}
    lively = think_with_style(base, VoiceSettings(model="flux-sienna-en", expressivity=2))
    calm = think_with_style(base, VoiceSettings(model="flux-sienna-en", expressivity=-2))
    assert lively["prompt"].startswith("BASE") and "exclamation marks" in lively["prompt"]
    assert calm["prompt"].count("VOICE STYLE") == 1 and "no exclamation marks" in calm["prompt"]
    assert think_with_style(base, BASE)["prompt"] == "BASE"
    assert lively["functions"] == [1] and lively["provider"] == base["provider"]
    assert base["prompt"] == "BASE"  # not mutated


def test_summary_shows_deepgram_config():
    summary = voice_summary(VoiceSettings(model="flux-gemma-en", speed=1.25, expressivity=1), ["UpdateSpeak"])
    assert summary["message"] == "UpdateSpeak"
    assert voice_summary(BASE, [])["message"] == "no change"
    assert summary["provider"] == "deepgram · speak v2 (Flux TTS)"
    assert summary["voice"] == "Gemma (British female)"
    assert summary["speed"] == "1.25x"
    assert summary["expressivity"] == "+1 (expressive)"


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

    def __init__(self, arguments):
        self.sent = []
        self.messages = iter([json.dumps({
            "type": "FunctionCallRequest",
            "functions": [{"id": "voice-1", "name": "update_voice", "arguments": json.dumps(arguments)}],
        })])

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.messages)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, message):
        self.sent.append(json.loads(message))


def _run_update(monkeypatch, arguments):
    monkeypatch.setattr(client, "Speaker", _FakeSpeaker)
    monkeypatch.setattr(client, "is_conversation_active", lambda: True)
    agent = client.VoiceAgent()
    agent.voice = BASE
    agent._base_think = {"provider": {"type": "open_ai", "model": "m"}, "prompt": "BASE"}
    agent.ws = _FakeWebSocket(arguments)
    asyncio.run(agent.receiver())
    return agent


def test_expressivity_request_updates_speak_and_think_before_responding(monkeypatch):
    agent = _run_update(monkeypatch, {"expressivity": 7})
    types = [m["type"] for m in agent.ws.sent]
    assert types == ["UpdateSpeak", "UpdateThink", "FunctionCallResponse"]
    assert agent.ws.sent[0]["speak"]["provider"]["expressivity"] == 2  # clamped, not 7
    assert agent.ws.sent[1]["think"]["prompt"].startswith("BASE")
    assert agent.voice.expressivity == 2
    response = json.loads(agent.ws.sent[2]["content"])
    assert response["expressivity"] == "+2 (very expressive)"
    assert response["message"] == "UpdateSpeak + UpdateThink"


def test_speed_only_request_skips_prompt_update(monkeypatch):
    agent = _run_update(monkeypatch, {"speed": 1.3})
    assert [m["type"] for m in agent.ws.sent] == ["UpdateSpeak", "FunctionCallResponse"]
    assert agent.ws.sent[0]["speak"]["provider"]["speed"] == 1.3


def test_noop_request_sends_no_deepgram_update(monkeypatch):
    agent = _run_update(monkeypatch, {"expressivity": 0})
    assert [m["type"] for m in agent.ws.sent] == ["FunctionCallResponse"]
