"""
schemas.py - The Contract Layer
Defines strict data models for all agent communications.
"""

from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid


# --- Enums for strict routing ---
class AgentRole(str, Enum):
    ORCHESTRATOR = "agent_orchestrator"
    KNOWLEDGE_ARCHITECT = "knowledge_architect"
    SYNTHESIS_EXPERT = "integrative_synthesis_expert"
    SOCIAL_MASTERY = "social_media_mastery"
    SRE_ENGINEER = "self_evolving_sre"
    QA_AUDITOR = "qa_auditor"
    VISUAL_DESIGNER = "visual_design_agent"
    BOOKING_AGENT = "booking_appointment_agent"
    ACCOUNTING_AGENT = "accounting_data_agent"


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_CLARIFICATION = "needs_clarification"
    WAITING_FOR_APPROVAL = "waiting_for_approval"


class TaskAction(str, Enum):
    RESEARCH = "research"
    ANALYZE = "analyze"
    CREATE = "create"
    MONITOR = "monitor"
    DECOMPOSE = "decompose"
    AUDIT = "audit"
    AUDIT_VISUAL = "audit_visual"
    GENERATE_IMAGE = "generate_image"
    OVERLAY_TEXT = "overlay_text"
    DESIGN_LAYOUT = "design_layout"
    BOOK_APPOINTMENT = "book_appointment"
    PROCESS_FINANCIAL_DOCUMENT = "process_financial_document"
    VERIFY_FINANCIAL_RECORD = "verify_financial_record"
    MANAGE_APPOINTMENT = "manage_appointment"
    COLLECT_INFO = "collect_info"
    CHECK_AVAILABILITY = "check_availability"
    RESCHEDULE = "reschedule"
    CANCEL_APPOINTMENT = "cancel_appointment"
    VIEW_HISTORY = "view_history"
    GET_RECOMMENDATIONS = "get_recommendations"


class AppointmentStatus(str, Enum):
    PENDING = "pending"
    WAITING_FOR_ADMIN = "waiting_for_admin"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentType(str, Enum):
    CONSULTATION = "consultation"
    TREATMENT = "treatment"
    FOLLOW_UP = "follow_up"
    OTHER = "other"


class NotificationType(str, Enum):
    SMS_CONFIRMATION = "sms_confirmation"
    EMAIL_CONFIRMATION = "email_confirmation"
    SMS_REMINDER = "sms_reminder"
    EMAIL_REMINDER = "email_reminder"
    RESCHEDULE_NOTICE = "reschedule_notice"
    CANCELLATION_NOTICE = "cancellation_notice"


class RescheduleReason(str, Enum):
    CUSTOMER_REQUEST = "customer_request"
    CONFLICT = "conflict"
    ADMIN_REQUEST = "admin_request"
    NO_SHOW = "no_show"
    OTHER = "other"


class CancellationReason(str, Enum):
    CUSTOMER_REQUEST = "customer_request"
    ADMIN_REQUEST = "admin_request"
    NO_SHOW = "no_show"
    CLINIC_CLOSED = "clinic_closed"
    OTHER = "other"


# --- Core Models ---

class TaskRequest(BaseModel):
    """The envelope sent by the Orchestrator to a Specialist Agent."""
    model_config = ConfigDict(strict=True)

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: Optional[str] = Field(default=None, description="Unique ID to trace the request across agents")
    priority: TaskPriority = TaskPriority.MEDIUM
    agent_role: AgentRole
    action: TaskAction
    payload: Dict[str, Any] = Field(description="The actual content/instructions for the agent")
    constraints: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    agent_config: Optional[Dict[str, Any]] = Field(default=None, description="Persistent config from DB (system_prompt, temperature, max_tokens, version)")

    def validate_payload(self):
        """Strict validation for the payload content."""
        if not self.payload:
            raise ValueError("Payload cannot be empty")
        
        # Ensure instruction is present for most actions
        if self.action in [TaskAction.RESEARCH, TaskAction.ANALYZE, TaskAction.CREATE]:
            if "instruction" not in self.payload and "user_input" not in self.payload:
                raise ValueError(f"Action {self.action} requires 'instruction' or 'user_input' in payload")
        
        # Prevent excessively long inputs to avoid API timeouts/costs
        content_str = str(self.payload)
        if len(content_str) > 50000:
            raise ValueError("Payload content exceeds maximum allowed size (50,000 chars)")


