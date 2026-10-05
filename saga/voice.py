"""Live voice control: Deepgram speak settings plus the matching LLM writing style.

update_voice changes how Eve sounds mid-session with two Voice Agent messages:
UpdateSpeak (the TTS engine's voice, speed, expressivity) and UpdatePrompt (how
the think model writes, since punctuation and word choice drive delivery too).

Live-verified on agent.deepgram.com, 2026-10-05:
- UpdateSpeak with a v2 provider answers SpeakUpdated and takes effect on the
  next utterance (one line went 6.08s -> 4.72s at speed 1.4).
- An out-of-range expressivity (5) gets NO error event: Deepgram just closes
  the socket and the demo dies. So DO NOT pass model-authored values through;
  every value is clamped to the documented range here first.
- UpdatePrompt APPENDS to the prompt rather than replacing it, so each style
  directive says it supersedes the previous one.
"""

from dataclasses import dataclass, replace

# Flux TTS ranges, per developers.deepgram.com/docs/tts-voice-controls.
SPEED_MIN, SPEED_MAX, SPEED_STEP, SPEED_DEFAULT = 0.5, 1.5, 0.05, 1.0
EXPRESSIVITY_MIN, EXPRESSIVITY_MAX, EXPRESSIVITY_DEFAULT = -2, 2, 0

# Flux TTS English voices from GET https://api.deepgram.com/v2/models
# (snapshot 2026-10-05): name -> (accent, gender). A name Deepgram does not
# serve would kill the session, so the function schema offers only these.
FLUX_VOICES = {
    "alexis": ("American", "female"), "bree": ("American", "female"),
    "brittany": ("American", "female"), "brooke": ("American", "female"),
    "bruce": ("American", "male"), "cliff": ("American", "male"),
    "cole": ("American", "male"), "colin": ("British", "male"),
    "conor": ("Irish", "male"), "donovan": ("American", "male"),
    "drew": ("American", "male"), "elise": ("American", "female"),
    "gemma": ("British", "female"), "haley": ("American", "female"),
    "hannah": ("American", "female"), "heather": ("American", "female"),
    "jack": ("British", "male"), "kai": ("Singaporean", "male"),
    "kelsey": ("American", "female"), "kit": ("British", "male"),
    "maeve": ("Irish", "female"), "marcelo": ("Filipino", "male"),
    "marcus": ("American", "male"), "meena": ("Indian", "female"),
    "meghan": ("American", "female"), "miles": ("American", "male"),
    "naveen": ("Indian", "male"), "paige": ("American", "female"),
    "priya": ("Indian", "female"), "rufus": ("British", "male"),
    "sean": ("British", "male"), "sharon": ("Australian", "female"),
    "sienna": ("American", "female"), "tanner": ("British", "male"),
    "wade": ("American", "male"), "wes": ("American", "male"),
}

EXPRESSIVITY_LABELS = {-2: "very calm", -1: "calm", 0: "default", 1: "expressive", 2: "very expressive"}

# How the think model should WRITE at each level. Flux TTS reads punctuation
# and phrasing, so text style and the engine's expressivity move together.
STYLE_BY_EXPRESSIVITY = {
    -2: ("Write flat, plain, even sentences. Periods only: no exclamation marks, "
         "no dashes, no ellipses, no interjections. Neutral, understated word choice."),
    -1: ("Write measured, composed sentences. Avoid exclamation marks and "
         "interjections; prefer simple, precise wording."),
    0: ("Use your normal calm, confident register."),
    1: ("Write with warmth and color: vivid, concrete word choice, varied sentence "
        "rhythm, an occasional exclamation mark, and em dashes for emphasis."),
    2: ("Write animated and lively: exclamation marks, natural interjections "
        "(\"Oh!\", \"Good news!\"), vivid adjectives, em dashes and ellipses for "
        "dramatic beats, and punchy short sentences mixed with longer ones."),
}


@dataclass(frozen=True)
class VoiceSettings:
    model: str
    speed: float = SPEED_DEFAULT
    expressivity: int = EXPRESSIVITY_DEFAULT


def is_flux(model: str) -> bool:
    return model.startswith("flux-")


