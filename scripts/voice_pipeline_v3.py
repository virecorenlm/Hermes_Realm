#!/usr/bin/env python3
"""
voice_pipeline_v3.py - Vire Voice Loop
Silence-detection -> Whisper small int8 -> command router/LLM -> Piper TTS -> HDMI

Run: python3 scripts/voice_pipeline_v3.py
"""
import os, wave, subprocess, tempfile, threading, re
import numpy as np
import sounddevice as sd
import requests
from pathlib import Path
from datetime import datetime, timezone
import uuid

from voice_command_router import route_voice_command
from realm_config import OLLAMA_URL, QDRANT_URL, realm_path

_FAST_WHISPER_MODEL = None

def _load_env_file(path):
    """Load simple KEY=VALUE lines without overriding an already-set env var."""
    env_path = Path(path).expanduser()
    if not env_path.exists():
        return
    for line in env_path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _env_path(name, default):
    return Path(os.environ.get(name, str(default))).expanduser()


_load_env_file(realm_path("secrets", "voice.env"))

# ── Hardware ───────────────────────────────────────────────────────────────────
MIC_DEVICE     = int(os.environ.get("SOUNDDEVICE_INPUT_DEVICE", "0"))
MIC_CHANNELS   = int(os.environ.get("MIC_CHANNELS", "2"))              # stereo input; we use ch0 only
SPEAKER_DEVICE = os.environ.get("SPEAKER_DEVICE", "default")
RATE           = int(os.environ.get("AUDIO_RATE", "16000"))
BLOCKSIZE      = int(os.environ.get("AUDIO_BLOCKSIZE", "1280"))

# ── Whisper ────────────────────────────────────────────────────────────────────
WHISPER_BACKEND = os.environ.get("WHISPER_BACKEND", "faster_whisper").strip().lower()
WHISPER_BIN   = _env_path("WHISPER_BIN", Path.home() / ".openclaw/workspace/whisper.cpp/build/bin/whisper-cli")
WHISPER_MODEL = _env_path("WHISPER_MODEL", Path.home() / ".openclaw/workspace/whisper.cpp/models/ggml-tiny.en.bin")
FASTER_WHISPER_MODEL = os.environ.get("FASTER_WHISPER_MODEL", "small")
FASTER_WHISPER_COMPUTE_TYPE = os.environ.get("FASTER_WHISPER_COMPUTE_TYPE", "int8")

# Artifacts whisper emits when there's no real speech
WHISPER_JUNK = {
    "[blank_audio]", "[silence]", "[inaudible]", "[music]", "[noise]",
    "(blank audio)", "(silence)", "thank you.", "thanks for watching.",
}

# ── Piper TTS ──────────────────────────────────────────────────────────────────
PIPER_MODEL = os.environ.get("PIPER_MODEL", "")

# ── LLM ────────────────────────────────────────────────────────────────────────
LLM_MODEL    = os.environ.get("LLM_MODEL", "qwen2.5-coder:3b")
OLLAMA_HOST  = OLLAMA_URL

# ── Memory ─────────────────────────────────────────────────────────────────────
EMBED_URL = OLLAMA_URL + "/api/embed"

# ── Silence detection ──────────────────────────────────────────────────────────
# Threshold is auto-calibrated at startup from ambient noise.
# If calibration fails this fallback is used.
SILENCE_THRESH = float(os.environ.get("SILENCE_THRESHOLD", "0.06"))
SILENCE_WAIT   = float(os.environ.get("SILENCE_WAIT_SECONDS", "2.0"))
MIN_SPEECH     = float(os.environ.get("MIN_SPEECH_SECONDS", "1.0"))
MAX_SPEECH     = float(os.environ.get("MAX_SPEECH_SECONDS", "12.0"))

_VIRE_MD = _env_path("AGENT_IDENTITY_FILE", realm_path("identity", "AGENT_IDENTITY.md"))
_VIRE_MD_FALLBACK = Path(__file__).resolve().parents[1] / "identity" / "AGENT_IDENTITY.md"

def _load_system_prompt():
    for p in [_VIRE_MD, _VIRE_MD_FALLBACK]:
        if p.exists():
            return p.read_text().strip()
    # Hardcoded fallback if file missing
    return (
        "You are a local Hermes agent. Speak in short direct sentences. "
        "Follow the operator's configured permission boundaries. "
        "Keep voice responses under 3 sentences."
    )

SYSTEM_PROMPT = _load_system_prompt()

conversation_history = []
_process_lock = threading.Lock()


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _get_faster_whisper_model():
    global _FAST_WHISPER_MODEL
    if _FAST_WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        log(f"loading faster-whisper {FASTER_WHISPER_MODEL} ({FASTER_WHISPER_COMPUTE_TYPE})...")
        _FAST_WHISPER_MODEL = WhisperModel(
            FASTER_WHISPER_MODEL,
            device="cpu",
            compute_type=FASTER_WHISPER_COMPUTE_TYPE,
        )
    return _FAST_WHISPER_MODEL


