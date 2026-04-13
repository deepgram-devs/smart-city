"""SAGA Smart City Voice AI Demo - Main Flask app."""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import asyncio
import websockets
import os
import json
import threading
import janus
import queue
import logging
from dotenv import load_dotenv

from common.agent_functions import (
    HOTWORD_FUNCTION_MAP,
    CHECK_HOTWORD_DEFINITION,
    CLOSE_HOTWORD_SESSION_DEFINITION,
    set_hotword,
    is_conversation_active,
    check_hotword,
)
from saga.functions import SAGA_FUNCTION_MAP, get_random_filler
from saga.definitions import SAGA_FUNCTION_DEFINITIONS
from saga.mock_data import get_city_state, reset_city_state

load_dotenv()

FUNCTION_MAP = {**HOTWORD_FUNCTION_MAP, **SAGA_FUNCTION_MAP}

VOICE_AGENT_URL = "wss://agent.deepgram.com/v1/agent/converse"
AUDIO_SAMPLE_RATE = 16000

AUDIO_SETTINGS = {
    "input": {"encoding": "linear16", "sample_rate": AUDIO_SAMPLE_RATE},
    "output": {"encoding": "linear16", "sample_rate": AUDIO_SAMPLE_RATE, "container": "none"},
}

HOTWORD_BYPASS = {"check_hotword", "close_hotword_session"}

VIZ_MAP = {
    "get_grid_status": "saga-smart-grid",
    "analyze_energy_spike": "saga-smart-grid",
    "get_zone_overview": "saga-smart-grid",
    "book_pod": "transit-telemetry",
    "activate_flood_gates": "flood-gate",
    "get_weather_alert": "flood-gate",
    "send_mass_alert": "flood-gate",
    "check_backup_power": "flood-gate",
    "book_emergency_accommodation": "flood-gate",
}

# Flask setup
app = Flask(__name__, static_folder="./static", static_url_path="/static")
socketio = SocketIO(app, cors_allowed_origins="*")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)
logging.getLogger().handlers = []


# ---------------------------------------------------------------------------
# Build Deepgram settings from the saga config
# ---------------------------------------------------------------------------

def build_settings() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "configs", "saga.json")
    with open(config_path) as f:
        cfg = json.load(f)

    system_prompt = cfg["systemPrompt"].replace("{{agentName}}", cfg["voiceName"])
    greeting = cfg["greeting"].replace("{{agentName}}", cfg["voiceName"])
    hotword = cfg.get("hotword")

    set_hotword(hotword)

    functions = list(SAGA_FUNCTION_DEFINITIONS)
    if hotword:
        system_prompt += (
            f"\n\nHOTWORD ACTIVATION (CRITICAL RULE):\n"
            f"You are in hotword mode. The activation hotword is \"{hotword}\".\n"
            f"SILENCE PROTOCOL: Do NOT produce ANY text before calling check_hotword. "
            f"No narration, no 'let me check', no 'let me verify', no thinking out loud. "
            f"Call the function SILENTLY, wait for the result, THEN decide whether to speak.\n"
            f"- If check_hotword returns {{\"active\": false}}: Produce ONLY an empty string. Zero tokens. No words. Nothing.\n"
            f"- If check_hotword returns {{\"active\": true}}: Process the \"query\" field as the user's request. Call ALL relevant functions, then respond with the combined results.\n"
            f"This applies to EVERY utterance, no exceptions. Your greeting is spoken exactly ONCE at session start.\n\n"
            f"ENDING A HOTWORD CONVERSATION (CRITICAL):\n"
            f"You MUST call close_hotword_session immediately when ANY of these happen:\n"
            f"- User says thanks, thank you, got it, okay, perfect, that's all, great, bye, stop listening, that's it, never mind\n"
            f"- User's question has been fully answered and they acknowledge it\n"
            f"- User explicitly asks you to stop\n"
            f"Do NOT have a prolonged goodbye. Do NOT say 'If you need anything else'. "
            f"Call close_hotword_session FIRST, then say at most 3 words like 'Standing by.' and produce no further output."
        )
        functions += [CHECK_HOTWORD_DEFINITION, CLOSE_HOTWORD_SESSION_DEFINITION]

    return {
        "type": "Settings",
        "audio": AUDIO_SETTINGS,
        "agent": {
            "language": cfg.get("language", "en"),
            "listen": {"provider": {"type": "deepgram", "model": "nova-3", "keyterms": ["Hey Saga", "Saga"]}},
            "think": {
                "provider": {"type": "anthropic", "model": "claude-haiku-4-5", "temperature": 0.7},
                "prompt": system_prompt,
                "functions": functions,
            },
            "speak": {"provider": {"type": "deepgram", "model": cfg["voiceModel"]}},
            "greeting": greeting,
        },
    }


