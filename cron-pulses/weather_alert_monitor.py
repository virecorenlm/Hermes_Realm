#!/usr/bin/env python3
"""
Weather Alert Monitor — Detects prime musky fishing conditions
Scans for falling barometer, pre-frontal conditions, temperature swings.
"""

import requests
import os
import time
import json
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from realm_config import realm_path

STORAGE = realm_path("alerts")
STORAGE.mkdir(parents=True, exist_ok=True)

HOURLY_URL = os.environ.get("NWS_HOURLY_URL", "")

def analyze_conditions():
    if not HOURLY_URL:
        raise ValueError("Set NWS_HOURLY_URL to your local forecast/hourly endpoint")
    headers = {"User-Agent": os.environ.get("WEATHER_USER_AGENT", "HermesRealmExample/1.0")}
    
    # Retry with exponential backoff for transient NWS outages
    r = None
    for attempt in range(1, 4):
        try:
            r = requests.get(HOURLY_URL, headers=headers, timeout=30)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(2 ** attempt)
    
    if r is None or r.status_code != 200:
        raise ConnectionError(f"NWS API unreachable (status={r.status_code if r else 'no response'}). Service may be down.")
    
    try:
        data = r.json()
    except Exception:
        raise ConnectionError(f"NWS API returned invalid JSON. Service may be down.")
    
    hourly = data["properties"]["periods"][:12]  # Next 12 hours
    
    alerts = []
    
    # Check for falling barometer (prime musky trigger)
    pressures = [h.get("barometricPressure", {}).get("value", 101325) for h in hourly]
    if len(pressures) >= 3:
        current_pa = pressures[0]
        later_pa = pressures[-3]
        drop_hpa = (current_pa - later_pa) / 100  # hPa
        
        if drop_hpa > 3.0:
            alerts.append(f"🚨 FALLING BAROMETER: Dropping {drop_hpa:.1f} hPa over next 12h")
            alerts.append("   → MUSKY WILL BE ACTIVE. Fish now!")
        elif drop_hpa > 1.5:
            alerts.append(f"⚠️ Barometer falling {drop_hpa:.1f} hPa. Good conditions.")
    
    # Check for storms/wind shifts
    wind_directions = [h.get("windDirection", "N") for h in hourly]
    wind_speeds = []
    for h in hourly:
        ws = h.get("windSpeed", "0 mph")
        try:
            wind_speeds.append(int(ws.split()[0]))
        except:
            wind_speeds.append(0)
    
    if wind_speeds and max(wind_speeds) > 25:
        alerts.append(f"🌬️ Heavy winds ({max(wind_speeds)} mph) expected. May trigger aggressive bite before front.")
    
    # Check precipitation
    precip_hours = [h for h in hourly if h.get("probabilityOfPrecipitation", {}).get("value", 0) > 50]
    if precip_hours:
        first_rain = precip_hours[0]
        alerts.append(f"🌧️ Rain expected at {first_rain['startTime'][11:16]}. Pre-frontal bite window!")
    
    # Temperature swing
    temps = [h.get("temperature", 0) for h in hourly]
    if temps and max(temps) - min(temps) > 15:
        alerts.append(f"🌡️ Big temp swing: {min(temps)}°F → {max(temps)}°F. Unstable = active fish.")
    
    return alerts

def main():
    alerts = analyze_conditions()
    
    if not alerts:
        print("Conditions normal. No alerts.")
        return 0
    
    print("=" * 50)
    print(f"🎣 WEATHER ALERT | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    for alert in alerts:
        print(f"\n{alert}")
    print("\n" + "=" * 50)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
