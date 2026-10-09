# Smart Hawker — HacKaTech Progress Log

## [2026-06-18] P0.4 สถิติหน้าแรก
- สถานะ: ✅ เสร็จ
- ทำอะไร: เพิ่ม /api/stats endpoint + อัปเดต JS หน้าแรกดึงค่าจริง + ดัชนีความโปร่งใสในแถว stats
- ไฟล์: api.py, templates/index.html
- ทดสอบ: เปิด / แล้วดูตัวเลขสถิติ 4 ช่อง

## [2026-06-18] P0.1 Public Allocation Ledger
- สถานะ: ✅ เสร็จ
- ทำอะไร: /api/ledger endpoint (paginated, filterable) + /api/ledger/export.csv + หน้า /transparency
- ไฟล์: api.py, templates/transparency.html
- ฟีเจอร์: filter จังหวัด/วิธีจัดสรร/สถานะ, search ref_no, pagination, method chips, CSV export
- ทดสอบ: เปิด /transparency → กรอง → export CSV → เปิดใน Excel ดูภาษาไทย

## [2026-06-18] P0.2 Fair Allocation Engine
- สถานะ: ✅ เสร็จ
- ทำอะไร: สร้าง allocation.py (scoring + lottery + auto_booking) + AllocationRecord/ZoneData models
- ไฟล์: allocation.py, models.py
- สูตร: W_WAIT=0.5, W_ROTATION=0.3, W_QUOTA=0.2
- Verifiable Lottery: SHA256(lot_id:date:salt) → reproducible shuffle
- ทดสอบ: POST /api/admin/allocate {"lotId":"xxx","applicants":["uid1","uid2"],"method":"SCORING"}

## [2026-06-18] P0.3 Zoning Layer on Map
- สถานะ: ✅ เสร็จ
- ทำอะไร: /api/zones endpoint + map.html density layer toggle (GREEN/YELLOW/RED circles)
- ไฟล์: api.py, templates/map.html
- ฟีเจอร์: 3 layer buttons (ล็อกว่าง / ความหนาแน่น / ร้องเรียน), circle overlays, density legend
- ทดสอบ: เปิด /map → กด "ความหนาแน่น" → เห็นวงกลมสีต่างๆ

## [2026-06-18] P0.5 How-It-Works Page
- สถานะ: ✅ เสร็จ
- ทำอะไร: หน้า /transparency/how-it-works อธิบายสูตร scoring, lottery, transparency index
- ไฟล์: templates/transparency_how.html
- ฟีเจอร์: formula box, weight bars, example calculation table, lottery explanation

## [2026-06-18] P0.6 Government Dashboard
- สถานะ: ✅ เสร็จ
- ทำอะไร: หน้า /gov สำหรับเจ้าหน้าที่ กทม. + Chart.js charts
- ไฟล์: templates/gov.html
- ฟีเจอร์: 5 KPI cards, doughnut chart สัดส่วนวิธีจัดสรร, bar chart คะแนน, district table
- ทดสอบ: เปิด /gov → ดู chart + table zone data

## [2026-06-18] P0.7 Policy Simulator
- สถานะ: ✅ เสร็จ
- ทำอะไร: หน้า /simulator จำลองนโยบาย 4 sliders, คำนวณ client-side
- ไฟล์: templates/simulator.html
- ฟีเจอร์: sliders จำนวนล็อก/ค่าเช่า/โควตา/ทางเท้า, metrics output, formula toggle, compare table
- ทดสอบ: เปิด /simulator → ขยับสไลเดอร์ → ดูผลเปลี่ยนทันที

## [2026-06-18] P0.8 Demo Seed
- สถานะ: ✅ เสร็จ
- ทำอะไร: seed_demo.py สร้างข้อมูลสาธิตครบ
- ไฟล์: seed_demo.py
- ข้อมูล: 6 ตลาด, 48 ล็อก, 10 ผู้ค้า, 15 bookings, 20 AllocationRecords, 6 ZoneData
- รัน: python seed_demo.py

## [2026-06-18] P1.1 Gov Dashboard Enhanced
- สถานะ: ✅ เสร็จ
- ทำอะไร: เพิ่ม 4 Chart.js charts + district table 11 columns + /api/gov/summary endpoint
- ไฟล์: api.py, templates/gov.html
- ฟีเจอร์: fairness bar, occ bar, complaint grouped, trend line, district table, alloc table

## [2026-06-18] P1.2 Walk-in / Inclusion Mode
- สถานะ: ✅ เสร็จ
- ทำอะไร: Walk-in modal ใน owner page + /api/walkin/booking + /api/walkin/receipt/<bid> + confirm_print.html
- ไฟล์: api.py, app.py, templates/owner.html, templates/confirm_print.html
- ฟีเจอร์: สร้าง seller ถ้าไม่มีอยู่, CONFIRMED status ทันที, พิมพ์ A4 receipt

