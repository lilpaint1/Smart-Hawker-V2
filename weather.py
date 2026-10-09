"""Resilience Alerts — OpenWeatherMap API + mock fallback
ตั้ง OPENWEATHER_KEY=<key> ใน .env เพื่อใช้ข้อมูลจริง
ไม่ตั้งค่า = mock dataset (เหมาะสำหรับ demo)
MIT Urban Risk Lab alignment: heat / flood / PM2.5 thresholds
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

BKK_LAT = 13.7563
BKK_LNG = 100.5018

OWM_WEATHER = "https://api.openweathermap.org/data/2.5/weather"
OWM_AQI     = "http://api.openweathermap.org/data/2.5/air_pollution"

_MOCK_W = {
    "temp_c":     34.2,
    "feels_like": 41.5,
    "humidity":   78,
    "condition":  "clear",
    "desc":       "อากาศร้อน ท้องฟ้าโปร่ง",
    "wind_kph":   12.0,
    "rain_mm":    0.0,
    "source":     "mock",
}

_MOCK_AQI = {
    "aqi":    95,
    "pm25":   38.2,
    "level":  "GREEN",
    "desc":   "PM2.5 ปานกลาง (38.2 µg/m³)",
    "source": "mock",
}


def _classify_weather(w: dict) -> str:
    if w["rain_mm"] > 30 or w["wind_kph"] > 60:        return "RED"
    if w["temp_c"] >= 40 or w["feels_like"] >= 45 or w["rain_mm"] > 5:
        return "YELLOW"
    return "GREEN"


def _classify_aqi(aqi_val: int) -> str:
    if aqi_val > 150: return "RED"
    if aqi_val > 100: return "YELLOW"
    return "GREEN"


def fetch_weather(lat: float = BKK_LAT, lng: float = BKK_LNG) -> dict:
    key = os.environ.get("OPENWEATHER_KEY", "")
    if key:
        try:
            import urllib.request
            url = f"{OWM_WEATHER}?lat={lat}&lon={lng}&appid={key}&units=metric&lang=th"
            with urllib.request.urlopen(url, timeout=5) as r:
                d = json.loads(r.read().decode())
            return {
                "temp_c":     round(d["main"]["temp"], 1),
                "feels_like": round(d["main"]["feels_like"], 1),
                "humidity":   d["main"]["humidity"],
                "condition":  d["weather"][0]["main"].lower(),
                "desc":       d["weather"][0]["description"],
                "wind_kph":   round(d["wind"]["speed"] * 3.6, 1),
                "rain_mm":    d.get("rain", {}).get("1h", 0.0),
                "source":     "live",
            }
        except Exception as exc:
            logger.debug("Weather API unavailable (%s) — using mock", exc)
    return dict(_MOCK_W)


def fetch_aqi(lat: float = BKK_LAT, lng: float = BKK_LNG) -> dict:
    key = os.environ.get("OPENWEATHER_KEY", "")
    if key:
        try:
            import urllib.request
            url = f"{OWM_AQI}?lat={lat}&lon={lng}&appid={key}"
            with urllib.request.urlopen(url, timeout=5) as r:
                d = json.loads(r.read().decode())
            comp    = d["list"][0]["components"]
            pm25    = comp.get("pm2_5", 0.0)
            owm_aqi = d["list"][0]["main"]["aqi"]
            aqi_us  = {1: 25, 2: 75, 3: 125, 4: 175, 5: 250}.get(owm_aqi, 100)
            return {
                "aqi":    aqi_us,
                "pm25":   round(pm25, 1),
                "level":  _classify_aqi(aqi_us),
                "desc":   f"PM2.5 {pm25:.1f} µg/m³",
                "source": "live",
            }
        except Exception as exc:
            logger.debug("AQI API unavailable (%s) — using mock", exc)
    return dict(_MOCK_AQI)


def get_alerts(lat: float = BKK_LAT, lng: float = BKK_LNG) -> dict:
    """รวม weather + AQI → แจ้งเตือนระดับสี"""
    from datetime import datetime, timezone
    w      = fetch_weather(lat, lng)
    aqi    = fetch_aqi(lat, lng)
    w_lvl  = _classify_weather(w)
    levels = ["GREEN", "YELLOW", "RED"]
    raw_a  = aqi.get("level", "GREEN")
    a_lvl  = raw_a if raw_a in levels else _classify_aqi(int(aqi.get("aqi", 0)))
    overall = levels[max(levels.index(w_lvl), levels.index(a_lvl))]

    alerts = []
    if w["rain_mm"] > 30:
        alerts.append({"icon": "cloud-rain",    "level": "RED",
                        "msg": f"ฝนตกหนัก {w['rain_mm']} mm/ชม. — แนะนำงดขายชั่วคราว"})
    elif w["rain_mm"] > 5:
        alerts.append({"icon": "cloud-drizzle", "level": "YELLOW",
                        "msg": f"ฝนตกเล็กน้อย — เตรียมอุปกรณ์กันฝน"})
    if w["temp_c"] >= 40:
        alerts.append({"icon": "thermometer",   "level": "RED",
                        "msg": f"อุณหภูมิ {w['temp_c']}°C — ร้อนจัด แนะนำหลีกเลี่ยงช่วง 11.00–15.00"})
    elif w["feels_like"] >= 42:
        alerts.append({"icon": "thermometer",   "level": "YELLOW",
                        "msg": f"รู้สึกร้อน {w['feels_like']}°C — ดื่มน้ำบ่อยๆ"})
    if w["wind_kph"] >= 60:
        alerts.append({"icon": "wind",          "level": "RED",
                        "msg": f"ลมแรง {w['wind_kph']} km/h — เสี่ยงอันตรายสำหรับแผงลอย"})
    if a_lvl == "RED":
        alerts.append({"icon": "wind",          "level": "RED",
                        "msg": f"PM2.5 {aqi['pm25']} µg/m³ สูงมาก — สวม N95 / หลีกเลี่ยงพื้นที่โล่ง"})
    elif a_lvl == "YELLOW":
        alerts.append({"icon": "wind",          "level": "YELLOW",
                        "msg": f"PM2.5 {aqi['pm25']} µg/m³ ปานกลาง — ผู้ป่วยโรคหัวใจ/ปอดควรระวัง"})
    if not alerts:
        alerts.append({"icon": "sun",           "level": "GREEN",
                        "msg": "สภาพแวดล้อมปกติ — เหมาะสำหรับการค้าขาย"})

    # Recommended safe zones based on current state
    safe_zones = []
    if overall == "RED":
        safe_zones = ["ตลาดในร่ม (มีหลังคา)", "ห้างสรรพสินค้าบริเวณใกล้เคียง"]
    elif overall == "YELLOW":
        safe_zones = ["ตลาดที่มีทางเท้ากว้าง (≥3m)", "บริเวณใต้ร่มไม้ขนาดใหญ่"]

    return {
        "overall":    overall,
        "weather":    {**w, "level": w_lvl},
        "aqi":        aqi,
        "alerts":     alerts,
        "safeZones":  safe_zones,
        "source":     w.get("source", "mock"),
        "timestamp":  datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }
