"""แหล่งความจริงเดียว (single source of truth) สำหรับค่าที่ใช้ทั้งฝั่ง Python และ JS
เพื่อ "กัน mismatch" — ค่าพวกนี้ถูกส่งเข้า template เป็น window.CONFIG ให้ JS ใช้ค่าเดียวกัน
(ดู base.html + app.py context_processor)
"""

ROLES = ["SELLER", "MARKET_OWNER", "ADMIN"]
OWNER_TYPES = ["GOV", "PRIVATE"]
RENT_TYPES = ["DAILY", "WEEKLY", "MONTHLY"]
BOOKING_STATUS = ["PENDING", "CONFIRMED", "CANCELLED"]
VERIFICATION_STATUS = ["UNVERIFIED", "PENDING", "VERIFIED", "REJECTED"]
PAYMENT_STATUS = ["PENDING", "PAID", "FAILED"]
LOT_STATUS = ["AVAILABLE", "BOOKED", "CLOSED"]
NOTIFICATION_TYPES = ["BOOKING_CONFIRMED", "BOOKING_CANCELLED", "MESSAGE", "PROMO", "SYSTEM"]
AUDIT_ACTIONS = [
    "DELETE_USER", "DELETE_MARKET", "DELETE_LOT", "DELETE_REVIEW",
    "CREATE_USER", "SUSPEND_USER", "VERIFY_MARKET", "FEATURE_MARKET",
    "CHANGE_ADMIN_CODE", "EXPORT_CSV", "ADMIN_LOGIN",
]

OWNER_TYPE_LABEL = {
    "GOV":     "เปิดโดยภาครัฐ",
    "PRIVATE": "โดยเอกชน/บุคคลธรรมดา",
}

ROLE_LABEL = {
    "SELLER":       "ผู้ขาย (พ่อค้าแม่ค้า)",
    "MARKET_OWNER": "เจ้าของตลาด / ผู้ให้เช่าพื้นที่",
    "ADMIN":        "ผู้ดูแลระบบ",
}

ROLE_LABEL_SHORT = {
    "SELLER":       "ผู้ขาย",
    "MARKET_OWNER": "เจ้าของตลาด",
    "ADMIN":        "แอดมิน",
}

RENT_TYPE_LABEL = {
    "DAILY":   "รายวัน",
    "WEEKLY":  "รายสัปดาห์",
    "MONTHLY": "รายเดือน",
}

BOOKING_STATUS_LABEL = {
    "PENDING":   "รอชำระเงิน",
    "CONFIRMED": "ยืนยันแล้ว",
    "CANCELLED": "ยกเลิก",
}

PAYMENT_STATUS_LABEL = {
    "PENDING": "รอชำระ",
    "PAID":    "ชำระแล้ว",
    "FAILED":  "ล้มเหลว",
}

LOT_STATUS_LABEL = {
    "AVAILABLE": "ว่าง",
    "BOOKED":    "จองแล้ว",
    "CLOSED":    "ปิด",
}

VERIFICATION_STATUS_LABEL = {
    "UNVERIFIED": "ยังไม่ยืนยัน",
    "PENDING":    "รอการยืนยัน",
    "VERIFIED":   "ยืนยันแล้ว",
    "REJECTED":   "ถูกปฏิเสธ",
}

# UI color tokens per status (for JS)
BOOKING_STATUS_COLOR = {
    "PENDING":   {"bg": "#fff7ed", "ink": "#c2410c"},
    "CONFIRMED": {"bg": "#ecfdf5", "ink": "#047857"},
    "CANCELLED": {"bg": "#fef2f2", "ink": "#b91c1c"},
}

# 7 accent themes ที่ผู้ใช้เลือกได้ (hue, saturation) — blossom เป็นค่าเริ่มต้น
ACCENT_THEMES = {
    "blossom": {"h": 340, "s": "85%", "label": "ชมพูสด (ค่าเริ่มต้น)"},
    "amber":   {"h": 36,  "s": "82%", "label": "อำพัน"},
    "teal":    {"h": 168, "s": "76%", "label": "เขียวมรกต"},
    "indigo":  {"h": 235, "s": "78%", "label": "คราม"},
    "rose":    {"h": 345, "s": "78%", "label": "กุหลาบ"},
    "violet":  {"h": 262, "s": "70%", "label": "ม่วง"},
    "emerald": {"h": 142, "s": "72%", "label": "เขียวมรกตเข้ม"},
}

