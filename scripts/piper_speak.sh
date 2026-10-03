#!/bin/bash
# Piper TTS wrapper — synthesizes text and plays through PipeWire (HDPI speakers)
TEXT="${1:-Hello, this is your local agent speaking.}"
MODEL="${PIPER_MODEL:?Set PIPER_MODEL to an installed Piper ONNX voice}"
OUT="/tmp/piper_spoken.wav"

echo "$TEXT" | piper --model "$MODEL" --output_file "$OUT" 2>&1 && \
pw-play "$OUT" 2>&1
