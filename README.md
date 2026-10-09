# Smart Hawker

เว็บแอปสำหรับหาและจองพื้นที่ขายของของหาบเร่แผงลอย เชื่อมผู้ขายกับเจ้าของตลาดในระบบเดียว ผู้ขายค้นหาตลาดบนแผนที่ เลือกล็อก จองและจ่ายมัดจำผ่าน PromptPay ส่วนเจ้าของตลาดจัดการล็อกและการจองของตัวเอง

พัฒนาด้วย Flask + Jinja2 + vanilla JS/CSS ฐานข้อมูล SQLite

## ทำอะไรได้บ้าง

- **ผู้ขาย:** ค้นหาตลาดบนแผนที่ จองล็อก จ่ายมัดจำ 20% ผ่าน PromptPay QR ดูใบยืนยันการจอง (พิมพ์ได้) แชตกับเจ้าของตลาด บันทึกตลาดโปรด รีวิว และรับการแจ้งเตือน
- **เจ้าของตลาด:** ลงทะเบียนตลาด ปักหมุด จัดการล็อก ติดตามการจองและการชำระเงิน
- **แอดมิน:** จัดการผู้ใช้และตลาด ดู audit log ซ่อนรีวิวที่ไม่เหมาะสม
- **หน้าโปร่งใส (public):** อธิบายหลักการทำงานของระบบ
- **หน้าเจ้าหน้าที่ กทม. (อ่านอย่างเดียว):** มุมมองภาพรวมสำหรับหน่วยงานกำกับดูแล
- **Simulator:** หน้าจำลองสถานการณ์การจัดสรรล็อก
- สมัครและยืนยันตัวตนด้วย OTP ทาง SMS แบ่งสิทธิ์ 3 บทบาท (SELLER / MARKET_OWNER / ADMIN) รองรับภาษาไทยและธีมสว่าง/มืด

> ส่วนยืนยันตัวตน (KYC) และ SMS ในโหมดพัฒนาเป็นแบบจำลอง (`IDENTITY_PROVIDER=mock`, `SMS_PROVIDER=console`) OTP จะพิมพ์ใน terminal ไม่ได้ส่งจริง

## ทำงานอย่างไร

เบราว์เซอร์ขอหน้าจาก Flask (`app.py`) ซึ่งตรวจ session แล้วเรนเดอร์ template ส่วนข้อมูลทั้งหมดดึงผ่าน REST API (`api.py`) ที่ตอบ JSON รูปแบบเดียวกันทุก endpoint แล้วเก็บลง SQLite ผ่าน SQLAlchemy

ขั้นตอนการจองล็อก:

1. สมัครและยืนยัน OTP
2. ค้นหาตลาดและเลือกล็อก
3. ระบบสร้างการจองสถานะ PENDING พร้อมคำนวณมัดจำ 20%
4. ระบบสร้าง PromptPay QR ตามมาตรฐาน EMVCo ให้สแกนจ่าย
5. ยืนยันการจ่าย ระบบอัปเดตการชำระเงิน การจอง และสถานะล็อกพร้อมกันใน transaction เดียว

## เทคโนโลยี

| ส่วน | เครื่องมือ |
|---|---|
| Backend | Python, Flask 3.0, Flask-SQLAlchemy, gunicorn (production) |
| Frontend | Jinja2, CSS, JavaScript (ไม่ใช้เฟรมเวิร์ก) |
| ฐานข้อมูล | SQLite (ตั้ง `DATABASE_URL` เพื่อใช้ PostgreSQL ได้) |
| ชำระเงิน | PromptPay QR (`promptpay.py` สร้าง payload และ CRC16 เอง), qrcode, Pillow |
| แผนที่ | Leaflet, OpenStreetMap, Nominatim |
| ทดสอบ | Playwright |

จุดที่ออกแบบไว้: ค่า role/rentType เก็บชุดเดียวใน `constants.py` แล้วส่งให้ JS ใช้ร่วมกัน, OTP เก็บเป็น HMAC-SHA256 hash หมดอายุใน 5 นาที, สลับผู้ให้บริการ SMS ด้วย env โดยไม่แก้โค้ด, ใส่ security headers (X-Frame-Options, HSTS, Permissions-Policy), ใช้ ProxyFix เมื่ออยู่หลัง reverse proxy และมี auto-migrate เพิ่มคอลัมน์ใหม่ให้ฐานข้อมูลเดิมโดยไม่ต้องลบทิ้ง

## วิธีติดตั้ง

ต้องมี Python 3 และ git

```bash
git clone https://github.com/lilpaint1/Smart-Hawker-V2.git
cd Smart-Hawker-V2

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # แล้วแก้ค่าใน .env (อย่างน้อย SECRET_KEY)
python seed.py                  # สร้างข้อมูลตัวอย่าง
python app.py                   # เปิดที่ http://localhost:5000
```

ตอนพัฒนา OTP จะพิมพ์ออกทาง terminal ไม่ต้องมีบัญชี Twilio ถ้าอยากเข้าสู่ระบบแอดมิน ให้ตั้ง `ADMIN_CODE` ใน `.env` แล้วเข้าที่ `/admin/login`

รันแบบ production: `gunicorn "app:app" --bind 0.0.0.0:$PORT --workers 3` ดูรายละเอียดที่ [DEPLOY.md](DEPLOY.md)

## โครงสร้างโปรเจกต์

```
app.py          จุดเริ่มต้น ตั้งค่า และหน้าเว็บ (27 route)
api.py          REST API (Blueprint)
models.py       โมเดลฐานข้อมูล
constants.py    ค่ากลาง
helpers.py      ตัวช่วยตอบ JSON, ตรวจสิทธิ์, OTP
sms.py          ส่ง SMS
promptpay.py    สร้าง QR PromptPay
seed.py         ข้อมูลตัวอย่าง
templates/      หน้า HTML
static/         CSS และ JS
```

เอกสารเพิ่มเติม: [DESIGN.md](DESIGN.md) · [DEPLOY.md](DEPLOY.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## ผู้พัฒนา

`<ชื่อ>` · [GitHub](https://github.com/lilpaint1)
