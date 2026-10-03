#!/usr/bin/env python3
"""Non-invasive Vire voice stack diagnostics.

Checks paths, Python imports, Piper WAV generation, Whisper transcription on the
Piper-generated WAV, OpenWakeWord model loading, and audio device visibility.
Does not play audio through speakers and does not start the live mic loop.
"""
from pathlib import Path
import hashlib
import importlib
import os
import subprocess
import sys

from realm_config import realm_path
ENV_PATH = realm_path("secrets", "voice.env")


def load_env(path=ENV_PATH):
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=kwargs.pop("timeout", 60), **kwargs)


def check_path(label, env_name):
    value = os.environ.get(env_name, "")
    p = Path(value).expanduser() if value else None
    ok = bool(p and p.exists())
    print(f"{label}: {'OK' if ok else 'MISSING'} {p or env_name}")
    return ok


def main():
    load_env()
    ok = True
    print("== Vire voice stack check ==")
    print(f"env: {ENV_PATH} exists={ENV_PATH.exists()}")

    path_checks = [
        ("Piper model", "PIPER_MODEL"),
        ("Piper config", "PIPER_CONFIG_PATH"),
        ("Wake word model", "WAKEWORD_MODEL"),
    ]
    if os.environ.get("WHISPER_BACKEND", "whisper_cpp").lower() in {"whisper_cpp", "whisper-cpp", "cpp"}:
        path_checks.extend([
            ("Whisper binary", "WHISPER_BIN"),
            ("Whisper model", "WHISPER_MODEL"),
        ])
    else:
        path_checks.append(("Whisper small int8 ONNX dir", "WHISPER_SMALL_INT8_ONNX_DIR"))

    for label, env in path_checks:
        ok = check_path(label, env) and ok

    print("\n== Python imports ==")
    for mod in ["numpy", "sounddevice", "faster_whisper", "openwakeword"]:
        try:
            m = importlib.import_module(mod)
            print(f"{mod}: OK {getattr(m, '__version__', '')}")
        except Exception as e:
            print(f"{mod}: ERROR {e!r}")
            ok = False

    print("\n== Audio devices ==")
    try:
        import sounddevice as sd
        print(sd.query_devices())
    except Exception as e:
        print(f"sounddevice query failed: {e!r}")
        ok = False

    print("\n== Piper generate WAV ==")
    out_wav = realm_path("state", "voice_stack_check.wav")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    piper = os.environ.get("PIPER_BIN", "piper")
    if not os.environ.get("PIPER_MODEL"):
        print("PIPER_MODEL is not configured; skipping synthesis")
        return 1
    piper_cmd = [
        piper,
        "--model", os.environ["PIPER_MODEL"],
        "--config", os.environ.get("PIPER_CONFIG_PATH", ""),
        "--output_file", str(out_wav),
    ]
    # Remove empty --config value if missing.
    piper_cmd = [x for x in piper_cmd if x]
    result = run(piper_cmd, input="Vire voice stack check. Piper generated this test file.\n", timeout=90)
    print(f"piper rc={result.returncode}")
    if result.stderr.strip():
        print(result.stderr.strip()[-800:])
    if result.returncode != 0 or not out_wav.exists():
        ok = False
    else:
        digest = hashlib.sha256(out_wav.read_bytes()).hexdigest()[:12]
        print(f"wav: {out_wav} bytes={out_wav.stat().st_size} sha256_12={digest}")

    print("\n== Whisper transcribe generated WAV ==")
    backend = os.environ.get("WHISPER_BACKEND", "whisper_cpp").lower()
    if backend in {"faster_whisper", "faster-whisper", "small_int8"}:
        try:
            from faster_whisper import WhisperModel
            model_name = os.environ.get("FASTER_WHISPER_MODEL", "small")
            compute_type = os.environ.get("FASTER_WHISPER_COMPUTE_TYPE", "int8")
            print(f"backend=faster_whisper model={model_name} compute_type={compute_type}")
            model = WhisperModel(model_name, device="cpu", compute_type=compute_type)
            segments, info = model.transcribe(str(out_wav), beam_size=5, language="en", task="transcribe", vad_filter=True)
            text = " ".join(seg.text.strip() for seg in segments).strip()
            print("transcript:", text)
            if not text:
                ok = False
        except Exception as e:
            print(f"faster-whisper: ERROR {e!r}")
            ok = False
    else:
        txt_base = "/tmp/vire_voice_stack_check_transcript"
        whisper_cmd = [
            os.environ["WHISPER_BIN"],
            "-m", os.environ["WHISPER_MODEL"],
            "-f", str(out_wav),
            "--no-prints",
            "--output-txt",
            "--output-file", txt_base,
        ]
        result = run(whisper_cmd, timeout=120)
        print(f"whisper rc={result.returncode}")
        transcript = Path(txt_base + ".txt")
        if transcript.exists():
            print("transcript:", transcript.read_text(errors="ignore").strip())
        else:
            ok = False
            print(result.stderr.strip()[-800:])

    print("\n== Voice command router ==")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from voice_command_router import route_voice_command
        for phrase in ["hey jarvis run hailo", "hey harvis check qdrant", "jarvis run kali defensive"]:
            reply = route_voice_command(phrase)
            print(f"{phrase!r}: {'MATCH' if reply else 'NO_MATCH'} {reply or ''}")
            ok = bool(reply) and ok
    except Exception as e:
        print(f"voice_command_router: ERROR {e!r}")
        ok = False

    print("\n== OpenWakeWord model load ==")
    try:
        from openwakeword.model import Model
        model = Model(wakeword_model_paths=[os.environ["WAKEWORD_MODEL"]])
        names = list(getattr(model, "models", {}).keys())
        print("openwakeword: OK", names)
    except Exception as e:
        print(f"openwakeword: ERROR {e!r}")
        ok = False

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
