"""
booking_appointment_agent_enhanced.py - Enhanced Appointment Booking Agent (Agent 8)
Comprehensive appointment booking system with availability management, notifications, rescheduling, and history tracking.
"""

import json
import re
from datetime import datetime, timedelta, time as datetime_time
from typing import Dict, Any, Optional, List, Tuple
from database import (
    DBManager, AppointmentRecord, AppointmentCollectionStateRecord,
    DepartmentRecord, ServiceTypeRecord, AppointmentSlotRecord,
    NotificationRecord, ReschedulingRecord, CancellationRecord,
    AppointmentHistoryRecord
)
from schemas import (
    TaskRequest, TaskResponse, TaskStatus, AgentRole, TaskAction,
    AppointmentInfo, AppointmentStatus, AppointmentType,
    AppointmentCollectionStep, AppointmentCollectionState,
    NotificationType, RescheduleReason, CancellationReason,
    AppointmentSlot, Notification, ReschedulingRequest, CancellationRequest
)
from utils.logger import logger


# ============================================
# APPOINTMENT VALIDATORS & HELPERS
# ============================================

class AppointmentValidator:
    """Enhanced appointment validator with additional checks."""
    
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
    def is_valid_email(email: str) -> Tuple[bool, str]:
        """Validates email format."""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if email and not re.match(email_regex, email):
            return False, "รูปแบบอีเมลไม่ถูกต้อง"
        return True, email
    
    @staticmethod
    def is_valid_date(date_str: str) -> Tuple[bool, str]:
        """Validates date format (YYYY-MM-DD) and that it's in future."""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if dt.date() < datetime.now().date():
                return False, "วันที่ต้องเป็นวันข้างหน้า"
            # Check not too far in the future (e.g., not beyond 3 months)
            max_future = datetime.now().date() + timedelta(days=90)
            if dt.date() > max_future:
                return False, "วันที่ไม่ควรเกิน 3 เดือนข้างหน้า"
            return True, date_str
        except ValueError:
            return False, "รูปแบบวันที่ต้องเป็น YYYY-MM-DD เช่น 2026-05-15"
    
    @staticmethod
    def is_valid_time(time_str: str) -> Tuple[bool, str]:
        """Validates time format (HH:MM) and reasonable hours."""
        try:
            dt = datetime.strptime(time_str, "%H:%M")
            hour = dt.hour
            # Check if time is during business hours (7:00 - 18:00)
            if hour < 7 or hour >= 18:
                return False, "เวลานัดหมายต้องอยู่ระหว่าง 7:00 - 18:00"
            return True, time_str
        except ValueError:
            return False, "รูปแบบเวลาต้องเป็น HH:MM เช่น 14:30"


# ============================================
# APPOINTMENT AVAILABILITY MANAGER
# ============================================