class TaskResponse(BaseModel):
    """The envelope returned by a Specialist Agent to the Orchestrator."""
    model_config = ConfigDict(strict=True)

    task_id: str
    status: TaskStatus
    artifacts: Dict[str, Any] = Field(
        description="Dictionary containing 'primary_output', 'supporting_data', etc."
    )
    meta: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Confidence scores, token usage, and execution time"
    )
    error_message: Optional[str] = None

    def get_token_usage(self) -> Dict[str, int]:
        """Helper to extract token usage from meta."""
        if not self.meta:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        usage = self.meta.get("token_usage", {})
        return usage if isinstance(usage, dict) else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class ProgressUpdate(BaseModel):
    """Model for streaming progress updates to the user."""
    task_id: str
    step_number: int
    total_steps: int
    agent_role: str
    status: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class RoutingDecision(BaseModel):
    """Output from the Local Router."""
    assigned_agent: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    escalate_to_cloud: bool = False
    task_id: Optional[str] = None


class SubTask(BaseModel):
    """Individual step in a decomposed plan."""
    step_number: int
    agent_role: str
    action: str
    instruction: str
    depends_on: List[int] = []


class MasterPlan(BaseModel):
    """High-level plan decomposed by Cloud Brain."""
    plan_id: str
    total_steps: int
    dag: List[SubTask]
    expected_outcome: str


class AgentRegistry(BaseModel):
    """Definition of what each agent can do."""
    role: AgentRole
    capabilities: List[str]
    endpoint: str
    is_active: bool = True
    health_status: str = "healthy"


class FactCheckResult(BaseModel):
    """Result of fact-checking a claim."""
    claim: str
    verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class BiasAnalysis(BaseModel):
    """Bias detection analysis result."""
    content: str
    bias_detected: bool
    bias_score: float = Field(ge=0.0, le=1.0)  # 0=no bias, 1=high bias
    bias_categories: List[str] = Field(default_factory=list)  # e.g., ["gender", "political"]
    recommendations: List[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    """Compliance check against brand/safety guidelines."""
    content: str
    compliant: bool
    violation_type: Optional[str] = None
    severity: Optional[str] = Field(default=None)  # "low", "medium", "high"
    details: Optional[str] = None


class AuditResult(BaseModel):
    """Complete audit report from QA Auditor agent."""
    model_config = ConfigDict(strict=False) # Allow flexible dict inputs if needed

    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_to_audit: str
    fact_checks: List[FactCheckResult] = Field(default_factory=list)
    bias_analysis: Optional[BiasAnalysis] = None
    compliance_report: Optional[ComplianceReport] = None
    overall_quality_score: float = Field(ge=0.0, le=1.0)
    recommendation: str  # "approved", "minor_revisions", "major_revisions", "rejected"
    audit_timestamp: datetime = Field(default_factory=datetime.now)


# --- New Strongly Typed Artifact Models ---

class AccountingArtifact(BaseModel):
    """Structured result from AccountingDataAgent."""
    model_config = ConfigDict(strict=False)
    
    summary: str
    details: Dict[str, Any]
    saved_path: str
    upload_result: Dict[str, Optional[str]]
    db_entry_id: str
    document_type: str = "unknown"
    confidence: float = 0.85

class VerificationArtifact(BaseModel):
    """Structured result when verifying a financial record."""
    model_config = ConfigDict(strict=False)
    
    status: str # PASSED, FLAGGED, FAILED
    issue: str
    confidence: float
    discrepancies: List[str] = Field(default_factory=list)


# --- Appointment Booking Models ---

class Department(BaseModel):
    """Represents a clinic/department for appointments."""
    model_config = ConfigDict(strict=False)
    
    department_id: str = Field(default_factory=lambda: f"DEPT-{str(uuid.uuid4())[:8]}")
    name: str = Field(..., description="Department name (e.g., General, Dental, Eye)")
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class ServiceType(BaseModel):
    """Represents a service type for appointments."""
    model_config = ConfigDict(strict=False)
    
    service_id: str = Field(default_factory=lambda: f"SVC-{str(uuid.uuid4())[:8]}")
    department_id: str = Field(..., description="Department this service belongs to")
    name: str = Field(..., description="Service name (e.g., Check-up, Cleaning)")
    duration_minutes: int = Field(default=30, description="Appointment duration in minutes")
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


class AppointmentSlot(BaseModel):
    """Represents an available appointment time slot."""
    model_config = ConfigDict(strict=False)
    
    slot_id: str = Field(default_factory=lambda: f"SLOT-{str(uuid.uuid4())[:8]}")
    department_id: str
    date: str = Field(..., description="Appointment date (YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    capacity: int = Field(default=1, description="Number of available slots")
    booked_count: int = Field(default=0, description="Number of slots already booked")
    is_available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


class Notification(BaseModel):
    """Represents a notification (SMS/Email) to be sent."""
    model_config = ConfigDict(strict=False)
    
    notification_id: str = Field(default_factory=lambda: f"NOTIF-{str(uuid.uuid4())[:8]}")
    appointment_id: str
    notification_type: NotificationType
    recipient: str = Field(..., description="Phone number or email address")
    message: str = Field(..., description="Message content")
    sent_at: Optional[datetime] = None
    delivery_status: str = Field(default="pending")  # pending, sent, failed
    retry_count: int = Field(default=0)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ReschedulingRequest(BaseModel):
    """Request to reschedule an appointment."""
    model_config = ConfigDict(strict=False)
    
    reschedule_id: str = Field(default_factory=lambda: f"RESCHED-{str(uuid.uuid4())[:8]}")
    appointment_id: str
    original_date: str
    original_time: str
    new_date: str
    new_time: str
    reason: RescheduleReason
    reason_notes: Optional[str] = None
    requested_by: str = Field(default="customer")  # customer, admin, system
    status: str = Field(default="pending")  # pending, approved, rejected
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)


class CancellationRequest(BaseModel):
    """Request to cancel an appointment."""
    model_config = ConfigDict(strict=False)
    
    cancellation_id: str = Field(default_factory=lambda: f"CANCEL-{str(uuid.uuid4())[:8]}")
    appointment_id: str
    reason: CancellationReason
    reason_notes: Optional[str] = None
    cancelled_by: str = Field(default="customer")  # customer, admin, system
    cancelled_at: datetime = Field(default_factory=datetime.now)
    refund_eligible: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)


