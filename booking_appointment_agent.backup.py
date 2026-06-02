"""
booking_appointment_agent.py - The Appointment Booking Agent (Agent 8)
Handles appointment booking with multi-turn conversation for information collection.
Collects: First Name, Last Name, Phone Number, Appointment Date & Time
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from database import DBManager, AppointmentRecord, AppointmentCollectionStateRecord
from schemas import (
    TaskRequest, TaskResponse, TaskStatus, AgentRole, TaskAction,
    AppointmentInfo, AppointmentStatus, AppointmentType,
    AppointmentCollectionStep, AppointmentCollectionState
)
from utils.logger import logger


class AppointmentValidator:
    """Validates appointment information."""
    
    @staticmethod
    def is_valid_phone(phone: str) -> Tuple[bool, str]:
        """Validates phone number (at least 9 digits)."""
        digits_only = ''.join(filter(str.isdigit, phone))
        if len(digits_only) >= 9:
            return True, digits_only
        return False, "เบอร์โทรศัพท์ต้องมีอย่างน้อย 9 หลัก"
    
    @staticmethod
    def is_valid_name(name: str) -> Tuple[bool, str]:
        """Validates name (not empty, at least 2 characters)."""
        name = name.strip()
        if len(name) < 2:
            return False, "ชื่อต้องมีอย่างน้อย 2 ตัวอักษร"
        return True, name
    
    @staticmethod
    def is_valid_date(date_str: str) -> Tuple[bool, str]:
        """Validates date format (YYYY-MM-DD) and that it's in future."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if dt.date() < datetime.now().date():
                return False, "วันที่ต้องเป็นวันข้างหน้า"
            return True, date_str
        except ValueError:
            return False, "รูปแบบวันที่ต้องเป็น YYYY-MM-DD เช่น 2026-05-15"
    
    @staticmethod
    def is_valid_time(time_str: str) -> Tuple[bool, str]:
        """Validates time format (HH:MM)."""
        try:
            datetime.strptime(time_str, "%H:%M")
            return True, time_str
        except ValueError:
            return False, "รูปแบบเวลาต้องเป็น HH:MM เช่น 14:30"