# ข้อความ i18n (TH/EN) — เพิ่มที่นี่แล้วไหลไปยัง JS ผ่าน CLIENT_CONFIG.STRINGS
STRINGS = {
    "search":      {"th": "ค้นหา",       "en": "Search"},
    "map":         {"th": "แผนที่",       "en": "Map"},
    "bookings":    {"th": "การจอง",      "en": "Bookings"},
    "chat":        {"th": "แชท",         "en": "Chat"},
    "profile":     {"th": "โปรไฟล์",     "en": "Profile"},
    "settings":    {"th": "ตั้งค่า",      "en": "Settings"},
    "favorites":   {"th": "รายการโปรด",  "en": "Favorites"},
    "owner":       {"th": "พื้นที่ของฉัน", "en": "My Spaces"},
    "space":       {"th": "พื้นที่",      "en": "Space"},
    "spaces":      {"th": "พื้นที่ค้าขาย","en": "Spaces"},
    "add_space":   {"th": "เพิ่มพื้นที่ใหม่", "en": "Add Space"},
    "manage_space":{"th": "จัดการพื้นที่", "en": "Manage Space"},
    "admin":       {"th": "แดชบอร์ด",    "en": "Dashboard"},
    "login":       {"th": "เข้าสู่ระบบ", "en": "Login"},
    "register":    {"th": "สมัครสมาชิก", "en": "Register"},
    "logout":      {"th": "ออกจากระบบ",  "en": "Logout"},
    "loading":     {"th": "กำลังโหลด...", "en": "Loading..."},
    "error":       {"th": "เกิดข้อผิดพลาด", "en": "Something went wrong"},
    "no_data":     {"th": "ไม่มีข้อมูล", "en": "No data"},
    "save":        {"th": "บันทึก",      "en": "Save"},
    "cancel":      {"th": "ยกเลิก",      "en": "Cancel"},
    "delete":      {"th": "ลบ",          "en": "Delete"},
    "edit":        {"th": "แก้ไข",       "en": "Edit"},
    "confirm":     {"th": "ยืนยัน",      "en": "Confirm"},
    "back":        {"th": "กลับ",        "en": "Back"},
    "submit":      {"th": "ส่ง",         "en": "Submit"},
    "book":        {"th": "จอง",         "en": "Book"},
    "price_from":  {"th": "เริ่ม",       "en": "From"},
    "available":   {"th": "ว่าง",        "en": "Available"},
    "lots":        {"th": "ล็อก",        "en": "lots"},
    "reviews":     {"th": "รีวิว",       "en": "reviews"},
    "navigate":    {"th": "นำทาง",       "en": "Navigate"},
    "theme_dark":  {"th": "มืด",         "en": "Dark"},
    "theme_light": {"th": "สว่าง",       "en": "Light"},
    "lang_th":     {"th": "ไทย",         "en": "Thai"},
    "lang_en":     {"th": "อังกฤษ",      "en": "English"},
    "senior_mode": {"th": "โหมดผู้สูงอายุ", "en": "Senior Mode"},
}

# รวมค่าที่อยากส่งให้ JS ใช้ (window.CONFIG)
CLIENT_CONFIG = {
    "ROLES":                ROLES,
    "OWNER_TYPES":          OWNER_TYPES,
    "OWNER_TYPE_LABEL":     OWNER_TYPE_LABEL,
    "RENT_TYPES":           RENT_TYPES,
    "RENT_TYPE_LABEL":      RENT_TYPE_LABEL,
    "ROLE_LABEL":           ROLE_LABEL,
    "ROLE_LABEL_SHORT":     ROLE_LABEL_SHORT,
    "BOOKING_STATUS":       BOOKING_STATUS,
    "BOOKING_STATUS_LABEL": BOOKING_STATUS_LABEL,
    "BOOKING_STATUS_COLOR": BOOKING_STATUS_COLOR,
    "PAYMENT_STATUS_LABEL": PAYMENT_STATUS_LABEL,
    "LOT_STATUS":           LOT_STATUS,
    "LOT_STATUS_LABEL":     LOT_STATUS_LABEL,
    "ACCENT_THEMES":              ACCENT_THEMES,
    "VERIFICATION_STATUS":        VERIFICATION_STATUS,
    "VERIFICATION_STATUS_LABEL":  VERIFICATION_STATUS_LABEL,
    "STRINGS":                    STRINGS,
}
