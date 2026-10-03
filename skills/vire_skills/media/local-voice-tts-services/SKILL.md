---
name: local-voice-tts-services
description: "Use when configuring Piper speech output or an optional HTTP TTS service."
version: 1.0.0
author: Vire Shorette
license: MIT
---

# Local voice and TTS

The included Piper path uses a local binary. Set `PIPER_MODEL` to a licensed ONNX voice and choose an audio output device for the machine. Run `scripts/voice_stack_check.py` before the live loop. No custom operator voice is required.

An HTTP TTS bridge is optional and not shipped here. If you build one, configure its base URL with `TTS_URL`, use a health endpoint appropriate to that server, and keep it on loopback unless remote access is secured. Do not send text containing secrets to an untrusted TTS endpoint.
