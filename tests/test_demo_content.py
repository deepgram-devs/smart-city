"""Customer-facing content contract.

These tests guard the demo persona that ships to customers: the hotword, the
TTS voice, and the management-team names the agent speaks. A future refactor
that accidentally reverts any of these would silently change what the customer
hears — pytest catches that here, since the structural tests in
test_function_consistency.py only check dict-key sync.

Keep this file in sync with whatever the customer signed off on: when a name
or voice changes, update both the source of truth (configs/saga.json plus
saga/mock_data.py:MANAGEMENT_STAKEHOLDERS) and the assertions below.
"""

import asyncio
import json
from pathlib import Path

import pytest

from saga.definitions import SAGA_FUNCTION_DEFINITIONS
from saga.functions import SAGA_FUNCTION_MAP
from saga.mock_data import (
    MANAGEMENT_STAKEHOLDERS,
    MANAGEMENT_STAKEHOLDERS_CSV,
    MANAGEMENT_STAKEHOLDERS_WITH_ROLES,
)

CONFIG_PATH = Path(__file__).parent.parent / "configs" / "saga.json"


@pytest.fixture(scope="module")
def cfg() -> dict:
    return json.loads(CONFIG_PATH.read_text())


# ---------------------------------------------------------------------------
# Voice + hotword: the wake word the customer says, and the voice they hear.
# ---------------------------------------------------------------------------

def test_voice_model_is_pandora(cfg):
    """British female aura-2 voice — locked per customer request.

    Note: aura-2-athena-en is documented en-gb but does not actually read as
    British (confirmed by ear, 2026-05-11). Pandora is the chosen voice; if
    the Deepgram catalog changes, re-audition before updating this assertion.
    """
    assert cfg["voiceModel"] == "aura-2-pandora-en"


def test_hotword_is_hey_eve(cfg):
    assert cfg["hotword"] == "Hey Eve"


def test_voice_name_and_greeting_use_eve(cfg):
    assert cfg["voiceName"] == "Eve"
    assert cfg["name"] == "Eve"
    assert "I'm Eve" in cfg["greeting"]
    assert "Hey Eve" in cfg["greeting"]


def test_legacy_brand_not_in_user_facing_config(cfg):
    """Catch a partial rename: 'SAGA' or 'Hey Saga' surviving in any visible field."""
    visible_fields = ["name", "company", "voiceName", "hotword", "greeting", "systemPrompt"]
    for field in visible_fields:
        value = cfg[field]
        assert "SAGA" not in value, f"Legacy 'SAGA' found in cfg[{field!r}]"
        assert "Hey Saga" not in value, f"Legacy 'Hey Saga' found in cfg[{field!r}]"


# ---------------------------------------------------------------------------
# Management team: the named stakeholders the agent emails on board prep.
# Must stay consistent across three surfaces (the constant, the function spec
# description sent to the LLM, and the system prompt narrative).
# ---------------------------------------------------------------------------

def test_management_stakeholders_appear_in_system_prompt(cfg):
    prompt = cfg["systemPrompt"]
    for _, name in MANAGEMENT_STAKEHOLDERS:
        assert name in prompt, f"Management stakeholder {name!r} missing from system prompt"


def test_old_management_names_removed_from_system_prompt(cfg):
    """Pre-rename stakeholder names must not leak into the persona."""
    prompt = cfg["systemPrompt"]
    for old_name in ("Donny Reyes", "Jordan Kwan", "Chris Peralta"):
        assert old_name not in prompt, f"Pre-rename name {old_name!r} still in system prompt"


def test_request_stakeholder_input_description_lists_current_team():
    """The LLM-facing function spec hints the current stakeholder names; if the
    constant changes, this description must reflect it automatically."""
    spec = next(d for d in SAGA_FUNCTION_DEFINITIONS if d["name"] == "request_stakeholder_input")
    recipients_desc = spec["parameters"]["properties"]["recipients"]["description"]
    assert MANAGEMENT_STAKEHOLDERS_WITH_ROLES in recipients_desc


def test_request_stakeholder_input_default_uses_current_team():
    """Runtime default when the LLM omits the recipients param."""
    result = asyncio.run(SAGA_FUNCTION_MAP["request_stakeholder_input"]({}))
    expected = [name for _, name in MANAGEMENT_STAKEHOLDERS]
    assert result["recipients"] == expected


def test_management_stakeholders_csv_matches_constant():
    expected = ", ".join(name for _, name in MANAGEMENT_STAKEHOLDERS)
    assert MANAGEMENT_STAKEHOLDERS_CSV == expected


# ---------------------------------------------------------------------------
# Brand surface in function returns: strings the LLM weaves into spoken replies.
# ---------------------------------------------------------------------------

def test_send_notification_method_uses_eve():
    result = asyncio.run(SAGA_FUNCTION_MAP["send_notification"]({}))
    assert result["method"] == "Eve wearable + email"


def test_generate_deck_link_uses_eve_domain():
    result = asyncio.run(SAGA_FUNCTION_MAP["generate_deck"]({}))
    assert "eve.city" in result["link"]
    assert "saga.city" not in result["link"]


def test_book_meeting_room_cast_string_uses_eve():
    result = asyncio.run(SAGA_FUNCTION_MAP["book_meeting_room"]({}))
    assert "Eve cast link ready" in result["av_confirmed"]