# ---------------------------------------------------------------------------
# VoiceAgent (browser-audio only)
# ---------------------------------------------------------------------------

class VoiceAgent:
    def __init__(self):
        self.mic_audio_queue = asyncio.Queue()
        self.speaker = None
        self.ws = None
        self.is_running = False
        self.loop = None
        self._greeting_done = False  # True after first user utterance; gates output suppression

    def set_loop(self, loop):
        self.loop = loop

    async def setup(self):
        api_key = os.environ.get("DEEPGRAM_API_KEY")
        if not api_key:
            logger.error("DEEPGRAM_API_KEY not set")
            return False
        logger.info(f"Connecting to Deepgram Voice Agent API...")
        try:
            self.ws = await websockets.connect(
                VOICE_AGENT_URL,
                extra_headers={"Authorization": f"Token {api_key}"},
            )
            settings = build_settings()
            logger.info(f"Connected. Sending settings ({len(settings['agent']['think']['functions'])} functions)")
            await self.ws.send(json.dumps(settings))
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            return False

    async def _handle_hotword_activation(self, result):
        """Handle hotword activation: emit state and inject filler on fresh activation."""
        if not result.get("active"):
            return
        socketio.emit("hotword_state", {"state": "active"})
        if result.get("freshly_activated"):
            filler = get_random_filler()
            logger.info(f"Injecting filler: {filler}")
            await self.ws.send(json.dumps({
                "type": "InjectAgentMessage",
                "message": filler,
            }))
            socketio.emit("show_viz", {"svg": "saga-loading"})

    async def sender(self):
        try:
            first_chunk = True
            while self.is_running:
                data = await self.mic_audio_queue.get()
                if self.ws and data:
                    if first_chunk:
                        logger.info(f"Sending first audio chunk to Deepgram: {len(data)} bytes")
                        first_chunk = False
                    await self.ws.send(data)
        except Exception as e:
            logger.error(f"Sender error: {e}")

    async def receiver(self):
        try:
            self.speaker = Speaker()
            last_user_transcript = ""
            with self.speaker:
                async for message in self.ws:
                    if isinstance(message, str):
                        msg = json.loads(message)
                        msg_type = msg.get("type")

                        if msg_type == "UserStartedSpeaking":
                            self.speaker.stop()

                        elif msg_type == "ConversationText":
                            role = msg.get("role")
                            if role == "user":
                                self._greeting_done = True
                                last_user_transcript = msg.get("content", "")
                            # Suppress assistant text when hotword not active (after greeting)
                            if role == "assistant" and self._greeting_done and not is_conversation_active():
                                logger.info(f"Suppressed: {msg.get('content', '')[:60]}")
                                continue
                            socketio.emit("conversation_update", msg)

                        elif msg_type == "FunctionCallRequest":
                            functions = msg.get("functions", [])
                            fn = functions[0]
                            fn_name = fn["name"]
                            fn_id = fn["id"]
                            params = json.loads(fn.get("arguments", "{}"))

                            logger.info(f"Function: {fn_name}({params})")

                            # Server-side hotword gate: if conversation not active
                            # and the LLM skipped check_hotword, auto-check the
                            # last transcript before blocking
                            if fn_name not in HOTWORD_BYPASS and not is_conversation_active():
                                if last_user_transcript:
                                    auto_result = await check_hotword({"transcript": last_user_transcript})
                                    if auto_result.get("active"):
                                        logger.info(f"Auto-activated hotword from transcript: {last_user_transcript[:50]}")
                                        await self._handle_hotword_activation(auto_result)

                                if not is_conversation_active():
                                    logger.info(f"BLOCKED {fn_name}: hotword not active")
                                    await self.ws.send(json.dumps({
                                        "type": "FunctionCallResponse",
                                        "id": fn_id,
                                        "name": fn_name,
                                        "content": json.dumps({"error": "BLOCKED. Hotword not active. Do not speak."}),
                                    }))
                                    continue

                            func = FUNCTION_MAP.get(fn_name)
                            if func:
                                result = await func(params)
                            else:
                                result = {"error": f"Unknown function: {fn_name}"}

                            # Emit hotword state changes to frontend
                            if fn_name == "check_hotword":
                                if result.get("active"):
                                    await self._handle_hotword_activation(result)
                                else:
                                    self.speaker.stop()  # Kill any leaked audio
                            elif fn_name == "close_hotword_session":
                                socketio.emit("hotword_state", {"state": "listening"})

                            # Emit visualization for SAGA functions
                            viz = VIZ_MAP.get(fn_name)
                            if viz:
                                socketio.emit("show_viz", {"svg": viz})

                            await self.ws.send(json.dumps({
                                "type": "FunctionCallResponse",
                                "id": fn_id,
                                "name": fn_name,
                                "content": json.dumps(result),
                            }))

                            # Push state update to frontend after any function call
                            socketio.emit("city_state_update", get_city_state())

                        elif msg_type == "Welcome":
                            logger.info(f"Deepgram session established: {msg.get('session_id')}")
                            socketio.emit("agent_ready")

                        elif msg_type == "Error":
                            logger.error(f"Deepgram error: {msg}")

                        else:
                            logger.info(f"Deepgram: {msg_type}")

                    elif isinstance(message, bytes):
                        # Suppress audio when hotword not active (after greeting)
                        if self._greeting_done and not is_conversation_active():
                            continue
                        await self.speaker.play(message)

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Deepgram WebSocket closed: {e}")
        except Exception as e:
            logger.error(f"Receiver error: {e}")

    async def keep_alive(self):
        while self.is_running:
            await asyncio.sleep(8)
            if self.is_running and self.ws and not self.ws.closed:
                try:
                    await self.ws.send(json.dumps({"type": "KeepAlive"}))
                except Exception:
                    break

    async def run(self):
        if not await self.setup():
            return
        self.is_running = True
        try:
            await asyncio.gather(self.sender(), self.receiver(), self.keep_alive())
        except Exception as e:
            logger.error(f"Run error: {e}")
        finally:
            self.is_running = False
            if self.ws:
                await self.ws.close()