class AppointmentAvailabilityManager:
    """Manages appointment slot availability and scheduling."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
    
    def get_available_slots(self, department_id: str, date_str: str) -> List[AppointmentSlot]:
        """Get available time slots for a specific department and date."""
        try:
            session = self.db.Session()
            slots = session.query(AppointmentSlotRecord).filter(
                AppointmentSlotRecord.department_id == department_id,
                AppointmentSlotRecord.date == date_str,
                AppointmentSlotRecord.is_available == True
            ).all()
            
            result = [
                AppointmentSlot(
                    slot_id=slot.slot_id,
                    department_id=slot.department_id,
                    date=slot.date,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    capacity=slot.capacity,
                    booked_count=slot.booked_count,
                    is_available=slot.booked_count < slot.capacity
                )
                for slot in slots if slot.booked_count < slot.capacity
            ]
            session.close()
            return result
        except Exception as e:
            logger.error(f"Error getting available slots: {e}")
            return []
    
    def get_available_dates(self, department_id: str, days_ahead: int = 14) -> List[str]:
        """Get dates with available slots in the next N days."""
        try:
            session = self.db.Session()
            today = datetime.now().date()
            dates = []
            
            for i in range(1, days_ahead + 1):
                check_date = today + timedelta(days=i)
                date_str = check_date.strftime("%Y-%m-%d")
                
                slot_count = session.query(AppointmentSlotRecord).filter(
                    AppointmentSlotRecord.department_id == department_id,
                    AppointmentSlotRecord.date == date_str,
                    AppointmentSlotRecord.is_available == True
                ).count()
                
                if slot_count > 0:
                    dates.append(date_str)
            
            session.close()
            return dates
        except Exception as e:
            logger.error(f"Error getting available dates: {e}")
            return []
    
    def book_slot(self, slot_id: str) -> Tuple[bool, str]:
        """Book a specific time slot."""
        try:
            session = self.db.Session()
            slot = session.query(AppointmentSlotRecord).filter_by(slot_id=slot_id).first()
            
            if not slot or slot.booked_count >= slot.capacity:
                session.close()
                return False, "ช่วงเวลาดังกล่าวไม่ว่าง"
            
            slot.booked_count += 1
            session.commit()
            session.close()
            return True, "จองช่วงเวลาสำเร็จ"
        except Exception as e:
            logger.error(f"Error booking slot: {e}")
            return False, "ไม่สามารถจองช่วงเวลาได้"
    
    def release_slot(self, slot_id: str) -> bool:
        """Release a booked slot (for cancellations)."""
        try:
            session = self.db.Session()
            slot = session.query(AppointmentSlotRecord).filter_by(slot_id=slot_id).first()
            
            if slot and slot.booked_count > 0:
                slot.booked_count -= 1
                session.commit()
                session.close()
                return True
            
            session.close()
            return False
        except Exception as e:
            logger.error(f"Error releasing slot: {e}")
            return False


# ============================================
# NOTIFICATION MANAGER
# ============================================

class NotificationManager:
    """Manages appointment notifications (SMS/Email)."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
    
    def create_notification(self, appointment_id: str, notification_type: NotificationType,
                           recipient: str, message: str) -> Notification:
        """Create a notification record."""
        try:
            notification = Notification(
                appointment_id=appointment_id,
                notification_type=notification_type,
                recipient=recipient,
                message=message,
                delivery_status="pending"
            )
            
            notif_record = NotificationRecord(
                notification_id=notification.notification_id,
                appointment_id=appointment_id,
                notification_type=notification_type.value,
                recipient=recipient,
                message=message,
                delivery_status="pending"
            )
            
            session = self.db.Session()
            session.add(notif_record)
            session.commit()
            session.close()
            
            logger.info(f"Created notification {notification.notification_id}")
            return notification
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise
    
    def send_confirmation_sms(self, appointment: AppointmentInfo) -> bool:
        """Send SMS confirmation for appointment."""
        try:
            message = f"""✓ ยืนยันการนัดหมายสำเร็จ!
เลขที่นัดหมาย: {appointment.appointment_id}
วัน-เวลา: {appointment.preferred_date} {appointment.preferred_time}
ระบบจะส่งการเตือนให้คุณก่อนนัดหมาย"""
            
            self.create_notification(
                appointment.appointment_id,
                NotificationType.SMS_CONFIRMATION,
                appointment.phone_number,
                message
            )
            return True
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    def send_reminder(self, appointment_id: str, appointment: AppointmentInfo) -> bool:
        """Send reminder 1 day before appointment."""
        try:
            message = f"""💬 การเตือน: นัดหมายของคุณคืนพรุ่งนี้!
เลขที่นัดหมาย: {appointment_id}
เวลา: {appointment.preferred_date} {appointment.preferred_time}
กรุณามาถึงสักครู่ก่อนเวลานัดหมาย"""
            
            self.create_notification(
                appointment_id,
                NotificationType.SMS_REMINDER,
                appointment.phone_number,
                message
            )
            return True
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return False
    
    def send_reschedule_notice(self, appointment_id: str, old_datetime: str,
                               new_datetime: str, phone: str) -> bool:
        """Send notice about rescheduled appointment."""
        try:
            message = f"""✓ นัดหมายของคุณได้รับการเปลี่ยนแปลง
เลขที่นัดหมาย: {appointment_id}
เวลาเก่า: {old_datetime}
เวลาใหม่: {new_datetime}"""
            
            self.create_notification(
                appointment_id,
                NotificationType.RESCHEDULE_NOTICE,
                phone,
                message
            )
            return True
        except Exception as e:
            logger.error(f"Error sending reschedule notice: {e}")
            return False


# ============================================
# DUPLICATE PREVENTION MANAGER
# ============================================

