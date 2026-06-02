# 📘 User Manual: Multi-Agent Production System (AgentOS)
**Version:** 2.1 | **Last Updated:** May 4, 2026
**System Architecture:** Async DAG-based Orchestration with Multi-Modal Vision Audit, Context Compression & Control Plane

---

## 🌟 Overview
AgentOS เป็นระบบ AI Agent แบบทำงานร่วมกัน (Multi-Agent System) ระดับ Production ที่ออกแบบมาเพื่อเปลี่ยน "คำสั่งที่ซับซ้อน" ให้เป็น "ผลลัพธ์ระดับมืออาชีพ" โดยใช้กลยุทธ์ **Hybrid Routing** (Local + Cloud) และการประมวลผลแบบ **Asynchronous Parallel Execution** เพื่อประสิทธิภาพสูงสุดและค่าใช้จ่ายที่ต่ำที่สุด

### 🤖 The Agent Team & Capabilities
1. **Knowledge Architect**: วิจัยข้อมูลสดจากอินเทอร์เน็ต (Tavily API), สร้างแผนผังความรู้ (Knowledge Map) และ Mermaid Diagrams
2. **Integrative Synthesis Expert**: วิเคราะห์ข้อมูลเชิงลึก, ตรวจสอบข้อขัดแย้ง (Contradictions) และสร้างความเชื่อมโยงเชิงระบบ
3. **Social Media Mastery**: สร้างคอนเทนต์ประสิทธิภาพสูงสำหรับ 5 แพลตฟอร์ม (LinkedIn, X, TikTok, Facebook, Line) พร้อมกลยุทธ์ Hook-first
4. **Self-Evolving SRE**: ตรวจสอบ Telemetry ของระบบ, ตรวจจับการเสื่อมสภาพของ Agent และเสนอแนวทาง Self-healing
5. **QA & Ethics Auditor**: 
    - **Text Audit**: ตรวจสอบข้อเท็จจริง (Fact-check), อคติ (Bias) และ Compliance
    - **Visual Audit**: ตรวจสอบงานออกแบบรูปภาพ (Readability, Contrast, Layout, Color Harmony)
    - **Refinement Loop**: ส่งงานกลับไปแก้ไขโดยอัตโนมัติหากไม่ผ่านเกณฑ์
6. **Agent Orchestrator**: ผู้ควบคุม Workflow, จัดการ Async DAG Execution และประสานงานระหว่าง Agent ทั้งหมด

---

## ⚙️ Installation & Setup

### 1. Environment Preparation
ติดตั้ง Python 3.8+ และสร้าง Virtual Environment:
```powershell
# Create venv
python -m venv .venv
# Activate venv
.venv\Scripts\activate
# Install dependencies (including Streamlit & Plotly)
pip install -r requirements.txt
```

### 2. Configuration (.env)
สร้างไฟล์ `.env` ใน Root Directory และกำหนดค่าดังนี้:
- `TAVILY_API_KEY`: สำหรับการค้นหาเว็บ (Knowledge Architect)
- `OPENAI_API_KEY` / `GEMINI_API_KEY`: สำหรับ Cloud Brain และ Agent วิเคราะห์
- `LOCAL_LLM_ENDPOINT`: (Optional) เช่น `http://localhost:11434` สำหรับใช้ Qwen 2.5 ผ่าน Ollama (ช่วยลด Token Cost)
- `DATABASE_PATH`: `agent_system.db` (ค่าเริ่มต้น)

---

## 🚀 How to Use

### 🛠️ Implementation Example
คุณสามารถเรียกใช้งานระบบผ่าน `AgentOrchestrator` ใน `orchestrator_main.py`:

```python
from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority

# 1. Initialize System
db = DBManager()
orch = AgentOrchestrator(db)

# 2. Example: Complex Request (Research -> Synthesis -> Content -> QA)
# ระบบจะสร้าง DAG และรัน Agent ที่ไม่เกี่ยวข้องกันแบบ Parallel โดยอัตโนมัติ
user_input = "วิจัยเรื่องการใช้ GLP-1 ในการชะลอวัย, สรุปผล และสร้างโพสต์ LinkedIn สำหรับหมอ"
result = orch.handle_request(user_input, priority=TaskPriority.HIGH)

# 3. Example: Visual Audit Request
visual_input = "ตรวจสอบรูปภาพใน path 'artifacts/design_v1.png' ว่าอ่านง่ายและสีเข้ากันหรือไม่"
visual_result = orch.handle_request(visual_input)

print(result['results'])
```