# ---------------------------------------------------------------------------
# Speaker (browser output via SocketIO)
# ---------------------------------------------------------------------------

class Speaker:
    def __init__(self):
        self._queue = None
        self._thread = None
        self._stop = None

    def __enter__(self):
        self._queue = janus.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._play_loop, daemon=True)
        self._thread.start()

    def __exit__(self, *args):
        self._stop.set()
        self._thread.join()

    def _play_loop(self):
        seq = 0
        while not self._stop.is_set():
            try:
                data = self._queue.sync_q.get(True, 0.05)
                socketio.emit("audio_output", {
                    "audio": data,
                    "sampleRate": AUDIO_SAMPLE_RATE,
                    "seq": seq,
                })
                seq += 1
            except queue.Empty:
                pass

    async def play(self, data):
        return await self._queue.async_q.put(data)

    def stop(self):
        if self._queue and self._queue.async_q:
            while not self._queue.async_q.empty():
                try:
                    self._queue.async_q.get_nowait()
                except Exception:
                    break
        if self._queue and hasattr(self._queue, "sync_q"):
            try:
                while True:
                    self._queue.sync_q.get_nowait()
            except queue.Empty:
                pass
        socketio.emit("stop_audio_output")


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/city-state")
def api_city_state():
    return jsonify(get_city_state())


@app.route("/api/reset", methods=["POST"])
def api_reset():
    data = reset_city_state()
    socketio.emit("city_state_update", data)
    return jsonify({"status": "reset"})