class DuplicatePreventionManager:
    """Prevents duplicate appointment bookings."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
    
    def check_duplicate(self, phone: str, date: str, time: str,
                       grace_period_hours: int = 24) -> Tuple[bool, Optional[str]]:
        """Check if customer already has appointment at same time."""
        try:
            session = self.db.Session()
            
            # Check for exact same appointment within grace period
            recent_apt = session.query(AppointmentRecord).filter(
                AppointmentRecord.phone_number == phone,
                AppointmentRecord.preferred_date == date,
                AppointmentRecord.preferred_time == time,
                AppointmentRecord.status.in_(["pending", "confirmed"]),
                AppointmentRecord.created_at >= datetime.now() - timedelta(hours=grace_period_hours)
            ).first()
            
            session.close()
            
            if recent_apt:
                return True, recent_apt.appointment_id
            
            return False, None
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False, None
    
    def check_conflicting_appointments(self, phone: str, date: str) -> List[Dict]:
        """Get customer's appointments on same date."""
        try:
            session = self.db.Session()
            
            appointments = session.query(AppointmentRecord).filter(
                AppointmentRecord.phone_number == phone,
                AppointmentRecord.preferred_date == date,
                AppointmentRecord.status.in_(["pending", "confirmed"])
            ).all()
            
            session.close()
            
            return [
                {
                    "appointment_id": apt.appointment_id,
                    "time": apt.preferred_time,
                    "status": apt.status
                }
                for apt in appointments
            ]
        except Exception as e:
            logger.error(f"Error checking conflicts: {e}")
            return []


# ============================================
# RESCHEDULING MANAGER
# ============================================

class ReschedulingManager:
    """Manages appointment rescheduling requests."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.history_manager = AppointmentHistoryManager(db_manager)
        self.notification_manager = NotificationManager(db_manager)
    
    def create_reschedule_request(self, appointment_id: str, new_date: str,
                                 new_time: str, reason: str = "customer_request") -> ReschedulingRequest:
        """Create a reschedule request."""
        try:
            session = self.db.Session()
            apt = session.query(AppointmentRecord).filter_by(
                appointment_id=appointment_id
            ).first()
            
            if not apt:
                session.close()
                raise ValueError("Appointment not found")
            
            reschedule_req = ReschedulingRequest(
                appointment_id=appointment_id,
                original_date=apt.preferred_date,
                original_time=apt.preferred_time,
                new_date=new_date,
                new_time=new_time,
                reason=RescheduleReason(reason),
                requested_by="customer"
            )
            
            reschedule_record = ReschedulingRecord(
                reschedule_id=reschedule_req.reschedule_id,
                appointment_id=appointment_id,
                original_date=apt.preferred_date,
                original_time=apt.preferred_time,
                new_date=new_date,
                new_time=new_time,
                reason=reason,
                requested_by="customer",
                status="pending"
            )
            
            session.add(reschedule_record)
            session.commit()
            session.close()
            
            logger.info(f"Created reschedule request {reschedule_req.reschedule_id}")
            return reschedule_req
        except Exception as e:
            logger.error(f"Error creating reschedule request: {e}")
            raise
    
    def approve_reschedule(self, reschedule_id: str) -> Tuple[bool, str]:
        """Approve and apply a reschedule request."""
        try:
            session = self.db.Session()
            reschedule = session.query(ReschedulingRecord).filter_by(
                reschedule_id=reschedule_id
            ).first()
            
            if not reschedule:
                session.close()
                return False, "Reschedule request not found"
            
            apt = session.query(AppointmentRecord).filter_by(
                appointment_id=reschedule.appointment_id
            ).first()
            
            if not apt:
                session.close()
                return False, "Appointment not found"
            
            # Update appointment
            old_date_time = f"{apt.preferred_date} {apt.preferred_time}"
            apt.preferred_date = reschedule.new_date
            apt.preferred_time = reschedule.new_time
            apt.updated_at = datetime.now()
            
            # Update reschedule record
            reschedule.status = "approved"
            reschedule.approved_at = datetime.now()
            
            session.commit()
            session.close()
            
            # Send notification
            new_date_time = f"{reschedule.new_date} {reschedule.new_time}"
            self.notification_manager.send_reschedule_notice(
                reschedule.appointment_id,
                old_date_time,
                new_date_time,
                apt.phone_number
            )
            
            # Record in history
            self.history_manager.record_event(
                reschedule.appointment_id,
                apt.phone_number,
                "rescheduled",
                f"เปลี่ยนเป็น {new_date_time}"
            )
            
            return True, "Reschedule approved"
        except Exception as e:
            logger.error(f"Error approving reschedule: {e}")
            return False, str(e)


# ============================================
# CANCELLATION MANAGER
# ============================================

class CancellationManager:
    """Manages appointment cancellations."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.history_manager = AppointmentHistoryManager(db_manager)
        self.notification_manager = NotificationManager(db_manager)
    
    def cancel_appointment(self, appointment_id: str, reason: str = "customer_request") -> Tuple[bool, str]:
        """Cancel an appointment."""
        try:
            session = self.db.Session()
            apt = session.query(AppointmentRecord).filter_by(
                appointment_id=appointment_id
            ).first()
            
            if not apt:
                session.close()
                return False, "Appointment not found"
            
            if apt.status == "cancelled":
                session.close()
                return False, "Appointment already cancelled"
            
            # Create cancellation record
            cancellation = CancellationRecord(
                cancellation_id=f"CANCEL-{str(uuid.uuid4())[:8]}",
                appointment_id=appointment_id,
                reason=reason,
                cancelled_by="customer",
                cancelled_at=datetime.now()
            )
            
            # Update appointment
            apt.status = "cancelled"
            apt.updated_at = datetime.now()
            
            session.add(cancellation)
            session.commit()
            session.close()
            
            # Send notification
            message = f"""✓ นัดหมายของคุณถูกยกเลิก
เลขที่นัดหมาย: {appointment_id}
สาเหตุ: {reason}"""
            
            self.notification_manager.create_notification(
                appointment_id,
                NotificationType.CANCELLATION_NOTICE,
                apt.phone_number,
                message
            )
            
            # Record in history
            self.history_manager.record_event(
                appointment_id,
                apt.phone_number,
                "cancelled",
                reason
            )
            
            return True, "Appointment cancelled"
        except Exception as e:
            logger.error(f"Error cancelling appointment: {e}")
            return False, str(e)


