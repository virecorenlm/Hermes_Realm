# Voice capability

The reference pipeline in `scripts/voice_pipeline_v3.py` captures speech, transcribes with faster-whisper or whisper.cpp, routes a small allowlist of diagnostic commands, sends other requests to the configured Hermes CLI, and speaks through Piper. Configure `HERMES_EXE`, `PIPER_MODEL`, microphone and speaker device variables for your machine. `OLLAMA_URL` and `QDRANT_URL` support optional memory storage; remote services are optional.

Start with `python3 scripts/voice_stack_check.py` to inspect dependencies and devices. The voice script reads a private `secrets/voice.env` under `HERMES_REALM_HOME` if present. A custom voice is never required. Use an ONNX Piper model you are licensed to use and set `PIPER_MODEL=/path/to/voice-model.onnx`.

Wake-word and hardware routing remain experimental. The diagnostics and smoke chain require real audio devices and are not part of the offline test suite. The voice command router does not execute arbitrary transcribed shell text.
