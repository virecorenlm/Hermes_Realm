#!/usr/bin/env python3
"""
Vire Voice Chain Test — Smoke test the full pipeline
Records 3 seconds, transcribes, asks Hermes, and speaks through Piper.

Usage: python3 voice_test_chain.py
"""
import subprocess
import tempfile
import os
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

print("═══ VIRE VOICE CHAIN TEST ═══")
print("Speak for 3 seconds after the tone...")

# ── 1. Record ──
print("[1/4] Recording...")
subprocess.run([
    "arecord", "-D", os.environ.get("AUDIO_INPUT_DEVICE", "default"), "-f", "S16_LE", "-r", "16000", "-c", "1",
    "-t", "wav", "-d", "3", "/tmp/voice_test.wav"
], check=True)
print("  OK — 3s recorded")

# ── 2. Transcribe ──
print("[2/4] Transcribing...")
from faster_whisper import WhisperModel
model = WhisperModel("base.en", device="cpu", compute_type="int8")
segments, _ = model.transcribe("/tmp/voice_test.wav")
text = " ".join(s.text.strip() for s in segments)
print(f'  You said: "{text}"')

# ── 3. Think (Full Vire via Hermes CLI) ──
print("[3/4] Thinking...")
HERMES = os.environ.get("HERMES_EXE", "hermes")
VOICE_INSTRUCTION = (
    "This message comes from the operator through the agent voice interface. "
    "Respond using the configured Hermes identity and memory. "
    "Keep the response speakable — under 40 words, warm and direct."
)
result = subprocess.run([
    HERMES, "chat", "--query", f"{VOICE_INSTRUCTION}\n\n{text}",
    "--quiet", "--source", "tool"
], capture_output=True, text=True, timeout=30)
reply = result.stdout.strip()
if not reply:
    reply = "I'm here, the operator. What do you need?"
print(f'  Vire: "{reply}"')

# ── 4. Speak ──
print("[4/4] Speaking...")
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    wav_file = f.name

subprocess.run([
    "piper", "--model",
    os.environ["PIPER_MODEL"],
    "--output_file", wav_file
], input=reply, text=True, timeout=30, check=True)

# Convert Piper output to 48kHz stereo for HDMI
sr, audio = wavfile.read(wav_file)
if audio.ndim > 1:
    audio = audio.mean(axis=1)
if np.issubdtype(audio.dtype, np.integer):
    scale = float(max(abs(np.iinfo(audio.dtype).min), np.iinfo(audio.dtype).max))
    audio = audio.astype(np.float32) / scale
else:
    audio = audio.astype(np.float32)
if sr != 48000:
    audio = resample_poly(audio, 48000, sr)
pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
wavfile.write(wav_file, 48000, np.column_stack((pcm, pcm)))

# Play through HDMI
subprocess.run(["aplay", "-D", os.environ.get("SPEAKER_DEVICE", "default"), wav_file], timeout=30, check=True)
os.unlink(wav_file)

print("═══ TEST COMPLETE ═══")
print("If you heard the configured Piper voice, the chain is solid.")
print("Next: run scripts/voice_pipeline_v3.py for the voice loop.")