# ============================================
# APPOINTMENT HISTORY MANAGER
# ============================================

class AppointmentHistoryManager:
    """Manages appointment history tracking."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
    
    def record_event(self, appointment_id: str, phone_number: str,
                    event_type: str, notes: Optional[str] = None):
        """Record an appointment event in history."""
        try:
            history = AppointmentHistoryRecord(
                history_id=f"HIST-{str(uuid.uuid4())[:8]}",
                appointment_id=appointment_id,
                phone_number=phone_number,
                event_type=event_type,
                notes=notes,
                event_date=datetime.now()
            )
            
            session = self.db.Session()
            session.add(history)
            session.commit()
            session.close()
            
            logger.info(f"Recorded event: {event_type} for {appointment_id}")
        except Exception as e:
            logger.error(f"Error recording history: {e}")
    
    def get_customer_history(self, phone_number: str, limit: int = 10) -> List[Dict]:
        """Get appointment history for a customer."""
        try:
            session = self.db.Session()
            history = session.query(AppointmentHistoryRecord).filter_by(
                phone_number=phone_number
            ).order_by(
                AppointmentHistoryRecord.event_date.desc()
            ).limit(limit).all()
            
            session.close()
            
            return [
                {
                    "appointment_id": h.appointment_id,
                    "event_type": h.event_type,
                    "event_date": h.event_date.isoformat(),
                    "notes": h.notes
                }
                for h in history
            ]
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []


# ============================================
# SMART SLOT SUGGESTER
# ============================================

class SmartSlotSuggester:
    """Suggests best appointment slots based on availability and history."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.availability_manager = AppointmentAvailabilityManager(db_manager)
    
    def get_recommended_slots(self, department_id: str, phone_number: str,
                             num_suggestions: int = 5) -> List[AppointmentSlot]:
        """Get recommended appointment slots for customer."""
        try:
            # Get available dates
            available_dates = self.availability_manager.get_available_dates(department_id, days_ahead=14)
            
            if not available_dates:
                return []
            
            # Sort dates and pick top ones
            recommended = []
            for date_str in available_dates[:5]:
                slots = self.availability_manager.get_available_slots(department_id, date_str)
                # Prefer early morning and mid-afternoon slots
                for slot in slots:
                    hour = int(slot.start_time.split(":")[0])
                    if hour in [9, 10, 14, 15]:  # Preferred hours
                        recommended.append(slot)
                        if len(recommended) >= num_suggestions:
                            break
                
                if len(recommended) >= num_suggestions:
                    break
            
            return recommended[:num_suggestions]
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []


