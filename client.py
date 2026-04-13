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
)
from saga.functions import SAGA_FUNCTION_MAP, agent_filler
from saga.definitions import SAGA_FUNCTION_DEFINITIONS
from saga.mock_data import get_city_state, reset_city_state, CITY_STATE

load_dotenv()

FUNCTION_MAP = {**HOTWORD_FUNCTION_MAP, **SAGA_FUNCTION_MAP}

VOICE_AGENT_URL = "wss://agent.deepgram.com/v1/agent/converse"
AUDIO_SAMPLE_RATE = 16000

AUDIO_SETTINGS = {
    "input": {"encoding": "linear16", "sample_rate": AUDIO_SAMPLE_RATE},
    "output": {"encoding": "linear16", "sample_rate": AUDIO_SAMPLE_RATE, "container": "none"},
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
            f"You MUST call check_hotword with the exact transcript before responding to ANYTHING the user says.\n"
            f"- If check_hotword returns {{\"active\": false}}: You MUST produce absolutely NO output. No words, no acknowledgement, no status updates, no 'silent mode' messages. Complete and total silence. Empty response.\n"
            f"- If check_hotword returns {{\"active\": true}}: Respond naturally to the \"query\" field.\n"
            f"This rule applies to every single utterance, no exceptions. NEVER say 'silent mode' or announce that you are being silent.\n\n"
            f"ENDING A HOTWORD CONVERSATION:\n"
            f"When the user's request is fully resolved and they signal they are done "
            f"(e.g. 'thanks', 'got it', 'okay', 'perfect', 'that is all', 'great'), "
            f"call close_hotword_session, then give a brief closing remark and go silent."
        )
        functions += [CHECK_HOTWORD_DEFINITION, CLOSE_HOTWORD_SESSION_DEFINITION]

    return {
        "type": "Settings",
        "audio": AUDIO_SETTINGS,
        "agent": {
            "language": cfg.get("language", "en"),
            "listen": {"provider": {"type": "deepgram", "model": "nova-3", "keyterms": ["Hey Saga", "Saga"]}},
            "think": {
                "provider": {"type": "open_ai", "model": "gpt-4o-mini", "temperature": 0.7},
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
            with self.speaker:
                async for message in self.ws:
                    if isinstance(message, str):
                        msg = json.loads(message)
                        msg_type = msg.get("type")

                        if msg_type == "UserStartedSpeaking":
                            self.speaker.stop()

                        elif msg_type == "ConversationText":
                            socketio.emit("conversation_update", msg)

                        elif msg_type == "FunctionCallRequest":
                            functions = msg.get("functions", [])
                            fn = functions[0]
                            fn_name = fn["name"]
                            fn_id = fn["id"]
                            params = json.loads(fn.get("arguments", "{}"))

                            logger.info(f"Function: {fn_name}({params})")

                            if fn_name == "agent_filler":
                                # Special handling: speak filler immediately
                                result = await agent_filler(self.ws, params)
                                inject_msg = result["inject_message"]
                                fn_response = result["function_response"]

                                # Send function response first
                                await self.ws.send(json.dumps({
                                    "type": "FunctionCallResponse",
                                    "id": fn_id,
                                    "name": fn_name,
                                    "content": json.dumps(fn_response),
                                }))
                                # Then inject the filler so it's spoken immediately
                                logger.info(f"Injecting filler: {inject_msg['message']}")
                                await self.ws.send(json.dumps(inject_msg))
                                continue

                            func = FUNCTION_MAP.get(fn_name)
                            if func:
                                result = await func(params)
                            else:
                                result = {"error": f"Unknown function: {fn_name}"}

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


@socketio.on("start_voice_agent")
def handle_start(data=None):
    global voice_agent, voice_agent_thread
    logger.info(f"start_voice_agent received, data={data}")
    if voice_agent is not None:
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
