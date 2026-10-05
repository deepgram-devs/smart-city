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
    """Owns the caption socket. Nothing here may block or fail the agent:

    - feed() never awaits: audio goes into a small bounded queue and the
      oldest chunk is dropped when the caption socket falls behind, so a
      stalled caption connection cannot stall agent audio or barge-in.
    - start() only schedules the connect, so a slow handshake cannot delay
      the agent session.
    - A dropped caption stream reconnects with backoff, a bounded number of
      times, so one network blip does not end captions for the session.
    """

    QUEUE_CHUNKS = 50  # ~1 s of 20 ms chunks; captions past that are stale anyway
    RETRY_DELAYS = (1, 2, 4, 8)  # reconnects per session; then captions stay off

    def __init__(self, emit):
        self._emit = emit  # emit(payload) -> pushes user_interim to the browser
        self._queue = asyncio.Queue(maxsize=self.QUEUE_CHUNKS)
        self._ws = None
        self._task = None
        self._last = None

    def start(self, api_key: str, keyterms, sample_rate: int) -> None:
        self._task = asyncio.create_task(self._run(api_key, keyterms, sample_rate))

    def feed(self, audio: bytes) -> None:
        if self._task is None or self._task.done():
            return
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(audio)

    async def _run(self, api_key, keyterms, sample_rate) -> None:
        for delay in (0, *self.RETRY_DELAYS):
            await asyncio.sleep(delay)
            try:
                await self._stream(api_key, keyterms, sample_rate)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(f"Interim captions dropped ({exc}); reconnecting")
            finally:
                await self._close_socket()
        logger.warning("Interim captions off for this session after repeated failures")

    async def _stream(self, api_key, keyterms, sample_rate) -> None:
        self._ws = await websockets.connect(
            interim_url(keyterms, sample_rate),
            extra_headers={"Authorization": f"Token {api_key}"},
        )
        # Either side ending (socket closed, send failed) ends both.
        tasks = [asyncio.create_task(self._pump()), asyncio.create_task(self._receive())]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            # Retrieve every outcome so none is reported as "never retrieved".
            results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            raise errors[0]

    async def _pump(self) -> None:
        while True:
            await self._ws.send(await self._queue.get())

    async def _receive(self) -> None:
        async for raw in self._ws:
            event = caption_event(json.loads(raw))
            # Flux repeats an unchanged transcript every update; only
            # forward changes (and every end of turn).
            if event and (event["final"] or (event["turn"], event["text"]) != self._last):
                self._last = (event["turn"], event["text"])
                self._emit(event)

    async def _close_socket(self) -> None:
        ws, self._ws = self._ws, None
        if ws is None or ws.closed:
            return
        try:
            # Bounded: a peer that stopped draining would hang this send forever.
            await asyncio.wait_for(ws.send(json.dumps({"type": "CloseStream"})), 0.5)
        except Exception:
            pass
        finally:
            try:
                await asyncio.wait_for(ws.close(), 1)  # library default waits up to 10 s
            except Exception:
                pass

    async def close(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            # Bounded wait for _run's finally (which closes the socket; at most
            # 0.5 s + 1 s). Do not `await self._task` under a blanket except:
            # that would also swallow a cancellation aimed at close() itself.
            await asyncio.wait([self._task], timeout=2)