# ============================================
# APPOINTMENT COLLECTOR
# ============================================

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
                "field_name": "email",
                "prompt": "📧 กรุณาระบุอีเมลของคุณ (ถ้าไม่มีพิมพ์ 'ไม่มี'):",
                "required": False
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
        """Process user input for current step."""
        current_step = state.steps[state.current_step]
        field_name = current_step.field_name
        
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
        
        elif field_name == "email":
            email_input = user_input.strip()
            if email_input.lower() == "ไม่มี":
                state.collected_data["email"] = None
                return True, f"✓ ไม่ระบุอีเมล\n"
            is_valid, value = self.validator.is_valid_email(email_input)
            if not is_valid:
                return False, f"❌ {value}\n💬 ลองใหม่ครับ:"
            state.collected_data["email"] = value
            return True, f"✓ อีเมล: {value}\n"
        
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
            email=state.collected_data.get("email"),
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
            
            logger.info(f"Created appointment {appointment.appointment_id}")
            return appointment
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise


# ============================================
# ENHANCED BOOKING APPOINTMENT AGENT
# ============================================

class BookingAppointmentAgent:
    """Enhanced Appointment Booking Agent with full lifecycle management."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.collector = AppointmentCollector(db_manager)
        self.availability_manager = AppointmentAvailabilityManager(db_manager)
        self.notification_manager = NotificationManager(db_manager)
        self.reschedule_manager = ReschedulingManager(db_manager)
        self.cancellation_manager = CancellationManager(db_manager)
        self.history_manager = AppointmentHistoryManager(db_manager)
        self.slot_suggester = SmartSlotSuggester(db_manager)
        self.duplicate_manager = DuplicatePreventionManager(db_manager)
    
    async def process_task(self, task: TaskRequest) -> TaskResponse:
        """Process appointment booking task with comprehensive features."""
        task_id = task.task_id
        
        try:
            if task.action == TaskAction.COLLECT_INFO:
                return await self._handle_collect_info(task)
            elif task.action == TaskAction.BOOK_APPOINTMENT:
                return await self._handle_book_appointment(task)
            elif task.action == TaskAction.MANAGE_APPOINTMENT:
                return await self._handle_manage_appointment(task)
            elif task.action == TaskAction.CHECK_AVAILABILITY:
                return await self._handle_check_availability(task)
            elif task.action == TaskAction.RESCHEDULE:
                return await self._handle_reschedule(task)
            elif task.action == TaskAction.CANCEL_APPOINTMENT:
                return await self._handle_cancel(task)
            elif task.action == TaskAction.VIEW_HISTORY:
                return await self._handle_view_history(task)
            elif task.action == TaskAction.GET_RECOMMENDATIONS:
                return await self._handle_get_recommendations(task)
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
                appointment = self.collector.create_appointment(state, session_id)
                
                # Send confirmation SMS
                self.notification_manager.send_confirmation_sms(appointment)
                
                # Record in history
                self.history_manager.record_event(
                    appointment.appointment_id,
                    appointment.phone_number,
                    "booked"
                )
                
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
        """Handle direct appointment booking."""
        task_id = task.task_id
        payload = task.payload
        
        required_fields = ["first_name", "last_name", "phone_number", "preferred_date", "preferred_time"]
        missing_fields = [f for f in required_fields if f not in payload or not payload[f]]
        
        if missing_fields:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.NEEDS_CLARIFICATION,
                artifacts={"missing_fields": missing_fields},
                error_message=f"ขาดข้อมูล: {', '.join(missing_fields)}"
            )
        
        # Check for duplicates
        is_duplicate, duplicate_id = self.duplicate_manager.check_duplicate(
            payload["phone_number"],
            payload["preferred_date"],
            payload["preferred_time"]
        )
        
        if is_duplicate:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": f"Duplicate appointment {duplicate_id}"},
                error_message="คุณมีการจองนัดหมายที่เดียวกันแล้ว"
            )
        
        try:
            appointment = AppointmentInfo(
                first_name=payload["first_name"],
                last_name=payload["last_name"],
                phone_number=payload["phone_number"],
                email=payload.get("email"),
                preferred_date=payload["preferred_date"],
                preferred_time=payload["preferred_time"],
                notes=payload.get("notes"),
                status=AppointmentStatus.CONFIRMED,
                created_by_session=payload.get("session_id")
            )
            
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
            
            # Send confirmation
            self.notification_manager.send_confirmation_sms(appointment)
            self.history_manager.record_event(
                appointment.appointment_id,
                appointment.phone_number,
                "booked"
            )
            
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
    
    async def _handle_check_availability(self, task: TaskRequest) -> TaskResponse:
        """Check available appointment slots."""
        task_id = task.task_id
        department_id = task.payload.get("department_id")
        date = task.payload.get("date")
        
        try:
            if date:
                slots = self.availability_manager.get_available_slots(department_id, date)
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "available_slots": [
                            {
                                "slot_id": s.slot_id,
                                "date": s.date,
                                "time": s.start_time,
                                "capacity": s.capacity - s.booked_count
                            }
                            for s in slots
                        ]
                    }
                )
            else:
                available_dates = self.availability_manager.get_available_dates(department_id)
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "available_dates": available_dates
                    }
                )
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message="ไม่สามารถตรวจสอบความพร้อมได้"
            )
    
    async def _handle_reschedule(self, task: TaskRequest) -> TaskResponse:
        """Handle appointment rescheduling."""
        task_id = task.task_id
        appointment_id = task.payload.get("appointment_id")
        new_date = task.payload.get("new_date")
        new_time = task.payload.get("new_time")
        
        try:
            reschedule_req = self.reschedule_manager.create_reschedule_request(
                appointment_id, new_date, new_time
            )
            
            success, message = self.reschedule_manager.approve_reschedule(
                reschedule_req.reschedule_id
            )
            
            if success:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "reschedule_id": reschedule_req.reschedule_id,
                        "new_date": new_date,
                        "new_time": new_time,
                        "message": "เปลี่ยนแปลงนัดหมายสำเร็จ"
                    }
                )
            else:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": message},
                    error_message="ไม่สามารถเปลี่ยนแปลงนัดหมายได้"
                )
        except Exception as e:
            logger.error(f"Error rescheduling: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message="เกิดข้อผิดพลาดในการเปลี่ยนแปลง"
            )
    
    async def _handle_cancel(self, task: TaskRequest) -> TaskResponse:
        """Handle appointment cancellation."""
        task_id = task.task_id
        appointment_id = task.payload.get("appointment_id")
        reason = task.payload.get("reason", "customer_request")
        
        try:
            success, message = self.cancellation_manager.cancel_appointment(
                appointment_id, reason
            )
            
            if success:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "appointment_id": appointment_id,
                        "message": "ยกเลิกนัดหมายสำเร็จ"
                    }
                )
            else:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": message},
                    error_message="ไม่สามารถยกเลิกนัดหมายได้"
                )
        except Exception as e:
            logger.error(f"Error cancelling: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message="เกิดข้อผิดพลาดในการยกเลิก"
            )
    
    async def _handle_view_history(self, task: TaskRequest) -> TaskResponse:
        """Get appointment history for customer."""
        task_id = task.task_id
        phone_number = task.payload.get("phone_number")
        
        try:
            history = self.history_manager.get_customer_history(phone_number)
            
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "phone_number": phone_number,
                    "history": history,
                    "total_count": len(history)
                }
            )
        except Exception as e:
            logger.error(f"Error viewing history: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message="ไม่สามารถดึงประวัติได้"
            )
    
    async def _handle_get_recommendations(self, task: TaskRequest) -> TaskResponse:
        """Get recommended appointment slots."""
        task_id = task.task_id
        department_id = task.payload.get("department_id")
        phone_number = task.payload.get("phone_number")
        
        try:
            recommendations = self.slot_suggester.get_recommended_slots(
                department_id, phone_number
            )
            
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "recommended_slots": [
                        {
                            "slot_id": s.slot_id,
                            "date": s.date,
                            "time": s.start_time,
                            "available_capacity": s.capacity - s.booked_count
                        }
                        for s in recommendations
                    ]
                }
            )
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message="ไม่สามารถรับคำแนะนำได้"
            )
    
    async def _handle_manage_appointment(self, task: TaskRequest) -> TaskResponse:
        """Generic appointment management (backward compatibility)."""
        task_id = task.task_id
        operation = task.payload.get("operation")
        appointment_id = task.payload.get("appointment_id")
        
        if operation == "check_status":
            try:
                session = self.db.Session()
                apt = session.query(AppointmentRecord).filter_by(
                    appointment_id=appointment_id
                ).first()
                session.close()
                
                if not apt:
                    return TaskResponse(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        artifacts={"error": "Appointment not found"},
                        error_message="ไม่พบนัดหมาย"
                    )
                
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "appointment_id": appointment_id,
                        "status": apt.status,
                        "date": apt.preferred_date,
                        "time": apt.preferred_time,
                        "customer": f"{apt.first_name} {apt.last_name}"
                    }
                )
            except Exception as e:
                return TaskResponse(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": str(e)},
                    error_message="เกิดข้อผิดพลาด"
                )
        else:
            return TaskResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": f"Unknown operation: {operation}"},
                error_message="ไม่รองรับคำสั่งนี้"
            )


# Ensure UUID is imported
import uuid
