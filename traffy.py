"""Traffy Fondue integration — real public API + mock fallback dataset
ใช้ TRAFFY_PROVIDER=mock เพื่อบังคับใช้ mock (เช่น บน PythonAnywhere free tier)
"""
import json
import math
import logging
import os

logger = logging.getLogger(__name__)

TRAFFY_API = "https://publicapi.traffy.in.th/share/teamchadchart/getdata"

# Mock dataset — สมจริงแถวตลาดกรุงเทพฯ
MOCK_COMPLAINTS = [
    # จตุจักร (13.7991, 100.5502)
    {"lat": 13.7986, "lng": 100.5498, "type": "ทางเท้า",     "desc": "แผงลอยยึดทางเท้าหน้าตลาดนัด", "date": "2026-05-28"},
    {"lat": 13.7994, "lng": 100.5508, "type": "ความสะอาด",   "desc": "ขยะล้นถังหลังตลาด",            "date": "2026-06-01"},
    {"lat": 13.7989, "lng": 100.5493, "type": "การจราจร",    "desc": "รถค้าขายจอดขวางทางออก",        "date": "2026-06-05"},
    {"lat": 13.7999, "lng": 100.5515, "type": "ทางเท้า",     "desc": "ร่มแผงทะลุเกินเขตอนุญาต",      "date": "2026-06-08"},
    # คลองเตย (13.7215, 100.5566)
    {"lat": 13.7212, "lng": 100.5560, "type": "ทางเท้า",     "desc": "ทางเท้าถูกครอบครองถาวร",       "date": "2026-06-02"},
    {"lat": 13.7221, "lng": 100.5572, "type": "ความสะอาด",   "desc": "น้ำทิ้งจากแผงไหลท่วมทางเท้า", "date": "2026-06-04"},
    {"lat": 13.7208, "lng": 100.5558, "type": "เสียง",       "desc": "เสียงดังจากแผงเพลง",           "date": "2026-06-09"},
    # ศรีนครินทร์ (13.6822, 100.6597)
    {"lat": 13.6819, "lng": 100.6592, "type": "ทางเท้า",     "desc": "แผงลอยบุกรุกทางเท้า 3 แผง",  "date": "2026-05-30"},
    {"lat": 13.6828, "lng": 100.6603, "type": "การจราจร",    "desc": "ที่จอดรถถูกแผงขายของรุกล้ำ",  "date": "2026-06-06"},
    # อมรพันธ์ (13.7899, 100.6213)
    {"lat": 13.7896, "lng": 100.6208, "type": "ทางเท้า",     "desc": "แผงกีดขวางทางเข้าออกซอย",     "date": "2026-06-03"},
    {"lat": 13.7904, "lng": 100.6220, "type": "ความสะอาด",   "desc": "เศษอาหารสะสมหลังปิดตลาด",     "date": "2026-06-07"},
    # นนทบุรี (13.8622, 100.5141)
    {"lat": 13.8618, "lng": 100.5136, "type": "ความสะอาด",   "desc": "ขยะจากตลาดล้นไปถนน",         "date": "2026-06-07"},
    # สีลม (13.7238, 100.5345)
    {"lat": 13.7234, "lng": 100.5340, "type": "ทางเท้า",     "desc": "พื้นที่สาธารณะถูกครอบครอง",  "date": "2026-06-05"},
    {"lat": 13.7242, "lng": 100.5350, "type": "ความสะอาด",   "desc": "แผงขายอาหารไม่มีถาดรองน้ำ",  "date": "2026-06-10"},
]


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def fetch_complaints_near(lat: float, lng: float, radius_km: float = 0.3) -> list[dict]:
    """ดึงเรื่องร้องเรียน Traffy Fondue ในรัศมีที่กำหนด
    ลอง live API ก่อน → fallback mock ถ้าล้มเหลว"""
    provider = os.environ.get("TRAFFY_PROVIDER", "auto")

    if provider != "mock":
        try:
            import urllib.request
            url = (f"{TRAFFY_API}?lat={lat}&lon={lng}"
                   f"&radius={radius_km}&count=30&type=&keyword=")
            req = urllib.request.Request(url, headers={"User-Agent": "SmartHawker/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            items = data.get("results") or data.get("data") or []
            if items:
                return [_normalize_live(item) for item in items[:30]]
        except Exception as exc:
            logger.debug("Traffy API unavailable (%s) — using mock", exc)

    return _mock_near(lat, lng, radius_km)


def _normalize_live(item: dict) -> dict:
    return {
        "lat":    float(item.get("lat") or item.get("latitude") or 0),
        "lng":    float(item.get("lng") or item.get("longitude") or 0),
        "type":   item.get("problem_type_fondue") or item.get("type") or "ร้องเรียน",
        "desc":   (item.get("description") or item.get("comment") or "")[:120],
        "date":   str(item.get("timestamp") or item.get("date") or "")[:10],
        "source": "live",
    }


def _mock_near(lat: float, lng: float, radius_km: float) -> list[dict]:
    return [
        {**c, "source": "mock"}
        for c in MOCK_COMPLAINTS
        if _haversine_km(lat, lng, c["lat"], c["lng"]) <= radius_km
    ]


def count_near(lat: float, lng: float, radius_km: float = 0.2) -> int:
    return len(fetch_complaints_near(lat, lng, radius_km))