class AppointmentCollector:
    """Handles multi-turn appointment information collection."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.validator = AppointmentValidator()
        
        # Define collection steps
        self.collection_steps = [
            {
                "field_name": "first_name",
                "prompt": "👤 กรุณาระบุชื่อของคุณครับ:",
                "required": True
            },
            {
                "field_name": "last_name",
                "prompt": "👤 กรุณาระบุสกุลของคุณครับ:",
                "required": True
            },
            {
                "field_name": "phone_number",
                "prompt": "📱 กรุณาระบุเบอร์โทรศัพท์ติดต่อของคุณ (เช่น 08X-XXX-XXXX):",
                "required": True
            },
            {
                "field_name": "preferred_date",
                "prompt": "📅 คุณต้องการนัดหมายวันไหน? (รูปแบบ YYYY-MM-DD เช่น 2026-05-15):",
                "required": True
            },
            {
                "field_name": "preferred_time",
                "prompt": "⏰ คุณต้องการนัดหมายเวลาไหน? (รูปแบบ HH:MM เช่น 14:30):",
                "required": True
            },
            {
                "field_name": "notes",
                "prompt": "📝 มีข้อมูลเพิ่มเติมหรือหมายเหตุพิเศษไหมครับ? (ถ้าไม่มีก็พิมพ์ 'ไม่มี'):",
                "required": False
            }
        ]
    
    def initialize_collection(self, session_id: str) -> AppointmentCollectionState:
        """Initialize a new appointment collection session."""
        state = AppointmentCollectionState(
            session_id=session_id,
            current_step=0,
            collected_data={},
            steps=[
                AppointmentCollectionStep(
                    field_name=step["field_name"],
                    prompt=step["prompt"],
                    required=step["required"]
                )
                for step in self.collection_steps
            ],
            is_complete=False
        )
        
        # Save to database
        try:
            state_record = AppointmentCollectionStateRecord(
                session_id=session_id,
                current_step=0,
                collected_data={},
                steps_config=self.collection_steps,
                is_complete=False
            )
            session = self.db.Session()
            session.add(state_record)
            session.commit()
            session.close()
            logger.info(f"Initialized appointment collection for session {session_id}")
        except Exception as e:
            logger.error(f"Error initializing collection state: {e}")
        
        return state
    
    def get_collection_state(self, session_id: str) -> Optional[AppointmentCollectionState]:
        """Retrieve existing collection state for session."""
        try:
            session = self.db.Session()
            state_record = session.query(AppointmentCollectionStateRecord).filter_by(
                session_id=session_id,
                is_complete=False
            ).first()
            session.close()
            
            if not state_record:
                return None
            
            return AppointmentCollectionState(
                session_id=state_record.session_id,
                current_step=state_record.current_step,
                collected_data=state_record.collected_data or {},
                steps=[
                    AppointmentCollectionStep(
                        field_name=step["field_name"],
                        prompt=step["prompt"],
                        required=step["required"]
                    )
                    for step in self.collection_steps
                ],
                is_complete=state_record.is_complete,
                appointment=None
            )
        except Exception as e:
            logger.error(f"❌ Error retrieving collection state: {e}")
            return None
    
    def process_user_response(self, state: AppointmentCollectionState, user_input: str) -> Tuple[bool, str]:
        """
        Process user input for current step.
        Returns: (is_valid, message)
        """
        current_step = state.steps[state.current_step]
        field_name = current_step.field_name
        
        # Validation logic per field
        if field_name == "first_name":
            is_valid, value = self.validator.is_valid_name(user_input)
            if not is_valid:
                return False, f"❌ {value}\n💬 ลองใหม่ครับ:"
            state.collected_data["first_name"] = value
            return True, f"✓ ชื่อ: {value}\n"
        
        elif field_name == "last_name":
            is_valid, value = self.validator.is_valid_name(user_input)
            if not is_valid:
                return False, f"❌ {value}\n💬 ลองใหม่ครับ:"
            state.collected_data["last_name"] = value
            return True, f"✓ สกุล: {value}\n"
        
        elif field_name == "phone_number":
            is_valid, value = self.validator.is_valid_phone(user_input)
            if not is_valid:
                return False, f"❌ {value}\n💬 ลองใหม่ครับ:"
            state.collected_data["phone_number"] = value
            return True, f"✓ เบอร์โทร: {value}\n"
        
        elif field_name == "preferred_date":
            is_valid, value = self.validator.is_valid_date(user_input)
            if not is_valid:
                return False, f"❌ {value}\n💬 ลองใหม่ครับ:"
            state.collected_data["preferred_date"] = value
            return True, f"✓ วันที่: {value}\n"
        
        elif field_name == "preferred_time":
            is_valid, value = self.validator.is_valid_time(user_input)
            if not is_valid:
                return False, f"❌ {value}\n💬 ลองใหม่ครับ:"
            state.collected_data["preferred_time"] = value
            return True, f"✓ เวลา: {value}\n"
        
        elif field_name == "notes":
            notes = user_input.strip()
            if notes.lower() == "ไม่มี":
                state.collected_data["notes"] = None
                return True, f"✓ ไม่มีหมายเหตุเพิ่มเติม\n"
            state.collected_data["notes"] = notes
            return True, f"✓ หมายเหตุ: {notes}\n"
        
        return False, "❌ ข้อมูลไม่ถูกต้อง"
    
    def get_next_prompt(self, state: AppointmentCollectionState) -> Optional[str]:
        """Get the prompt for next step."""
        if state.current_step >= len(state.steps):
            return None
        return state.steps[state.current_step].prompt
    
    def advance_step(self, state: AppointmentCollectionState):
        """Move to next collection step."""
        state.current_step += 1
        if state.current_step >= len(state.steps):
            state.is_complete = True
    
    def create_appointment(self, state: AppointmentCollectionState, session_id: str) -> AppointmentInfo:
        """Create appointment from collected data."""
        appointment = AppointmentInfo(
            first_name=state.collected_data["first_name"],
            last_name=state.collected_data["last_name"],
            phone_number=state.collected_data["phone_number"],
            preferred_date=state.collected_data["preferred_date"],
            preferred_time=state.collected_data["preferred_time"],
            notes=state.collected_data.get("notes"),
            status=AppointmentStatus.CONFIRMED,
            created_by_session=session_id
        )
        
        # Save to database
        try:
            apt_record = AppointmentRecord(
                appointment_id=appointment.appointment_id,
                first_name=appointment.first_name,
                last_name=appointment.last_name,
                phone_number=appointment.phone_number,
                email=appointment.email,
                appointment_type=appointment.appointment_type.value,
                preferred_date=appointment.preferred_date,
                preferred_time=appointment.preferred_time,
                notes=appointment.notes,
                status=appointment.status.value,
                created_by_session=session_id,
                confirmed_at=datetime.now()
            )
            
            session = self.db.Session()
            session.add(apt_record)
            
            # Update collection state to complete
            state_record = session.query(AppointmentCollectionStateRecord).filter_by(
                session_id=session_id
            ).first()
            if state_record:
                state_record.is_complete = True
                state_record.appointment_id = appointment.appointment_id
            
            session.commit()
            session.close()
            
            logger.info(f"Created appointment {appointment.appointment_id} for {appointment.full_name()}")
            return appointment
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise


class BookingAppointmentAgent:
    """The Appointment Booking Agent - Handles all appointment-related tasks."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.collector = AppointmentCollector(db_manager)
    
    async def process_task(self, task: TaskRequest) -> TaskResponse:
        """
        Process appointment booking task.
        Supports multi-turn conversation for information collection.
        """
        task_id = task.task_id
        
        try:
            if task.action == TaskAction.COLLECT_INFO:
                return await self._handle_collect_info(task)
            elif task.action == TaskAction.BOOK_APPOINTMENT:
                return await self._handle_book_appointment(task)
            elif task.action == TaskAction.MANAGE_APPOINTMENT:
                return await self._handle_manage_appointment(task)
            else:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": f"Unknown action: {task.action}"},
                    error_message="ไม่รองรับคำสั่งนี้"
                )
        except Exception as e:
            logger.error(f"❌ Booking Agent Error: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message=f"เกิดข้อผิดพลาด: {str(e)}"
            )
    
    async def _handle_collect_info(self, task: TaskRequest) -> TaskResponse:
        """Handle multi-turn information collection."""
        task_id = task.task_id
        session_id = task.payload.get("session_id")
        user_input = task.payload.get("user_input", "").strip()
        
        if not session_id:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": "Missing session_id"},
                error_message="ขาด session_id"
            )
        
        # Get or initialize collection state
        state = self.collector.get_collection_state(session_id)
        if not state:
            # Start new collection
            state = self.collector.initialize_collection(session_id)
            prompt = self.collector.get_next_prompt(state)
            
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.IN_PROGRESS,
                artifacts={
                    "step": state.current_step,
                    "prompt": prompt,
                    "total_steps": len(state.steps),
                    "progress": f"ขั้นตอนที่ {state.current_step + 1}/{len(state.steps)}"
                }
            )
        
        # Process user input
        if user_input:
            is_valid, message = self.collector.process_user_response(state, user_input)
            
            if not is_valid:
                # Invalid input, ask again
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.IN_PROGRESS,
                    artifacts={
                        "step": state.current_step,
                        "validation_error": message,
                        "total_steps": len(state.steps),
                        "progress": f"ขั้นตอนที่ {state.current_step + 1}/{len(state.steps)}"
                    }
                )
            
            # Valid input, advance
            self.collector.advance_step(state)
            
            # Update state in database
            try:
                session = self.db.Session()
                state_record = session.query(AppointmentCollectionStateRecord).filter_by(
                    session_id=session_id
                ).first()
                if state_record:
                    state_record.current_step = state.current_step
                    state_record.collected_data = state.collected_data
                    state_record.is_complete = state.is_complete
                    session.commit()
                session.close()
            except Exception as e:
                logger.error(f"Error updating state: {e}")
            
            # Check if collection is complete
            if state.is_complete:
                # Create appointment
                appointment = self.collector.create_appointment(state, session_id)
                
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "appointment_id": appointment.appointment_id,
                        "status": "confirmed",
                        "summary": f"""✓ ยืนยันการนัดหมายสำเร็จครับ!

📋 สรุปข้อมูลนัดหมาย:
• ชื่อ-สกุล: {appointment.full_name()}
• เบอร์โทร: {appointment.phone_number}
• วันที่: {appointment.preferred_date}
• เวลา: {appointment.preferred_time}
• เลขที่นัดหมาย: {appointment.appointment_id}

💬 ระบบจะส่งข้อมูลและเตือนให้คุณก่อนถึงวันนัดหมายครับ""",
                        "appointment": appointment.model_dump()
                    }
                )
            else:
                # Get next prompt
                next_prompt = self.collector.get_next_prompt(state)
                
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.IN_PROGRESS,
                    artifacts={
                        "step": state.current_step,
                        "prompt": next_prompt,
                        "total_steps": len(state.steps),
                        "progress": f"ขั้นตอนที่ {state.current_step + 1}/{len(state.steps)}"
                    }
                )
        
        # No input yet, get first prompt
        prompt = self.collector.get_next_prompt(state)
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.IN_PROGRESS,
            artifacts={
                "step": state.current_step,
                "prompt": prompt,
                "total_steps": len(state.steps),
                "progress": f"ขั้นตอนที่ {state.current_step + 1}/{len(state.steps)}"
            }
        )
    
    async def _handle_book_appointment(self, task: TaskRequest) -> TaskResponse:
        """Handle direct appointment booking (all info provided at once)."""
        task_id = task.task_id
        payload = task.payload
        
        # Validate required fields
        required_fields = ["first_name", "last_name", "phone_number", "preferred_date", "preferred_time"]
        missing_fields = [f for f in required_fields if f not in payload or not payload[f]]
        
        if missing_fields:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.NEEDS_CLARIFICATION,
                artifacts={"missing_fields": missing_fields},
                error_message=f"ขาดข้อมูล: {', '.join(missing_fields)}"
            )
        
        # Create appointment
        appointment = AppointmentInfo(
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            phone_number=payload["phone_number"],
            preferred_date=payload["preferred_date"],
            preferred_time=payload["preferred_time"],
            notes=payload.get("notes"),
            status=AppointmentStatus.CONFIRMED,
            created_by_session=payload.get("session_id")
        )
        
        # Save to database
        try:
            apt_record = AppointmentRecord(
                appointment_id=appointment.appointment_id,
                first_name=appointment.first_name,
                last_name=appointment.last_name,
                phone_number=appointment.phone_number,
                email=appointment.email,
                appointment_type=payload.get("appointment_type", "consultation"),
                preferred_date=appointment.preferred_date,
                preferred_time=appointment.preferred_time,
                notes=appointment.notes,
                status=appointment.status.value,
                created_by_session=payload.get("session_id"),
                confirmed_at=datetime.now()
            )
            
            session = self.db.Session()
            session.add(apt_record)
            session.commit()
            session.close()
            
            logger.info(f"Booked appointment {appointment.appointment_id}")
            
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "appointment_id": appointment.appointment_id,
                    "status": "confirmed",
                    "appointment": appointment.model_dump()
                }
            )
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message="ไม่สามารถจองนัดหมายได้"
            )
    
    async def _handle_manage_appointment(self, task: TaskRequest) -> TaskResponse:
        """Handle appointment management (cancel, reschedule, check status)."""
        task_id = task.task_id
        operation = task.payload.get("operation")  # cancel, reschedule, check_status
        appointment_id = task.payload.get("appointment_id")
        
        try:
            session = self.db.Session()
            appointment = session.query(AppointmentRecord).filter_by(
                appointment_id=appointment_id
            ).first()
            session.close()
            
            if not appointment:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": f"Appointment not found: {appointment_id}"},
                    error_message="ไม่พบข้อมูลนัดหมาย"
                )
            
            if operation == "cancel":
                session = self.db.Session()
                appointment.status = "cancelled"
                session.commit()
                session.close()
                
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "message": f"✓ ยกเลิกนัดหมาย {appointment_id} สำเร็จ"
                    }
                )
            
            elif operation == "check_status":
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "appointment_id": appointment_id,
                        "status": appointment.status,
                        "date": appointment.preferred_date,
                        "time": appointment.preferred_time,
                        "customer": f"{appointment.first_name} {appointment.last_name}"
                    }
                )
            
            else:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": f"Unknown operation: {operation}"},
                    error_message="ไม่รองรับคำสั่งนี้"
                )
        
        except Exception as e:
            logger.error(f"Error managing appointment: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message="เกิดข้อผิดพลาดในการจัดการนัดหมาย"
            )
