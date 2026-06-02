# 📅 Booking Appointment Agent - Documentation

**Agent 8** ในระบบ Multi-Agent System - จัดการการจองนัดหมายอย่างอัจฉริยะพร้อมการรวบรวมข้อมูลแบบหลายขั้นตอน

## 🎯 ฟีเจอร์หลัก

### 1. **การรวบรวมข้อมูลแบบหลายขั้นตอน (Multi-Turn Collection)**
Agent จะขอข้อมูลทีละขั้นตอนในการสนทนา:
- ✅ ชื่อ (First Name)
- ✅ สกุล (Last Name)
- ✅ เบอร์โทรศัพท์ (Phone Number)
- ✅ วันที่นัดหมาย (Preferred Date)
- ✅ เวลานัดหมาย (Preferred Time)
- ✅ หมายเหตุเพิ่มเติม (Notes) - ไม่จำเป็น

### 2. **การตรวจสอบข้อมูล (Validation)**
- 📋 ตรวจสอบชื่อ - ต้องมีอย่างน้อย 2 ตัวอักษร
- 📱 ตรวจสอบเบอร์โทร - ต้องมีอย่างน้อย 9 หลัก
- 📅 ตรวจสอบวันที่ - รูปแบบ YYYY-MM-DD และต้องเป็นวันข้างหน้า
- ⏰ ตรวจสอบเวลา - รูปแบบ HH:MM

### 3. **การจองตรงโดยการให้ข้อมูลทั้งหมด (Direct Booking)**
หากมีข้อมูลครบถ้วน สามารถจองได้ในครั้งเดียว

### 4. **การจัดการนัดหมาย (Appointment Management)**
- ✓ ตรวจสอบสถานะ (Check Status)
- ✓ ยกเลิกนัดหมาย (Cancel)
- ✓ เปลี่ยนแปลงนัดหมาย (Reschedule)

## 📊 การรวบรวมข้อมูลแบบหลายขั้นตอน (Multi-Turn Flow)

```
User: "ผมต้องการจองนัดหมาย"
  ↓ [Agent checks conversation state]
  ↓
Agent: "👤 กรุณาระบุชื่อของคุณครับ:"
  ↓
User: "สมชาย"
  ↓ [Validation: ✓ Valid]
  ↓
Agent: "✓ ชื่อ: สมชาย
        👤 กรุณาระบุสกุลของคุณครับ:"
  ↓
User: "สมศรี"
  ↓ [Validation: ✓ Valid]
  ↓
Agent: "✓ สกุล: สมศรี
        📱 กรุณาระบุเบอร์โทรศัพท์:"
  ↓
... [continues for 3 more fields]
  ↓
Agent: "✓ ยืนยันการนัดหมายสำเร็จครับ!
        
        📋 สรุปข้อมูลนัดหมาย:
        • ชื่อ-สกุล: สมชาย สมศรี
        • เบอร์โทร: 0812345678
        • วันที่: 2026-05-20
        • เวลา: 14:30
        • เลขที่นัดหมาย: APT-a1b2c3d4"
```

## 🛠️ การใช้งาน

### ตัวอย่าง 1: Multi-Turn Booking ผ่าน Telegram
```
User: ผมต้องการจองนัดหมายตรวจสุขภาพ
Bot: 👤 กรุณาระบุชื่อของคุณครับ:

User: นายดำ
Bot: ✓ ชื่อ: นายดำ
     👤 กรุณาระบุสกุลของคุณครับ:

... [continues]
```

### ตัวอย่าง 2: Direct Booking ผ่าน Python API
```python
from booking_appointment_agent import BookingAppointmentAgent
from schemas import TaskRequest, TaskAction, AgentRole

agent = BookingAppointmentAgent(db)

task = TaskRequest(
    task_id="booking_001",
    agent_role=AgentRole.BOOKING_AGENT,
    action=TaskAction.BOOK_APPOINTMENT,
    payload={
        "first_name": "นายสมชาย",
        "last_name": "สมศรี",
        "phone_number": "0812345678",
        "preferred_date": "2026-05-20",
        "preferred_time": "14:30",
        "notes": "อาการปวดศีรษะ"
    }
)

result = asyncio.run(agent.process_task(task))
```

## 📦 โครงสร้างข้อมูล