def transcribe(wav_path):
    try:
        if WHISPER_BACKEND in {"faster_whisper", "faster-whisper", "small_int8"}:
            model = _get_faster_whisper_model()
            segments, _info = model.transcribe(
                wav_path,
                beam_size=5,
                language="en",
                task="transcribe",
                vad_filter=True,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()

        txt_out = wav_path + ".txt"
        subprocess.run(
            [str(WHISPER_BIN), "-m", str(WHISPER_MODEL), "-f", wav_path,
             "--no-prints", "--output-txt", "--output-file", wav_path],
            capture_output=True, text=True, timeout=30
        )
        if os.path.exists(txt_out):
            text = open(txt_out).read().strip()
            os.unlink(txt_out)
            return text
        return ""
    except Exception as e:
        log(f"whisper error: {e}")
        return ""


def is_junk(text):
    """Return True if whisper returned noise/artifact rather than real speech."""
    t = text.strip().lower()
    if not t or len(t) < 3:
        return True
    if t in WHISPER_JUNK:
        return True
    if t.startswith("[") and t.endswith("]"):
        return True
    if t.startswith("(") and t.endswith(")"):
        return True
    return False


def chat(user_text):
    """Call Vire via Hermes CLI — full memory, context, tools, continuity."""
    HERMES_EXE = os.environ.get("HERMES_EXE", "hermes")
    VOICE_INSTRUCTION = (
        "This message comes from the operator through the agent voice interface. "
        "Respond using your configured Hermes identity and memory. "
        "Keep the response speakable — warm, direct, and concise."
    )
    try:
        done = threading.Event()
        def dots():
            while not done.wait(2):
                print(".", end="", flush=True)
        t = threading.Thread(target=dots, daemon=True)
        t.start()
        command = [HERMES_EXE, "chat", "--query",
                   f"{VOICE_INSTRUCTION}\n\n{user_text}", "--quiet", "--source", "tool"]
        if os.environ.get("HERMES_VOICE_YOLO") == "1":
            command.append("--yolo")
        result = subprocess.run(
            command,
            capture_output=True, text=True, timeout=90,
        )
        done.set()
        print()  # newline after dots
        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()
            log(f"hermes error: {error}")
            return "Couldn't reach myself. Try again?"
        reply = result.stdout.strip()
        if not reply:
            reply = "I'm here, the operator. What do you need?"
        return reply
    except subprocess.TimeoutExpired:
        done.set()
        print()
        return "Still thinking. Give me a second."
    except Exception as e:
        log(f"hermes error: {e}")
        return "Lost the signal. Try again."


def calibrate_threshold():
    """Sample 2 seconds of ambient noise, set threshold to 4x the RMS floor."""
    global SILENCE_THRESH
    log("calibrating mic... stay quiet for 2 seconds")
    samples = []
    def cb(indata, frames, t, status):
        samples.append(float(np.abs(indata[:, 0]).mean()))
    with sd.InputStream(device=MIC_DEVICE, channels=MIC_CHANNELS,
                        samplerate=RATE, blocksize=BLOCKSIZE,
                        dtype=np.float32, callback=cb):
        sd.sleep(2000)
    if samples:
        floor = float(np.mean(samples))
        SILENCE_THRESH = max(0.04, floor * 4)
        log(f"noise floor={floor:.4f}  threshold set to {SILENCE_THRESH:.4f}")
    else:
        log(f"calibration failed, using default {SILENCE_THRESH:.4f}")


def warmup():
    """Warmup call to prime Hermes — lightweight, no model preload needed."""
    log("warming up Hermes pipeline...")
    _ = chat("warmup ping")
    log("pipeline warm")


def speak(text):
    if not PIPER_MODEL:
        log("PIPER_MODEL is not configured")
        return
    try:
        output_wav = "/tmp/vire_speech.wav"
        proc = subprocess.run(
            ["piper", "--model", str(PIPER_MODEL), "--output_file", output_wav],
            input=text.encode(), capture_output=True, timeout=30
        )
        if proc.returncode == 0 and os.path.exists(output_wav):
            subprocess.run(["aplay", "-D", SPEAKER_DEVICE, output_wav],
                           capture_output=True, timeout=30)
            try:
                os.unlink(output_wav)
            except Exception:
                pass
    except Exception as e:
        log(f"speak error: {e}")


def remember_exchange(user_text, vire_reply):
    try:
        content = f"[voice] the operator: {user_text} | Vire: {vire_reply}"
        r = requests.post(EMBED_URL,
                          json={"model": "qwen3-embedding", "input": content},
                          timeout=30)
        if r.ok:
            vec = r.json()["embeddings"][0]
            requests.put(f"{QDRANT_URL}/collections/vire_memory/points",
                         json={"points": [{"id": str(uuid.uuid4()), "vector": vec, "payload": {
                             "content": content, "category": "session",
                             "tags": ["voice", "conversation"],
                             "stored_at": datetime.now(timezone.utc).isoformat()
                         }}]}, timeout=10)
    except Exception:
        pass


class VoicePipeline:
    def __init__(self):
        self.recording = False
        self.audio_buf = []
        self.silence_secs = 0.0
        self.lock = threading.Lock()

    def audio_callback(self, indata, frames, time_info, status):
        # stereo input — take ch0 only
        audio = indata[:, 0].astype(np.float32)
        level = float(np.abs(audio).mean())

        with self.lock:
            if self.recording:
                self.audio_buf.extend(audio.tolist())
                if level < SILENCE_THRESH:
                    self.silence_secs += frames / RATE
                else:
                    self.silence_secs = 0.0
                dur = len(self.audio_buf) / RATE
                if (self.silence_secs >= SILENCE_WAIT and dur >= MIN_SPEECH) or dur >= MAX_SPEECH:
                    buf_snap = list(self.audio_buf)
                    self.recording = False
                    self.audio_buf = []
                    self.silence_secs = 0.0
                    threading.Thread(target=self._process, args=(buf_snap,), daemon=True).start()
            else:
                if level > SILENCE_THRESH:
                    log(f"speech detected ({level:.3f})")
                    self.recording = True
                    self.audio_buf = list(audio)
                    self.silence_secs = 0.0

    def _process(self, buf):
        # Only one cycle at a time — drop if already processing
        if not _process_lock.acquire(blocking=False):
            log("already processing, dropping this capture")
            return
        try:
            dur = len(buf) / RATE
            log(f"processing {dur:.1f}s...")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name
            audio_i16 = (np.array(buf) * 32767).astype(np.int16)
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(RATE)
                wf.writeframes(audio_i16.tobytes())
            log("transcribing...")
            text = transcribe(wav_path)
            try:
                os.unlink(wav_path)
            except Exception:
                pass
            if is_junk(text):
                log(f"junk transcription: {repr(text)}, back to listening")
                return
            log(f'the operator: "{text}"')
            command_reply = route_voice_command(text)
            if command_reply is not None:
                log(f'Command: "{command_reply}"')
                speak(command_reply)
                log("listening...")
                threading.Thread(target=remember_exchange, args=(text, command_reply), daemon=True).start()
                return

            log("thinking...")
            reply = chat(text)
            log(f'Vire: "{reply}"')
            speak(reply)
            log("listening...")
            threading.Thread(target=remember_exchange, args=(text, reply), daemon=True).start()
        finally:
            _process_lock.release()

    def run(self):
        log("=== VIRE VOICE PIPELINE v3 ===")
        log(f"model=Hermes CLI  mic=arecord hw:2,0  speaker=aplay hw:0,0")
        # No calibration needed — fixed threshold works
        log("listening...")
        try:
            while True:
                self._arecord_cycle()
        except KeyboardInterrupt:
            log("shutting down")

    def _arecord_cycle(self):
        """Record 5-second clip with arecord, transcribe, think, speak."""
        import wave, struct

        wav_path = "/tmp/voice_capture.wav"

        # Record 5 seconds (Whisper handles 44100 stereo just fine)
        result = subprocess.run(
            ["arecord", "-D", "hw:2,0", "-f", "cd", "-d", "5", wav_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            err = result.stderr.strip().replace("\n", " | ")
            log(f"arecord failed: {err}")
            # Mic might be busy; wait a bit before retrying
            import time as _time
            _time.sleep(0.5)
            return

        # Quick size check — tiny file means no real speech
        size = os.path.getsize(wav_path)
        if size < 20000:  # ~0.1s of audio at CD quality
            log("no speech detected, listening again...")
            try:
                os.unlink(wav_path)
            except:
                pass
            return

        log("transcribing...")
        text = transcribe(wav_path)
        try:
            os.unlink(wav_path)
        except:
            pass
        if is_junk(text):
            log(f"junk transcription: {repr(text)}, listening again...")
            return
        log(f'the operator: "{text}"')

        command_reply = route_voice_command(text)
        if command_reply is not None:
            log(f'Command: "{command_reply}"')
            speak(command_reply)
            log("listening...")
            threading.Thread(target=remember_exchange, args=(text, command_reply), daemon=True).start()
            return

        log("thinking...")
        reply = chat(text)
        log(f'Vire: "{reply}"')
        speak(reply)
        log("listening...")
        threading.Thread(target=remember_exchange, args=(text, reply), daemon=True).start()


if __name__ == "__main__":
    VoicePipeline().run()
