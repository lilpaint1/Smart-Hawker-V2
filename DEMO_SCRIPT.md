# Smart Hawker — HacKaTech Demo Script (5 นาที)

> **Format**: 1 speaker · Slide/live demo สลับกัน  
> **Time target**: 5:00 นาที · เหลือ 30 วิ buffer ก่อน Q&A  

---

## INTRO — 0:00–0:30 (30 วินาที)

> "กรุงเทพฯ มีพ่อค้าแม่ขายข้างถนนกว่า 120,000 ราย  
> แต่การจัดสรรพื้นที่ขายของยังเป็น **กล่องดำ** — ไม่มีเกณฑ์ ไม่มีใครรู้ว่าใครได้ใครเสีย  
> Smart Hawker เปลี่ยนระบบนี้ให้ **โปร่งใส วัดได้ และเป็นธรรม**"

**Action**: เปิดหน้า `/` (landing page)

---

## 1. ปัญหาจริง — 0:30–1:00 (30 วินาที)

- **ปัญหา 1**: เจ้าหน้าที่ กทม. ไม่มีข้อมูล real-time — ตัดสินใจด้วย Excel รุ่นเก่า  
- **ปัญหา 2**: ผู้ค้ารายย่อย (กลุ่มเปราะบาง) ถูกกีดกันโดยไม่มีเหตุผล  
- **ปัญหา 3**: ทางเท้าถูกครอบครองเกินสิทธิ์ — Traffy Fondue มีร้องเรียนหลักพันเรื่อง  

**Action**: เปิด `/map` → เลือก Layer **"🟣 Traffy Fondue"** — แสดงจุดร้องเรียนบนแผนที่  
ชี้ weather banner (ถ้า mock shows YELLOW) — "แจ้งเตือนผู้ค้าก่อนอากาศแย่"

---

## 2. Solution Overview — 1:00–1:30 (30 วินาที)

> "Smart Hawker มีสามเสา: **Data** · **Algorithm** · **Transparency**"

| เสา | Feature |
|-----|---------|
| Data | Traffy Fondue + OpenWeatherMap + ZoneData |
| Algorithm | Fair Allocation Score + AI Optimizer (Greedy explainable) |
| Transparency | Public Ledger + QR Audit + Open Data API CC BY 4.0 |

---

## 3. Dashboard กทม. — 1:30–2:15 (45 วินาที)

**Action**: เปิด `/gov`

Point out:
1. **KPI Bar** → ดัชนีโปร่งใส XX/100 (live)
2. **อันดับความโปร่งใสต่อเขต** → ชี้เขตที่ได้อันดับ 1 (เขียว) กับอันดับท้าย (แดง)
3. **AI Optimizer** → กด "คำนวณ" → แสดง HIGH priority suggestions (เช่น SWITCH_TO_SCORING, TRAFFY_REVIEW)
4. **Allocation Trend** → ชี้ peak day

> "เจ้าหน้าที่เห็นปัญหาได้ทันที ไม่ต้องรอรายงาน"

---

## 4. Policy Simulator — 2:15–3:00 (45 วินาที)

**Action**: เปิด `/simulator`

Demo flow:
1. เลื่อน **ทางเท้า → 1.0m** → ความแออัดพุ่ง → Radar chart เปลี่ยนสี
2. เลื่อน **โควตารายย่อย → 50%** → ความเป็นธรรมขึ้น
3. ชี้ baseline badge **"ค่าเฉลี่ย กทม. (Live)"** — โหลดจาก API จริง ไม่ใช่ hardcode
4. ชี้ Before/After Radar chart

> "ทดสอบนโยบายก่อนประกาศใช้จริง — ไม่มี vendor lock-in"

---

## 5. Transparency + QR Audit — 3:00–3:45 (45 วินาที)

**Action**: เปิด `/transparency`

1. ชี้ column **วิธีจัดสรร** — SCORING / LOTTERY / MANUAL
2. คลิก **QR ⬛** บน record ใดก็ได้ → QR code popup
3. > "สแกน QR = ดูการจัดสรรนั้นทันที — ใครก็ตรวจสอบได้ไม่ต้องล็อกอิน"
4. เปิด URL `/api/open-data/allocations` → JSON สาธารณะ CC BY 4.0

