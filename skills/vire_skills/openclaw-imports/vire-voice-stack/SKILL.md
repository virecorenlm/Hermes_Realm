---
name: vire-voice-stack
description: "Use when configuring or debugging the optional local Hermes Realm voice pipeline."
version: 1.0.0
author: Vire Shorette
license: MIT
metadata:
  hermes:
    tags: [voice, wake-word, whisper, piper, audio]
---

# Voice stack

The included `scripts/voice_pipeline_v3.py` demonstrates capture, Whisper transcription, Hermes CLI response, Piper speech, and optional Qdrant memory. `scripts/voice_command_router.py` handles a small allowlist of local diagnostics. Wake-word work remains experimental and may require a separate implementation.

Set `PIPER_MODEL` to a licensed ONNX voice and configure your own audio devices. Use `scripts/voice_stack_check.py` for diagnostics before running the live loop. `HERMES_EXE` selects the Hermes command when it is not on `PATH`. The optional `secrets/voice.env` belongs under `HERMES_REALM_HOME` and must remain private.

ALSA and PipeWire may compete for devices. Inspect your system's device list and choose a working capture/playback route. Do not assume a specific microphone, speaker, custom voice, or CPU architecture.