class AppointmentHistoryEntry(BaseModel):
    """Record of appointment history for a customer."""
    model_config = ConfigDict(strict=False)
    
    history_id: str = Field(default_factory=lambda: f"HIST-{str(uuid.uuid4())[:8]}")
    appointment_id: str
    phone_number: str
    event_type: str = Field(..., description="booked, rescheduled, cancelled, completed, no_show")
    event_date: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None


# --- Appointment Booking Models ---

class AppointmentInfo(BaseModel):
    """Customer information for appointment booking."""
    model_config = ConfigDict(strict=False)
    
    appointment_id: str = Field(default_factory=lambda: f"APT-{str(uuid.uuid4())[:8]}")
    first_name: str = Field(..., min_length=1, description="First name of customer")
    last_name: str = Field(..., min_length=1, description="Last name of customer")
    phone_number: str = Field(..., min_length=9, description="Customer contact number")
    email: Optional[str] = Field(default=None, description="Email address (optional)")
    appointment_type: AppointmentType = AppointmentType.CONSULTATION
    preferred_date: str = Field(..., description="Preferred appointment date (YYYY-MM-DD)")
    preferred_time: str = Field(..., description="Preferred appointment time (HH:MM)")
    notes: Optional[str] = Field(default=None, description="Additional notes or requirements")
    status: AppointmentStatus = AppointmentStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by_session: Optional[str] = Field(default=None, description="Session ID that created this appointment")

    def full_name(self) -> str:
        """Returns full name of customer."""
        return f"{self.first_name} {self.last_name}"

    def appointment_datetime(self) -> str:
        """Returns formatted appointment datetime."""
        return f"{self.preferred_date} {self.preferred_time}"


class AppointmentCollectionStep(BaseModel):
    """Represents one step in multi-turn appointment collection."""
    model_config = ConfigDict(strict=False)
    
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    field_name: str = Field(..., description="Field being collected (first_name, last_name, phone_number, preferred_date, preferred_time, notes)")
    prompt: str = Field(..., description="Question to ask user")
    collected_value: Optional[str] = Field(default=None)
    is_valid: bool = Field(default=False)
    validation_message: Optional[str] = Field(default=None)
    required: bool = Field(default=True)


class AppointmentCollectionState(BaseModel):
    """Tracks multi-turn appointment information collection."""
    model_config = ConfigDict(strict=False)
    
    session_id: str
    current_step: int = 0
    collected_data: Dict[str, Any] = Field(default_factory=dict)
    steps: List[AppointmentCollectionStep] = Field(default_factory=list)
    is_complete: bool = False
    appointment: Optional[AppointmentInfo] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