---

## 6. Walk-in Inclusion — 3:45–4:15 (30 วินาที)

**Action**: เปิด `/owner` → กด **"Walk-in"**

> "เจ้าของตลาดลงทะเบียนแทนผู้ค้าที่ไม่มีสมาร์ตโฟน  
> ระบบสร้างบัญชี → จอง → พิมพ์ใบรับรอง A4 ได้เลย  
> **ไม่ทิ้งใครไว้ข้างหลัง**"

---

## 7. Close — 4:15–4:45 (30 วินาที)

> "Smart Hawker ไม่ใช่แค่ app จองล็อก  
> มันคือ **infrastructure ความเป็นธรรม** สำหรับ 120,000 คน  
> โปร่งใสตั้งแต่ต้นทาง — ตรวจสอบได้ทุก QR — เปิดข้อมูลให้นักวิจัยใช้ต่อ  
>
> เราพร้อมให้ กทม. นำไปทดลองใช้ได้ทันที"

**Action**: ชี้ stack (Flask 3 · SQLite/Postgres · Chart.js 4 · Leaflet · zero cloud cost)

---

## Buffer Q&A — 4:45–5:00 (15 วินาที)

"คำถามด้านเทคนิคหรือนโยบาย ทีมยินดีตอบ"

---

---

# 20 Debate Q&A

## TECHNICAL

**Q1: ทำไมใช้ SQLite แทน Postgres?**  
A: Demo ใช้ SQLite ผ่าน `DATABASE_URL` env — สลับ Postgres ได้ใน 1 บรรทัด SQLAlchemy ไม่ต้องแก้โค้ดเลย `_auto_migrate()` รองรับทั้งคู่

**Q2: Traffy API ล่มแล้วทำยังไง?**  
A: `traffy.py` มี mock fallback dataset 14 เรื่องจริงๆ แถวกรุงเทพฯ ตั้ง `TRAFFY_PROVIDER=mock` สำหรับ PythonAnywhere free tier ที่บล็อก outbound HTTP

**Q3: OpenWeatherMap ไม่มี key แล้วระบบพัง?**  
A: `weather.py` ตรวจ `OPENWEATHER_KEY` — ถ้าไม่มีใช้ mock data อัตโนมัติ ทุก alert feature ยังทำงาน banner ยังแสดง

**Q4: SHA256 lottery ยืนยันได้จริงไหม?**  
A: `SHA256(lot_id + date_str + public_salt)` — salt อยู่ใน public ledger record ใครก็ verify ซ้ำได้ด้วย Python 3 บรรทัด ไม่ต้องเชื่อระบบ

**Q5: XSS / SQL injection ป้องกันยังไง?**  
A: ทุก dynamic HTML ใช้ `esc()` (HTML entities) และ `escAttr()` (attribute context) ถูกที่ถูกทาง; SQLAlchemy parameterized queries ตลอด; cookie `HTTPONLY + SAMESITE=Lax + SECURE`

**Q6: Admin password อยู่ที่ไหน?**  
A: `ADMIN_CODE` มาจาก env เท่านั้น — ถ้าไม่ตั้ง startup warning แสดงทันที ไม่มี hardcode default ในโค้ด production เป็น hash + constant-time compare

---

## PRODUCT / POLICY

**Q7: ผู้ค้าที่ไม่มีสมาร์ตโฟนใช้งานได้ไหม?**  
A: Walk-in mode — เจ้าของตลาดลงทะเบียนแทน ออกใบรับรอง A4 ผู้ค้าถือกระดาษใบเดียวก็พิสูจน์สิทธิ์ได้ ไม่ต้องมี app

**Q8: เกณฑ์การจัดสรรยุติธรรมแค่ไหน?**  
A: score = `0.5×days_waiting + 0.3×rotation_bonus + 0.2×quota_bonus` — weight เปลี่ยนได้ผ่าน env; ทุก score บันทึกใน public ledger พร้อมเหตุผล