def speak_provider(voice: VoiceSettings) -> dict:
    """Voice Agent speak provider, routed by model-name prefix.

    Flux TTS (``flux-{voice}-{lang}``) is Speak v2, so DO NOT drop ``version``:
    the agent picks the TTS engine by it, and v1 is the Aura (``aura-*``) path.
    speed and expressivity are Flux controls, sent only on v2.
    """
    if not is_flux(voice.model):
        return {"type": "deepgram", "version": "v1", "model": voice.model}
    return {"type": "deepgram", "version": "v2", "model": voice.model,
            "speed": voice.speed, "expressivity": voice.expressivity}


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def apply_voice_update(current: VoiceSettings, params: dict) -> VoiceSettings:
    """New settings from model-authored params, every value forced into range.

    Unknown or unparseable values keep the current setting rather than raise,
    because a bad value must never reach Deepgram (see module docstring).
    """
    new = current
    if params.get("expressivity") is not None:
        try:
            level = round(float(params["expressivity"]))
            new = replace(new, expressivity=_clamp(level, EXPRESSIVITY_MIN, EXPRESSIVITY_MAX))
        except (TypeError, ValueError):
            pass
    if params.get("speed") is not None:
        try:
            speed = round(float(params["speed"]) / SPEED_STEP) * SPEED_STEP
            new = replace(new, speed=round(_clamp(speed, SPEED_MIN, SPEED_MAX), 2))
        except (TypeError, ValueError):
            pass
    voice = str(params.get("voice") or "").strip().lower()
    if voice in FLUX_VOICES:
        new = replace(new, model=f"flux-{voice}-en")
    return new


def style_directive(voice: VoiceSettings) -> str:
    """UpdatePrompt text. UpdatePrompt appends, so it must supersede earlier ones."""
    return (
        f"VOICE STYLE UPDATE (supersedes every earlier VOICE STYLE UPDATE): "
        f"expressivity is now {voice.expressivity} ({EXPRESSIVITY_LABELS[voice.expressivity]}). "
        f"{STYLE_BY_EXPRESSIVITY[voice.expressivity]} "
        f"All other style rules still apply, including keeping replies to 1-3 sentences."
    )


def voice_summary(voice: VoiceSettings) -> dict:
    """What the dashboard card shows and the model hears back. Rows flash on change."""
    name = voice.model.removeprefix("flux-").removesuffix("-en")
    accent, gender = FLUX_VOICES.get(name, ("", ""))
    return {
        "message": "UpdateSpeak + UpdatePrompt",
        "provider": f"deepgram · speak {'v2 (Flux TTS)' if is_flux(voice.model) else 'v1 (Aura)'}",
        "model": voice.model,
        "voice": f"{name.title()} ({accent} {gender})".strip() if accent else name.title(),
        "speed": f"{voice.speed:.2f}x",
        "expressivity": f"{voice.expressivity:+d} ({EXPRESSIVITY_LABELS[voice.expressivity]})",
        "llm_style": EXPRESSIVITY_LABELS[voice.expressivity],
    }


# Session-scoped tool (needs the live socket), so like the hotword tools it is
# added in build_settings and handled in VoiceAgent, not SAGA_FUNCTION_MAP.
UPDATE_VOICE_DEFINITION = {
    "name": "update_voice",
    "description": (
        "Change how YOU sound, live: expressiveness, speaking speed, or which voice. "
        "Call this whenever the user asks you to sound more or less expressive, "
        "animated, lively, emotional, calm, flat or monotone, to talk faster or "
        "slower, or to switch to a different voice or accent. It really "
        "reconfigures the Deepgram text-to-speech engine and your writing style; "
        "never just claim you will sound different without calling it. Values are "
        "absolute: 'a bit more expressive' means one step above the current "
        "expressivity (start at 0), 'much faster' about +0.25 speed. Pass only "
        "the fields that change."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "expressivity": {
                "type": "integer",
                "enum": list(range(EXPRESSIVITY_MIN, EXPRESSIVITY_MAX + 1)),
                "description": "-2 very calm, -1 calm, 0 default, 1 expressive, 2 very expressive.",
            },
            "speed": {
                "type": "number",
                "description": f"Speech rate multiplier, {SPEED_MIN} to {SPEED_MAX}; 1.0 is normal.",
            },
            "voice": {
                "type": "string",
                "enum": sorted(FLUX_VOICES),
                "description": "Voice name. " + "; ".join(
                    f"{n}: {a} {g}" for n, (a, g) in sorted(FLUX_VOICES.items())
                ),
            },
        },
    },
}

VOICE_CONTROL_PROMPT = (
    "\n\nVOICE CONTROL (CRITICAL RULE):\n"
    "You can change your own voice live with update_voice. Whenever the user asks "
    "you to sound more or less expressive, animated, calm or flat, to speak faster "
    "or slower, or to use a different voice or accent, call update_voice FIRST, then "
    "confirm in one short sentence written in the NEW style. Never merely promise to "
    "sound different. When a VOICE STYLE UPDATE is appended to these instructions, "
    "follow the latest one for word choice and punctuation in every later reply. "
    "update_voice already puts the Deepgram voice config on the dashboard, so do "
    "NOT also call update_dashboard for a voice change."
)
