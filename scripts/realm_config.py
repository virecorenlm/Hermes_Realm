"""Portable configuration shared by the standalone Realm scripts."""

import os
from pathlib import Path


def realm_home() -> Path:
    override = os.environ.get("HERMES_REALM_HOME")
    if override:
        return Path(override).expanduser()
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_home / "hermes-realm"


def realm_path(*parts: str) -> Path:
    return realm_home().joinpath(*parts)


def service_url(name: str, default: str) -> str:
    return os.environ.get(name, default).rstrip("/")


OLLAMA_URL = service_url("OLLAMA_URL", "http://127.0.0.1:11434")
QDRANT_URL = service_url("QDRANT_URL", "http://127.0.0.1:6333")
N8N_URL = service_url("N8N_URL", "http://127.0.0.1:5678")
REDIS_URL = service_url("REDIS_URL", "redis://127.0.0.1:6379")
TTS_URL = os.environ.get("TTS_URL", "")