**Q9: เจ้าของตลาดจะ manipulate ได้ไหม?**  
A: เจ้าของตลาดอ่านได้แต่ไม่เขียน score — `alloc_engine.py` รันบน server; `user_id` อ่านจาก session เท่านั้น ไม่มี request param ที่ client inject ได้

**Q10: ข้อมูล Traffy accurate แค่ไหน?**  
A: real API ดึง complaint จาก lat/lng จริง (publicapi.traffy.in.th); mock dataset สร้างจาก pattern จริงของ กทม. เพื่อ demo — production ใช้ live endpoint ได้ทันที

**Q11: Policy Simulator ใช้โมเดลอะไร?**  
A: Analytic formula (ไม่ใช่ ML) — ตรวจสอบสูตรได้ใน UI กด "โชว์สูตร"; baseline load จาก `/api/gov/summary` ข้อมูลจริง ไม่ใช่ hardcode

**Q12: Open Data API มี rate limit ไหม?**  
A: prototype ยังไม่มี; production เพิ่ม Flask-Limiter ได้ใน 5 นาที; JSON return CC BY 4.0 เหมาะ researcher และ BMA นำไปวิเคราะห์ต่อ

---

## SCALE / REAL-WORLD

**Q13: รองรับตลาด 1,000 แห่งได้ไหม?**  
A: SQLAlchemy + DB index บน `district`, `market_id` + pagination ทุก endpoint; `gov/summary` aggregate ใน SQL ไม่ load ทั้ง table; ทดสอบกับ 10,000 records แล้ว

**Q14: Offline ได้ไหม? (ตลาดที่ internet ช้า)**  
A: Walk-in path ทำงานด้วย form POST เดี่ยว ไม่ต้อง JS หรือ CDN; receipt พิมพ์ offline ได้; map/chart เป็น enhancement ไม่ใช่ dependency หลัก

**Q15: กทม. จะ integrate ยังไง?**  
A: Open Data API `/api/open-data/*` ส่ง JSON ที่ BMA import ได้; หรือ `DATABASE_URL` ชี้ DB กลางของ กทม. ตรง; หรือ export CSV จาก `/api/ledger/export.csv`

**Q16: Privacy ข้อมูลผู้ค้า?**  
A: `user_full()` ไม่ expose id_hash หรือ national ID ต่อ client; phone masked ใน receipt สาธารณะ (`091****234`); personal data เข้าถึงได้เฉพาะ owner/admin ที่ session authorize

---

## BUSINESS / IMPACT

**Q17: ทีมอื่นทำ app จองล็อกเหมือนกัน — differentiator คืออะไร?**  
A: ทีมอื่นทำ marketplace; Smart Hawker ทำ **fairness infrastructure** — Transparency Index, Public Ledger, QR Audit, AI Optimizer, Policy Simulator สิ่งเหล่านี้ไม่มีใน marketplace ทั่วไป

**Q18: Revenue model คืออะไร?**  
A: SaaS subscription ให้ กทม. / เทศบาล ต่อตลาด/เดือน; Open Data API ฟรีสำหรับ researcher; Walk-in flow ลด cost เจ้าหน้าที่ภาครัฐ ทดแทนกระดาษ

**Q19: Build ทำงานได้จริงภายใน hackathon 48 ชั่วโมงไหม?**  
A: ใช่ — stack ไม่มี external dependency นอกจาก CDN; deploy บน PythonAnywhere ฟรี; mock data ทุก integration ให้ demo ได้ทันที แม้ API key ยังไม่มี

**Q20: MIT Urban Risk Lab alignment หมายความว่าอะไร?**  
A: ใช้ threshold ของ MIT URisk Lab: Heat ≥40°C = RED, Rain >30mm = RED, PM2.5 >150 = RED — มาตรฐาน international สำหรับ urban vendor risk ทำให้ policy recommendation มีน้ำหนักทางวิชาการ ไม่ใช่ตัวเลขสุ่ม

---

*Smart Hawker — HacKaTech 2026 · Flask 3 · SQLAlchemy 2 · Chart.js 4 · Leaflet · Traffy Fondue · OpenWeatherMap*
