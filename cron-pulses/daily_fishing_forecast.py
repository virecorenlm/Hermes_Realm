#!/usr/bin/env python3
"""
Hermes-ready fishing forecast script.
Prints forecast text to stdout — Hermes cron captures it and sends to Telegram.
"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(os.environ.get("FISHING_FORECAST_DIR", Path(__file__).resolve().parents[1] / "agents" / "fishing_forecast")).expanduser()))
from forecast import fetch_weather, get_musky_advice, format_report

try:
    weather = fetch_weather()
    data = get_musky_advice(weather)
    text = format_report(data)
    print(text)  # This goes to Telegram via Hermes cron
except Exception as e:
    print(f"❌ Forecast error: {e}")
