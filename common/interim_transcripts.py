"""Live user captions: a parallel Flux STT stream beside the Voice Agent.

The Voice Agent socket only reports what the user said once the turn ends
(ConversationText). Measured 2026-10-05: no interim-transcript event exists on
it with either nova-3 or Flux listen. So the UI's live caption comes from a
second, STT-only Flux socket on /v2/listen fed the same mic audio, whose
TurnInfo events carry the running transcript about every 240 ms.

It roughly doubles STT minutes, and it is cosmetic: every failure here is
logged and swallowed, never allowed to touch the agent session.

Keep this model the same as the agent's listen model (FLUX_STT_MODEL) so both
streams cut turns in the same places and the caption matches the final text.
"""

import asyncio
import json
import logging
from urllib.parse import urlencode

import websockets

FLUX_STT_MODEL = "flux-general-en"
FLUX_LISTEN_URL = "wss://api.deepgram.com/v2/listen"

logger = logging.getLogger(__name__)


def interim_url(keyterms, sample_rate: int) -> str:
    query = [("model", FLUX_STT_MODEL), ("encoding", "linear16"), ("sample_rate", sample_rate)]
    query += [("keyterm", k) for k in keyterms]
    return f"{FLUX_LISTEN_URL}?{urlencode(query)}"


def caption_event(msg: dict) -> dict | None:
    """Map a Flux TurnInfo message to the UI's user_interim payload, or None."""
    if msg.get("type") != "TurnInfo":
        return None
    return {
        "turn": msg.get("turn_index"),
        "text": msg.get("transcript", ""),
        "final": msg.get("event") == "EndOfTurn",
    }


class InterimTranscriber:
    def __init__(self, emit):
        self._emit = emit  # emit(payload) -> pushes user_interim to the browser
        self._ws = None
        self._task = None
        self._last = None

    async def start(self, api_key: str, keyterms, sample_rate: int) -> None:
        try:
            self._ws = await websockets.connect(
                interim_url(keyterms, sample_rate),
                extra_headers={"Authorization": f"Token {api_key}"},
            )
            self._task = asyncio.create_task(self._receive())
        except Exception as exc:
            logger.warning(f"Interim captions unavailable: {exc}")
            self._ws = None

    async def send(self, audio: bytes) -> None:
        if not self._ws or self._ws.closed:
            return
        try:
            await self._ws.send(audio)
        except Exception as exc:
            logger.warning(f"Interim captions stopped: {exc}")
            self._ws = None

    async def _receive(self) -> None:
        try:
            async for raw in self._ws:
                event = caption_event(json.loads(raw))
                # Flux repeats an unchanged transcript every update; only
                # forward changes (and every end of turn).
                if event and (event["final"] or (event["turn"], event["text"]) != self._last):
                    self._last = (event["turn"], event["text"])
                    self._emit(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(f"Interim captions receiver ended: {exc}")

    async def close(self) -> None:
        if self._task:
            self._task.cancel()
        if self._ws and not self._ws.closed:
            try:
                await self._ws.send(json.dumps({"type": "CloseStream"}))
                await self._ws.close()
            except Exception:
                pass
