# Smart Hawker — คู่มือ Deploy

## แนะนำ Hosting

| Platform | แผน | ราคา | เหมาะกับ |
|----------|-----|------|---------|
| **PythonAnywhere** | Hacker | $5/เดือน | Demo / พัฒนา — ง่ายที่สุด |
| **Render** | Starter | $7/เดือน | Production — Postgres + disk ถาวร |
| **Railway** | Hobby | $5/เดือน | Production — คล้าย Render |

> **แนะนำ**: PythonAnywhere Hacker สำหรับ demo / ทดสอบกับลูกค้า ใช้งานง่ายที่สุด ไม่ต้องตั้ง Dockerfile  
> สำหรับ production จริง → Render (Postgres + persistent disk สำหรับ uploads)

---

## สร้าง ZIP ก่อน Deploy

```powershell
# รันใน PowerShell จาก root ของโปรเจกต์
.\scripts\make_deploy_zip.ps1
```

ไฟล์ `smart-hawker-deploy.zip` จะถูกสร้างใน parent folder

---

## PythonAnywhere — ขั้นตอนครบ

### 1. สมัครและเข้าระบบ

1. ไปที่ [pythonanywhere.com](https://www.pythonanywhere.com) → สมัคร Hacker ($5/เดือน)
2. เข้า Dashboard → เปิด **Bash console**

### 2. อัปโหลดไฟล์

**วิธี A — ผ่าน Files tab (แนะนำ):**
- ไปที่ tab **Files** → กด **Upload a file** → เลือก `smart-hawker-deploy.zip`
- ใน Bash console:
```bash
cd ~
mkdir smart-hawker
unzip smart-hawker-deploy.zip -d smart-hawker
cd smart-hawker
```

**วิธี B — ผ่าน git (ถ้ามี repo):**
```bash
git clone https://github.com/YOUR_USERNAME/smart-hawker.git
cd smart-hawker
```

### 3. สร้าง Virtual Environment

```bash
cd ~/smart-hawker
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. ตั้งค่า Environment Variables

ไปที่ tab **Web** → ส่วน **Environment variables** (หรือสร้างไฟล์ `.env`)

```bash
# ใน Bash console — สร้าง .env
cat > .env << 'EOF'
SECRET_KEY=<สร้างด้วย: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_CODE_HASH=<สร้างด้วย: python -c "import hashlib; print(hashlib.sha256(b'รหัสผ่านของคุณ').hexdigest())">
DATABASE_URL=sqlite:///smart_hawker.db
SMS_PROVIDER=console
PROMPTPAY_ID=0812345678
IDENTITY_PROVIDER=mock
SESSION_COOKIE_SECURE=1
EOF
```

### 5. ตั้งค่า Web App

ไปที่ tab **Web** → กด **Add a new web app**:
- Framework: **Manual configuration** (not Flask)
- Python version: **3.12**
- Source code: `/home/YOUR_USERNAME/smart-hawker`
- Working directory: `/home/YOUR_USERNAME/smart-hawker`

**WSGI file** — กด edit ที่ WSGI configuration file แล้วแทนที่ทั้งหมดด้วย:

```python
import sys, os
sys.path.insert(0, '/home/YOUR_USERNAME/smart-hawker')
os.chdir('/home/YOUR_USERNAME/smart-hawker')

from dotenv import load_dotenv
load_dotenv('/home/YOUR_USERNAME/smart-hawker/.env')

from app import app as application
```

**Virtualenv path**: `/home/YOUR_USERNAME/smart-hawker/venv`

### 6. Static Files Mapping

ใน tab **Web** → ส่วน **Static files**:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOUR_USERNAME/smart-hawker/static/` |

### 7. Initialize Database

```bash
cd ~/smart-hawker
source venv/bin/activate
python -c "from app import app; from extensions import db; app.app_context().__enter__(); db.create_all()"
# หรือถ้าต้องการข้อมูลตัวอย่าง:
python seed.py
```

### 8. Reload และทดสอบ

ไปที่ tab **Web** → กด **Reload** → เปิด `https://YOUR_USERNAME.pythonanywhere.com`

---

## Gotchas (สิ่งที่ต้องรู้)

### Free tier บล็อก outbound HTTP
PythonAnywhere free tier อนุญาต HTTP ออกไปได้แค่โดเมนที่ whitelist ไว้  
**Hacker plan ($5) ไม่มีข้อจำกัดนี้** — SMS, ThaiID OAuth, Nominatim ทำงานได้ปกติ

### SQLite + Uploads — อยู่รอดข้าม Reload
- `smart_hawker.db` เก็บในโฟลเดอร์โปรเจกต์ — **ไม่หายเมื่อ reload**
- `static/uploads/` เก็บในโฟลเดอร์โปรเจกต์ — **ไม่หายเมื่อ reload**
- แต่ถ้า **replace source code** ทั้งหมดให้ backup ไฟล์เหล่านี้ก่อน

### SESSION_COOKIE_SECURE=1 บังคับ HTTPS
PythonAnywhere ให้ HTTPS อัตโนมัติ ตั้งค่านี้ได้เลย  
ถ้าทดสอบบน localhost ให้เปลี่ยนเป็น `SESSION_COOKIE_SECURE=0`

### Database Migrations
แอปมี `_auto_migrate()` ที่รันอัตโนมัติตอนเริ่ม Flask  
ถ้า upgrade version ใหม่แค่ reload — ไม่ต้อง migrate เอง

### ADMIN_CODE_HASH ต้องตั้งก่อน login admin
ถ้าไม่ตั้ง server จะยังรันได้แต่ login admin จะ fail ทุกครั้ง  
สร้างด้วย:
```python
import hashlib
print(hashlib.sha256(b"รหัสผ่านของคุณ").hexdigest())
```

---

## Production บน Render (สำหรับ scale)

1. สร้าง [render.com](https://render.com) account
2. New → **Web Service** → เลือก repo (หรืออัปโหลดด้วย render.yaml)
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Environment variables: ตั้งเหมือน `.env` ด้านบน + `DATABASE_URL=postgresql://...`
6. Add a **PostgreSQL** database → copy connection string เป็น `DATABASE_URL`
7. Add a **Disk** (persistent volume) → mount ที่ `/opt/render/project/src/static/uploads`

```bash
# requirements.txt — ต้องมี gunicorn
gunicorn>=21.0
```

---

## Checklist ก่อน go-live

- [ ] `SECRET_KEY` เป็น random hex 32 bytes — ไม่ใช่ default
- [ ] `ADMIN_CODE_HASH` ตั้งแล้ว
- [ ] `SESSION_COOKIE_SECURE=1` (HTTPS เท่านั้น)
- [ ] `SMS_PROVIDER` ตั้งเป็น `twilio` หรือ `thaibulksms` (ไม่ใช่ `console`)
- [ ] `PROMPTPAY_ID` ตั้งเป็นเบอร์จริง
- [ ] ทดสอบ OTP flow ครบ
- [ ] Backup `.env` ไว้ที่ปลอดภัย (ไม่ใน git)