### AppointmentInfo Model
```python
{
    "appointment_id": "APT-xxxxx",
    "first_name": "สมชาย",
    "last_name": "สมศรี",
    "phone_number": "0812345678",
    "email": None,
    "appointment_type": "consultation",
    "preferred_date": "2026-05-20",
    "preferred_time": "14:30",
    "notes": "หมายเหตุ",
    "status": "confirmed",
    "created_by_session": "session_id",
    "created_at": "2026-04-30T10:00:00"
}
```

### AppointmentStatus Values
- `pending` - รอการยืนยัน
- `confirmed` - ยืนยันแล้ว
- `completed` - เสร็จสิ้น
- `cancelled` - ถูกยกเลิก
- `no_show` - ไม่มาตามนัด

## 🔧 การทดสอบ

### Run Tests
```bash
python test_booking_appointment.py
```

### Tests ที่รวมอยู่
1. ✅ Multi-turn booking flow
2. ✅ Direct booking with all info
3. ✅ Appointment status checking
4. ✅ Data validation
5. ✅ Multi-step state persistence

## 📝 Database Schema

### appointments table
```sql
CREATE TABLE appointments (
    appointment_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    email TEXT,
    appointment_type TEXT DEFAULT 'consultation',
    preferred_date TEXT NOT NULL,
    preferred_time TEXT NOT NULL,
    notes TEXT,
    status TEXT DEFAULT 'pending',
    created_by_session TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    confirmed_at DATETIME,
    completed_at DATETIME
)
```

### appointment_collection_states table
```sql
CREATE TABLE appointment_collection_states (
    state_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    current_step INTEGER DEFAULT 0,
    collected_data JSON,
    steps_config JSON,
    is_complete BOOLEAN DEFAULT FALSE,
    appointment_id TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(appointment_id) REFERENCES appointments(appointment_id)
)
```

## 🎪 Integration Points

### Router Configuration
ใน `router.py` Agent ถูกเพิ่มเป็น routing option:
```python
"booking_appointment_agent": "For appointment booking, scheduling, customer information collection"
```

### Orchestrator Registration
ใน `orchestrator_main.py` Agent ถูกลงทะเบียน:
```python
self.booking_agent = BookingAppointmentAgent(db_manager)
```

### Telegram Bot Support
ใน `telegram_bot.py` มีการจัดการพิเศษสำหรับ booking responses:
```python
if "prompt" in artifacts:
    # Handle multi-turn prompt
    answer = artifacts.get("prompt")
```

## 💡 Action Types

### 1. COLLECT_INFO
สำหรับการรวบรวมข้อมูลแบบหลายขั้นตอน
```python
TaskAction.COLLECT_INFO
```

### 2. BOOK_APPOINTMENT
สำหรับการจองโดยให้ข้อมูลทั้งหมด
```python
TaskAction.BOOK_APPOINTMENT
```

### 3. MANAGE_APPOINTMENT
สำหรับการจัดการนัดหมาย (cancel, reschedule, check_status)
```python
TaskAction.MANAGE_APPOINTMENT
```

## 📱 Telegram Command Examples

```
/start - เริ่มต้นและดูเมนู
"ผมต้องการจองนัดหมาย" - เริ่มการจองนัดหมาย
"จองคิวจึงวินิจฉัย" - เริ่มการจองนัดหมาย
"ตรวจสอบนัดหมายของผม" - ตรวจสอบสถานะ
```

## 🔐 Security Features

- ✅ Input validation ทั้งหมด
- ✅ Phone number sanitization
- ✅ Date format validation
- ✅ Session isolation per user
- ✅ Database encryption support

## 📊 Metrics & Logging

Agent บันทึก:
- ✓ Appointment creation events
- ✓ Validation failures
- ✓ Collection state transitions
- ✓ Error messages
- ✓ User interactions

## 🚀 Future Enhancements

1. 📧 Email notifications before appointment
2. 📱 SMS reminders
3. 📞 Auto-reschedule conflicting bookings
4. 🎯 Preferred time slot suggestions
5. 🔄 Two-way sync with calendar systems
6. 👥 Multiple service providers
7. 💳 Payment integration
8. ⭐ Rating & review system

## 📞 Support

สำหรับปัญหาหรือคำถาม:
1. ตรวจสอบ logs ใน `utils/logs/`
2. Run `test_booking_appointment.py` เพื่อหา issues
3. ตรวจสอบ database state ใน `agent_system.db`

## ✨ Version Info

- **Version**: 1.0.0
- **Created**: 2026-04-30
- **Agent #**: 8/10
- **Status**: Production Ready ✅
