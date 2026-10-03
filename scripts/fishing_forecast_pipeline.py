#!/usr/bin/env python3
"""
Optional Daily Fishing Forecast Pipeline
Run via: FISHING_FORECAST_DIR=/path/to/forecast python3 scripts/fishing_forecast_pipeline.py
Output: stdout = forecast text (captured by cron for Telegram delivery)
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(os.environ.get("FISHING_FORECAST_DIR", Path(__file__).resolve().parents[1] / "agents" / "fishing_forecast")).expanduser()))

from forecast import main as forecast_main

def main():
    # Run forecast generation
    result = forecast_main()
    return result

if __name__ == "__main__":
    sys.exit(main())