## [2026-06-18] P1.3 Traffy Fondue Integration
- สถานะ: ✅ เสร็จ
- ทำอะไร: traffy.py (live API + mock fallback) + /api/traffy/all + /api/traffy/near + map layer "Traffy Fondue"
- ไฟล์: traffy.py, api.py, templates/map.html
- ฟีเจอร์: color-coded complaint markers, legend, TRAFFY_PROVIDER=mock env override

## [2026-06-18] P1.4 Resilience Alerts
- สถานะ: ✅ เสร็จ
- ทำอะไร: weather.py (OpenWeatherMap + mock) + /api/weather/alerts + weather banner บน /map
- ไฟล์: weather.py, api.py, templates/map.html
- ฟีเจอร์: GREEN/YELLOW/RED banner, heat/rain/PM2.5 alerts, MIT Urban Risk Lab thresholds, dismissible

## [2026-06-18] P2.1 Policy Simulator Enhanced
- สถานะ: ✅ เสร็จ
- ทำอะไร: เพิ่ม Chart.js Radar chart, load real baseline จาก /api/gov/summary
- ไฟล์: templates/simulator.html
- ฟีเจอร์: Before/After radar, live baseline badge, slider defaults จาก real data

## [2026-06-18] P2.2 AI Allocation Optimizer
- สถานะ: ✅ เสร็จ
- ทำอะไร: /api/optimizer/suggest (greedy, explainable) + section ใน /gov
- ไฟล์: api.py, templates/gov.html
- algorithm: HIGH/MEDIUM priority suggestions — REDUCE_LOTS, SWITCH_TO_SCORING, TRAFFY_REVIEW, REDUCE_FOR_SIDEWALK

## [2026-06-18] P2.3 Open Data API Expanded
- สถานะ: ✅ เสร็จ
- ทำอะไร: /api/open-data/markets + /api/open-data/zones (CC BY 4.0)
- ไฟล์: api.py

## [2026-06-18] P2.4 QR Audit
- สถานะ: ✅ เสร็จ
- ทำอะไร: QR column ใน transparency ledger + modal ด้วย qrcode.js CDN
- ไฟล์: templates/transparency.html
- ฟีเจอร์: per-row QR → public audit URL, market/method/score detail ใน modal

## [2026-06-18] P2.5 Transparency Ranking per District
- สถานะ: ✅ เสร็จ
- ทำอะไร: ranking section ใน /gov พร้อม medal icons + progress bar
- ไฟล์: templates/gov.html
- ข้อมูล: ดึงจาก /api/gov/summary districts → sort by fairnessIndex

## [2026-06-18] DEMO_SCRIPT.md Updated
- สถานะ: ✅ เสร็จ
- ทำอะไร: 5-minute presentation script + 20 Q&A debates
- ไฟล์: DEMO_SCRIPT.md

## สรุป P0 Features ที่ implement แล้ว

| Feature | Status | Route |
|---------|--------|-------|
| AllocationRecord + ZoneData models | ✅ | — |
| Fair Allocation Engine (scoring+lottery) | ✅ | /api/admin/allocate |
| Public Ledger API | ✅ | /api/ledger |
| CSV Export | ✅ | /api/ledger/export.csv |
| Open Data JSON API | ✅ | /api/open-data/allocations |
| Zones API | ✅ | /api/zones |
| Stats API | ✅ | /api/stats |
| Index stats (real data) | ✅ | / |
| Map density layer | ✅ | /map |
| Transparency Ledger Page | ✅ | /transparency |
| How-It-Works Page | ✅ | /transparency/how-it-works |
| Government Dashboard | ✅ | /gov |
| Policy Simulator | ✅ | /simulator |
| Demo Seed | ✅ | python seed_demo.py |

## สรุป P1–P2 Features ที่ implement แล้ว

| Feature | Status | Route |
|---------|--------|-------|
| Gov Dashboard Enhanced (4 charts + district table) | ✅ | /gov |
| Walk-in / Inclusion Mode | ✅ | /owner → Walk-in modal |
| Print Receipt | ✅ | /confirm/<bid>/print |
| Traffy Fondue Layer บนแผนที่ | ✅ | /map → Traffy button |
| Traffy API + mock fallback | ✅ | /api/traffy/all, /near |
| Resilience Weather Banner | ✅ | /map (banner ด้านบน) |
| Weather/AQI API + mock | ✅ | /api/weather/alerts |
| Policy Simulator + Radar Chart | ✅ | /simulator |
| Live baseline จาก gov/summary | ✅ | /simulator |
| AI Optimizer (Greedy, explainable) | ✅ | /api/optimizer/suggest |
| AI Optimizer section ใน Gov | ✅ | /gov |
| Open Data Markets | ✅ | /api/open-data/markets |
| Open Data Zones | ✅ | /api/open-data/zones |
| QR Audit per allocation | ✅ | /transparency |
| Transparency Ranking per district | ✅ | /gov |
| DEMO_SCRIPT.md (5 min + 20 Q&A) | ✅ | DEMO_SCRIPT.md |
