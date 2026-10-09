# Smart Hawker

เว็บแอปสำหรับหาและจองพื้นที่ขายของของหาบเร่แผงลอย เชื่อมผู้ขายกับเจ้าของตลาดในระบบเดียว ผู้ขายค้นหาตลาดบนแผนที่ เลือกล็อก จองและจ่ายมัดจำผ่าน PromptPay ส่วนเจ้าของตลาดจัดการล็อกและการจองของตัวเอง

พัฒนาด้วย Flask + Jinja2 + vanilla JS/CSS ฐานข้อมูล SQLite

## ทำอะไรได้บ้าง

- **ผู้ขาย:** ค้นหาตลาดบนแผนที่ (ค้นด้วยชื่อ คลิกแผนที่ หรือใช้ GPS) จองล็อก จ่ายมัดจำ 20% ผ่าน PromptPay QR ดูสถานะการจองและการแจ้งเตือน
- **เจ้าของตลาด:** ลงทะเบียนตลาด ปักหมุด จัดการล็อก ติดตามการจองและการชำระเงิน
- **แอดมิน:** จัดการผู้ใช้และข้อมูลระบบ
- สมัครและยืนยันตัวตนด้วย OTP ทาง SMS แบ่งสิทธิ์ 3 บทบาท (SELLER / MARKET_OWNER / ADMIN)

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
| Backend | Python, Flask 3.0, Flask-SQLAlchemy |
| Frontend | Jinja2, CSS, JavaScript (ไม่ใช้เฟรมเวิร์ก) |
| ฐานข้อมูล | SQLite |
| ชำระเงิน | PromptPay QR (`promptpay.py` สร้าง payload และ CRC16 เอง), qrcode, Pillow |
| แผนที่ | Leaflet, OpenStreetMap, Nominatim |
| ทดสอบ | Playwright |

จุดที่ออกแบบไว้: ค่า role/rentType เก็บชุดเดียวใน `constants.py` แล้วส่งให้ JS ใช้ร่วมกัน, OTP เก็บเป็น HMAC-SHA256 hash หมดอายุใน 5 นาที, สลับผู้ให้บริการ SMS (console/Twilio) ด้วย env โดยไม่แก้โค้ด

## วิธีติดตั้ง

ต้องมี Python 3 และ git

```bash
git clone https://github.com/lilpaint1/Smart-Hawker-V2.git
cd Smart-Hawker-V2

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # แล้วแก้ค่าใน .env
python seed.py                  # สร้างข้อมูลตัวอย่าง
python app.py                   # เปิดที่ http://localhost:5000
```

ตอนพัฒนา SMS จะพิมพ์ OTP ออกทางหน้าจอ terminal (โหมด console) ไม่ต้องมีบัญชี Twilio

## โครงสร้างโปรเจกต์

```
app.py          เสิร์ฟหน้าและตั้งค่า
api.py          REST API
models.py       โมเดลฐานข้อมูล (9 ตาราง)
constants.py    ค่ากลาง
helpers.py      ตัวช่วยตอบ JSON, ตรวจสิทธิ์, OTP
sms.py          ส่ง SMS
promptpay.py    สร้าง QR PromptPay
seed.py         ข้อมูลตัวอย่าง
templates/      หน้า HTML (19 หน้า)
static/         CSS และ JS
```

เอกสารเพิ่มเติม: [DESIGN.md](DESIGN.md) · [DEPLOY.md](DEPLOY.md) · [SECURITY.md](SECURITY.md) · [CHANGELOG.md](CHANGELOG.md)

## ผู้พัฒนา

`<ชื่อ>` · [GitHub](https://github.com/lilpaint1)