@app.route("/api/start", methods=["POST"])
def api_start():
    """Start the voice agent session (for testing without browser)."""
    global voice_agent, voice_agent_thread
    if voice_agent is not None:
        if not voice_agent.is_running or not voice_agent.ws or voice_agent.ws.closed:
            logger.info("Stale voice agent detected via API, cleaning up before restart")
            handle_stop()
        else:
            return jsonify({"error": "already running"}), 400
    reset_city_state()
    voice_agent = VoiceAgent()
    voice_agent_thread = threading.Thread(target=_run_agent, daemon=True)
    voice_agent_thread.start()
    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    """Stop the voice agent session (for testing without browser)."""
    global voice_agent
    if not voice_agent:
        return jsonify({"error": "not running"}), 400
    handle_stop()
    return jsonify({"status": "stopped"})


@app.route("/api/inject", methods=["POST"])
def api_inject():
    """Inject a user message into the voice agent session (for testing)."""
    text = request.json.get("text", "")
    if not text:
        return jsonify({"error": "text required"}), 400
    if not voice_agent or not voice_agent.is_running or not voice_agent.ws:
        return jsonify({"error": "no active session"}), 400
    try:
        asyncio.run_coroutine_threadsafe(
            voice_agent.ws.send(json.dumps({
                "type": "InjectUserMessage",
                "content": text,
            })),
            voice_agent.loop,
        )
        return jsonify({"status": "injected", "text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# SocketIO handlers
# ---------------------------------------------------------------------------

voice_agent = None
voice_agent_thread = None


def _run_agent():
    global voice_agent
    try:
        loop = asyncio.DefaultEventLoopPolicy().new_event_loop()
        asyncio.set_event_loop(loop)
        voice_agent.set_loop(loop)
        try:
            loop.run_until_complete(voice_agent.run())
        except asyncio.CancelledError:
            pass
        finally:
            pending = asyncio.all_tasks(loop)
            for t in pending:
                t.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
    except Exception as e:
        logger.error(f"Agent thread error: {e}")


@socketio.on("connect")
def handle_connect():
    logger.info("Browser connected via SocketIO")


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Browser disconnected")
    handle_stop()


@socketio.on("start_voice_agent")
def handle_start(data=None):
    global voice_agent, voice_agent_thread
    logger.info(f"start_voice_agent received, data={data}")
    if voice_agent is not None:
        # If the old agent's WS is dead, clean it up instead of rejecting
        if not voice_agent.is_running or not voice_agent.ws or voice_agent.ws.closed:
            logger.info("Stale voice agent detected, cleaning up before restart")
            handle_stop()
        else:
            logger.warning("Voice agent already running, ignoring start")
            return

    reset_city_state()
    socketio.emit("city_state_update", get_city_state())

    voice_agent = VoiceAgent()
    voice_agent_thread = threading.Thread(target=_run_agent, daemon=True)
    voice_agent_thread.start()


@socketio.on("stop_voice_agent")
def handle_stop():
    global voice_agent
    logger.info("stop_voice_agent received")
    if not voice_agent:
        return
    voice_agent.is_running = False
    if voice_agent.loop and not voice_agent.loop.is_closed():
        try:
            if voice_agent.ws and not voice_agent.ws.closed:
                asyncio.run_coroutine_threadsafe(voice_agent.ws.close(), voice_agent.loop)
            for t in asyncio.all_tasks(voice_agent.loop):
                voice_agent.loop.call_soon_threadsafe(t.cancel)
        except Exception as e:
            logger.error(f"Stop error: {e}")
    voice_agent = None


@socketio.on("audio_data")
def handle_audio(data):
    global voice_agent
    if not voice_agent or not voice_agent.is_running:
        return

    audio_buffer = data.get("audio")
    if not audio_buffer:
        return

    if isinstance(audio_buffer, memoryview):
        audio_bytes = audio_buffer.tobytes()
    elif isinstance(audio_buffer, bytes):
        audio_bytes = audio_buffer
    else:
        try:
            audio_bytes = bytes(audio_buffer)
        except Exception:
            return

    if len(audio_bytes) % 2 != 0:
        audio_bytes = audio_bytes[:-1]

    if voice_agent.loop and not voice_agent.loop.is_closed():
        asyncio.run_coroutine_threadsafe(
            voice_agent.mic_audio_queue.put(audio_bytes),
            voice_agent.loop,
        )


if __name__ == "__main__":
    print("\n  SAGA Smart City Demo")
    print("  http://127.0.0.1:5000\n")
    socketio.run(app, debug=True)
