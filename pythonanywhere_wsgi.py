# ============================================================
# WSGI สำหรับ PythonAnywhere
# วิธีใช้: คัดลอกเนื้อหาทั้งไฟล์นี้ไปวางทับใน WSGI file ของ PythonAnywhere
# (แท็บ Web -> ลิงก์ "WSGI configuration file") แล้วแก้ YOURUSERNAME เป็นชื่อจริง
# ============================================================
import os
import sys

# 1) ชี้ไปที่โฟลเดอร์โปรเจกต์บน PythonAnywhere (แก้ YOURUSERNAME)
project = "/home/YOURUSERNAME/flask-app"
if project not in sys.path:
    sys.path.insert(0, project)

# 2) อ่านค่าจาก environment ของ PythonAnywhere
# ตั้งค่าผ่าน "Environment variables" ใน Dashboard หรือไฟล์ .env บน server
# ห้ามใส่ secret ตรงนี้ — ใช้ os.environ เท่านั้น

# ตรวจสอบ secret สำคัญ (หากไม่ตั้ง ระบบยังรันได้แต่จะ warning)
_missing = [k for k in ("SECRET_KEY", "ADMIN_CODE") if not os.environ.get(k)]
if _missing:
    import logging
    logging.warning("Smart Hawker WSGI: ตัวแปร %s ยังไม่ได้ตั้งค่า!", ", ".join(_missing))

# ค่า default ที่ปลอดภัยสำหรับ non-secret options
os.environ.setdefault("SMS_PROVIDER", "console")
os.environ.setdefault("ENABLE_QUICK_LOGIN", "0")   # ปิด quick-login บน production
os.environ.setdefault("PROMPTPAY_ID", "0812345678")
os.environ.setdefault("APP_NAME", "Smart Hawker")
os.environ.setdefault("DEFAULT_THEME", "light")
os.environ.setdefault("DEFAULT_LANG", "th")

# 3) โหลดแอป (PythonAnywhere ต้องการตัวแปรชื่อ application)
from app import app as application