### 📈 Detailed Workflow Process (Version 2.0)
1. **Triage (Local Router)**: ใช้ Qwen 2.5 วิเคราะห์ว่างานเป็น `SIMPLE` (ส่งให้ Agent ทันที) หรือ `COMPLEX` (ส่งให้ Cloud Brain)
2. **Planning (Cloud Brain)**: 
   - หากประวัติการสนทนายาวเกินไป จะใช้ **Context Compression** เพื่อบีบอัดข้อมูลสำคัญ
   - สร้าง **Directed Acyclic Graph (DAG)** เพื่อกำหนดลำดับการทำงานและ Dependency
3. **Async Execution (Orchestrator)**: 
   - รัน Agent ในรูปแบบ **Waves** (งานที่ไม่มี Dependency ต่อกันจะรันพร้อมกัน)
   - บันทึกทุกขั้นตอนลงใน `TaskRecord` และ `ArtifactRecord` ใน SQLite
   - ใช้ `ResponseValidator` ตรวจสอบ JSON Output ให้ตรงตาม Schema
4. **Quality Gate (QA Auditor)**: 
   - ตรวจสอบผลลัพธ์สุดท้าย
   - หากพบจุดบกพร่อง จะเข้าสู่ **Refinement Loop** (ส่งกลับไปให้ Agent แก้ไข $\rightarrow$ ตรวจซ้ำ) จนกว่าจะผ่านหรือครบ 3 รอบ
5. **Delivery**: รวบรวม Artifacts ทั้งหมดส่งคืนผู้ใช้

---

## 📊 Observability Dashboard
คุณสามารถติดตามการทำงานของระบบได้แบบ Real-time ผ่าน Dashboard:

**วิธีเริ่มใช้งาน:**
```powershell
streamlit run dashboard.py
```
**ฟีเจอร์หลัก:**
- **DAG Flow:** ดู Timeline การทำงานของ Agent แต่ละตัว (Gantt Chart)
- **Token Analytics:** วิเคราะห์การใช้ Token และประมาณการค่าใช้จ่ายราย Agent
- **System Health:** ดูประสิทธิภาพ (Latency) และรายงานจาก SRE Agent
- **Deep Trace:** เจาะลึก Log และ Artifacts ของแต่ละ Task ID

---

## 🔍 Troubleshooting & Maintenance

### Common Issues & Fixes
- **ModuleNotFoundError**: ตรวจสอบว่าได้ activate `.venv` และติดตั้ง `pip install -r requirements.txt`
- **API 429 (Rate Limit)**: ตรวจสอบโควตา API หรือสลับ Provider ใน `.env`
- **Database Lock**: หากเกิด `sqlite3.OperationalError: database is locked` ให้ปิดโปรแกรมที่เชื่อมต่อ DB ทั้งหมด หรือลบ `agent_system.db` เพื่อ Reset
- **JSON Parsing Error**: ระบบมี `ResponseValidator` ช่วยล้าง Markdown fences (` ```json `) ให้อัตโนมัติ

### System Health Check
รันสคริปต์ทดสอบเพื่อยืนยันความพร้อม:
- `test_env_config.py`: ตรวจสอบ API Keys
- `test_api_connectivity.py`: ตรวจสอบการเชื่อมต่อ LLM/Tavily
- `test_visual_audit.py`: ทดสอบระบบตรวจสอบรูปภาพ
- `test_e2e_pipeline.py`: ทดสอบ Workflow ตั้งแต่ต้นจนจบ

---

## 🛡️ Safety, Ethics & Compliance
ระบบถูกออกแบบให้มี Guardrails ในทุกขั้นตอน:
- **Fact Checking**: ป้องกันการ Hallucination โดยการอ้างอิงแหล่งที่มา
- **Bias Detection**: ตรวจสอบอคติ 5 ด้าน (Gender, Political, Racial, Ageist, Ableist)
- **Visual Compliance**: ตรวจสอบ Contrast Ratio ตามมาตรฐาน WCAG AAA
- **SRE Monitoring**: ตรวจจับ Agent Degradation เพื่อป้องกันคุณภาพงานลดลง
- **Control Plane (Human-in-the-Loop)**: ระบบควบคุมการทำงานของ Agent แบบ Real-time ผ่าน Dashboard เพื่อให้มนุษย์สามารถตรวจสอบและปรับแต่งการทำงานได้โดยไม่ต้องเขียนโค้ด
