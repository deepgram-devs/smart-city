"""Hotword detection for SAGA. Adapted from flask-agent-function-calling-demo."""

import random
import re
import time

_ACTIVATION_FILLERS = [
    "One moment.", "Pulling that up now.", "Running the query.",
    "On it.", "Right away.", "Stand by.", "Processing.",
]


# ---------------------------------------------------------------------------
# Hotword state
# ---------------------------------------------------------------------------

_current_hotword: str | None = None
_conversation_active: bool = False
_last_activity_time: float = 0.0
CONVERSATION_TIMEOUT = 30.0


def set_hotword(hotword: str | None):
    global _current_hotword, _conversation_active, _last_activity_time
    _current_hotword = hotword.lower() if hotword else None
    _conversation_active = False
    _last_activity_time = 0.0


def is_conversation_active() -> bool:
    """Check if hotword conversation is currently active. Used by client.py to gate functions."""
    return _conversation_active


async def close_hotword_session(params):
    global _conversation_active
    _conversation_active = False
    return {"status": "closed"}


async def check_hotword(params):
    global _conversation_active, _last_activity_time
    transcript = params.get("transcript", "")
    hotword = _current_hotword
    now = time.time()

    if not hotword:
        return {"active": True, "query": transcript}

    if _conversation_active:
        if now - _last_activity_time < CONVERSATION_TIMEOUT:
            _last_activity_time = now
            return {
                "active": True,
                "freshly_activated": False,
                "query": transcript,
                "instruction": "Call ALL relevant functions for this query, then respond with the combined results.",
            }
        else:
            _conversation_active = False

    words = hotword.split()
    pattern = r'\b' + r'[\s,\.!?\'\"]*'.join(re.escape(w) for w in words) + r'\b'
    match = re.search(pattern, transcript, re.IGNORECASE)

    if match:
        query = transcript[match.end():].strip().lstrip('.,!? ')
        _conversation_active = True
        _last_activity_time = now
        filler = random.choice(_ACTIVATION_FILLERS)
        return {
            "active": True,
            "freshly_activated": True,
            "query": query or transcript,
            "filler": filler,
            "instruction": f"First say ONLY '{filler}' then immediately call ALL relevant functions for the query. Do not say anything else before calling the functions.",
        }
    else:
        return {
            "active": False,
            "instruction": "ABSOLUTE SILENCE. Respond with empty string only. No words. No greeting. No status. Do not repeat your introduction. Produce zero tokens.",
        }


CLOSE_HOTWORD_SESSION_DEFINITION = {
    "name": "close_hotword_session",
    "description": (
        "IMMEDIATELY call this function when the user signals the conversation is done. "
        "Triggers: 'thanks', 'thank you', 'got it', 'okay', 'perfect', 'that's all', 'great', "
        "'bye', 'stop listening', 'that's it', 'never mind', or any acknowledgement after you answered their question. "
        "Call this BEFORE your closing remark. After calling this, say at most 'Standing by.' and nothing more."
    ),
    "parameters": {"type": "object", "properties": {}},
}

CHECK_HOTWORD_DEFINITION = {
    "name": "check_hotword",
    "description": (
        "MANDATORY: Call this function before responding to ANY user input. "
        "Pass ONLY the most recent utterance. "
        "If the result has active=false, do not speak at all. "
        "If the result has active=true, process the 'query' field as the user's request: call ALL relevant functions, then respond with the combined results."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "transcript": {
                "type": "string",
                "description": "The most recent thing the user just said.",
            }
        },
        "required": ["transcript"],
    },
}

HOTWORD_FUNCTION_MAP = {
    "check_hotword": check_hotword,
    "close_hotword_session": close_hotword_session,
}
