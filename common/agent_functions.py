"""Hotword detection for SAGA. Adapted from flask-agent-function-calling-demo."""

import re
import time


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
            return {"active": True, "query": transcript}
        else:
            _conversation_active = False

    words = hotword.split()
    pattern = r'\b' + r'[\s,\.!?\'\"]*'.join(re.escape(w) for w in words) + r'\b'
    match = re.search(pattern, transcript, re.IGNORECASE)

    if match:
        query = transcript[match.end():].strip().lstrip('.,!? ')
        _conversation_active = True
        _last_activity_time = now
        return {"active": True, "query": query or transcript}
    else:
        return {
            "active": False,
            "instruction": "SILENCE. Do not produce any text, words, or sounds. Produce absolutely no output. Say nothing.",
        }


CLOSE_HOTWORD_SESSION_DEFINITION = {
    "name": "close_hotword_session",
    "description": (
        "Call this function when the conversation triggered by the hotword is complete. "
        "Triggers when the user's question is fully answered and they indicate satisfaction "
        "(e.g. 'thanks', 'got it', 'okay', 'that's all', 'perfect', 'great'). "
        "After calling this, return to silent listening mode."
    ),
    "parameters": {"type": "object", "properties": {}},
}

CHECK_HOTWORD_DEFINITION = {
    "name": "check_hotword",
    "description": (
        "MANDATORY: Call this function before responding to ANY user input. "
        "Pass ONLY the most recent utterance. "
        "If the result has active=false, do not speak at all. "
        "If the result has active=true, respond naturally to the 'query' field only."
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
