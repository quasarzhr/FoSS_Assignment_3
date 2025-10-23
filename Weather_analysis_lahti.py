import requests
import pandas as pd
import matplotlib.pyplot as plt
import json
from datetime import datetime

LAT, LON = 60.98, 25.66
DATE = "2025-10-23"
JSON_FILE = "lahti_weather_23.json"
PNG_FILE = "lahti_weather_chart.png"

def fetch_hourly_ms(lat=LAT, lon=LON):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,wind_speed_10m,relative_humidity_2m",
        "start_date": DATE,
        "end_date": DATE,
        "timezone": "Europe/Helsinki",
        "wind_speed_unit": "ms",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    hourly = data.get("hourly", {})
    if not hourly:
        raise RuntimeError("API returned no 'hourly' data. Check parameters or API availability.")

    df = pd.DataFrame(hourly)
    if "time" not in df.columns:
        raise RuntimeError("Hourly data has no 'time' column.")
    df["time"] = pd.to_datetime(df["time"])

    rename_map = {
        "temperature_2m": "Temperature (°C)",
        "wind_speed_10m": "Wind Speed (m/s)",
        "relative_humidity_2m": "Humidity (%)",
    }
    df.rename(columns=rename_map, inplace=True)

    units = data.get("hourly_units", {})
    ws_unit = units.get("wind_speed_10m", "m/s")

    if "Wind Speed (m/s)" not in df.columns:
        if "wind_speed_10m" in df.columns:
            df["Wind Speed (m/s)"] = df["wind_speed_10m"]
        else:
            raise RuntimeError("No wind speed field found in hourly data.")

    if ws_unit.lower() in ["km/h", "kmh", "kph"]:
        df["Wind Speed (m/s)"] = df["Wind Speed (m/s)"] / 3.6
    elif ws_unit.lower() in ["kn", "knot", "knots"]:
        df["Wind Speed (m/s)"] = df["Wind Speed (m/s)"] * 0.514444

    return df

def summarize_and_plot(df: pd.DataFrame):
    use_cols = ["Temperature (°C)", "Wind Speed (m/s)", "Humidity (%)"]
    missing = [c for c in use_cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing expected columns: {missing}")

    summary = df[use_cols].agg(["mean", "min", "max"]).round(2)
    print("\n===== Weather Summary for Lahti, Finland (24h, hourly) =====\n")
    print(summary)

    mean_ws = summary.loc["mean", "Wind Speed (m/s)"]
    if mean_ws > 12:
        print("\n[WARN] Average wind speed > 12 m/s — this is unusually high for surface wind.")
        print("       Please double-check if you really want surface wind. The script already forced m/s and surface model.")
        print("       If you still see this, it might be a stormy day indeed, or try a different model: 'icon_seamless'.")

    records = df[["time"] + use_cols].copy()
    records["time"] = records["time"].astype(str)
    json_data = records.to_dict(orient="records")
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    plt.figure(figsize=(10, 5))
    plt.plot(df["time"], df["Temperature (°C)"], label="Temperature (°C)", marker="o")
    plt.plot(df["time"], df["Wind Speed (m/s)"], label="Wind Speed (m/s)", marker="s")
    plt.title("Lahti Weather: Temperature and Wind Speed\nUnits: °C and m/s")
    plt.xlabel("Time (Europe/Helsinki)")
    plt.ylabel("Value")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("lahti_weather_chart.png", dpi=300)
    plt.show()

if __name__ == "__main__":
    df_hourly = fetch_hourly_ms()
    summarize_and_plot(df_hourly)