"""
system_control_agent.py - Phase 8: System Control & Monitoring Agent
Inspired by mission-control architecture: agent lifecycle, task routing, real-time monitoring.
"""

from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncio
import uuid
from database import DBManager
from schemas import TaskRequest, TaskResponse, TaskStatus, AgentRole, TaskAction
from utils.logger import logger
from utils.resilience import retry_async, CONFIG_API_CALL


# --- Enums for Agent State Management ---

class AgentStatus(str, Enum):
    """Agent operational state (similar to mission-control)"""
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class TaskPriority(str, Enum):
    """Task execution priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    URGENT = "urgent"


class RiskLevel(str, Enum):
    """Execution risk assessment (similar to exec-approvals)"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --- Data Models ---

@dataclass
class AgentHealthMetric:
    """Real-time health snapshot for an agent"""
    agent_role: str
    status: AgentStatus
    last_heartbeat: datetime
    task_count: int
    error_count: int
    avg_duration_ms: float
    success_rate: float  # 0.0-1.0
    token_usage: Dict[str, int]
    memory_usage_pct: float
    last_error: Optional[str] = None


@dataclass
class ControlCommand:
    """Instruction to control/configure an agent"""
    command_id: str
    agent_role: str
    command_type: str  # "pause", "resume", "reconfigure", "restart", "execute_task"
    payload: Dict[str, Any]
    priority: TaskPriority
    created_at: datetime
    executed_at: Optional[datetime] = None
    status: str = "pending"  # pending, accepted, executed, failed


@dataclass
class SystemAlert:
    """Alert triggered by monitoring thresholds"""
    alert_id: str
    severity: str  # "info", "warning", "critical"
    message: str
    agent_role: Optional[str]
    metric: str
    threshold_value: float
    actual_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None


@dataclass
class ExecutionApproval:
    """Risk gating for agent task execution (similar to mission-control)"""
    approval_id: str
    agent_role: str
    action: str
    payload: Dict[str, Any]
    risk_level: RiskLevel
    status: str = "pending"  # pending, approved, denied, expired
    created_at: datetime = None
    expires_at: datetime = None
    approved_by: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=5)


# --- System Control Agent ---

class SystemControlAgent:
    """
    Master control plane for the multi-agent system.
    Responsibilities:
    - Monitor agent health & performance
    - Route & prioritize tasks
    - Execute approval gates (risk assessment)
    - Coordinate inter-agent communication
    - Auto-remediation (restart degraded agents, rebalance load)
    """

    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.health_metrics: Dict[str, AgentHealthMetric] = {}
        self.pending_commands: Dict[str, ControlCommand] = {}
        self.active_alerts: Dict[str, SystemAlert] = {}
        self.pending_approvals: Dict[str, ExecutionApproval] = {}
        
        # Configuration thresholds
        self.health_thresholds = {
            "max_error_rate": 0.3,  # 30% error rate triggers alert
            "max_avg_duration_ms": 30000,  # 30 seconds
            "max_memory_pct": 85.0,
            "heartbeat_timeout_sec": 300,  # 5 minutes
        }

    def register_agent(self, agent_role: str, metadata: Dict[str, Any]) -> bool:
        """Register an agent with the control plane."""
        self.agent_registry[agent_role] = {
            "role": agent_role,
            "status": AgentStatus.IDLE,
            "registered_at": datetime.now().isoformat(),
            "metadata": metadata,
            "task_queue": []
        }
        logger.info(f"✓ Agent registered | Role: {agent_role}")
        return True

    async def execute_with_approval_gate(
        self, 
        agent_role: str, 
        action: str,
        payload: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Risk-gated execution: assess risk and require approval if needed.
        Returns (approved, approval_id or reason)
        """
        # Risk assessment logic
        risk_level = self._assess_execution_risk(agent_role, action, payload)
        
        # Create approval request
        approval = ExecutionApproval(
            approval_id=str(uuid.uuid4()),
            agent_role=agent_role,
            action=action,
            payload=payload,
            risk_level=risk_level,
        )
        
        self.pending_approvals[approval.approval_id] = approval
        
        # Auto-approve low-risk actions
        if risk_level == RiskLevel.LOW:
            logger.info(f"✓ Auto-approved low-risk action | Agent: {agent_role} | Action: {action}")
            return True, None
        
        # Log high-risk actions for human review
        logger.warning(f"⚠️ High-risk execution gated | Agent: {agent_role} | Risk: {risk_level} | ID: {approval.approval_id}")
        return False, approval.approval_id

    def _assess_execution_risk(self, agent_role: str, action: str, payload: Dict[str, Any]) -> RiskLevel:
        """
        Assess risk of agent action using pattern matching.
        Similar to mission-control's exec-approvals logic.
        """
        # Check for dangerous patterns
        dangerous_patterns = {
            "delete": RiskLevel.HIGH,
            "modify_system": RiskLevel.CRITICAL,
            "execute_shell": RiskLevel.HIGH,
            "access_secrets": RiskLevel.HIGH,
            "modify_config": RiskLevel.MEDIUM,
            "create_task": RiskLevel.LOW,
            "research": RiskLevel.LOW,
            "analyze": RiskLevel.LOW,
        }
        
        risk = dangerous_patterns.get(action, RiskLevel.MEDIUM)
        
        # Escalate if agent is in degraded state
        if self.health_metrics.get(agent_role, {}).status == AgentStatus.DEGRADED:
            risk = RiskLevel(min(risk.value + 1, RiskLevel.CRITICAL.value))
        
        return risk

    def approve_execution(self, approval_id: str, approved_by: str) -> bool:
        """Approve pending execution request."""
        approval = self.pending_approvals.get(approval_id)
        if not approval:
            logger.warning(f"Approval not found: {approval_id}")
            return False
        
        approval.status = "approved"
        approval.approved_by = approved_by
        logger.info(f"✓ Execution approved | ID: {approval_id} | By: {approved_by}")
        return True

    def deny_execution(self, approval_id: str, reason: str) -> bool:
        """Deny pending execution request."""
        approval = self.pending_approvals.get(approval_id)
        if not approval:
            return False
        
        approval.status = "denied"
        logger.warning(f"❌ Execution denied | ID: {approval_id} | Reason: {reason}")
        return True

    async def monitor_agent_health(self, agent_role: str) -> AgentHealthMetric:
        """
        Continuous health monitoring with thresholds and alerting.
        Similar to mission-control's diagnostics endpoint.
        """
        # Fetch metrics from DB
        session = self.db.Session()
        try:
            from database import ExecutionMetricsRecord
            metrics = session.query(ExecutionMetricsRecord)\
                .filter(ExecutionMetricsRecord.agent_role == agent_role)\
                .order_by(ExecutionMetricsRecord.created_at.desc())\
                .limit(100).all()
            
            if not metrics:
                # No metrics yet, assume healthy
                metric = AgentHealthMetric(
                    agent_role=agent_role,
                    status=AgentStatus.IDLE,
                    last_heartbeat=datetime.now(),
                    task_count=0,
                    error_count=0,
                    avg_duration_ms=0.0,
                    success_rate=1.0,
                    token_usage={"prompt": 0, "completion": 0},
                    memory_usage_pct=0.0
                )
                self.health_metrics[agent_role] = metric
                return metric
            
            # Calculate aggregates
            successful = sum(1 for m in metrics if m.success)
            failed = len(metrics) - successful
            total_duration = sum(m.duration_seconds or 0 for m in metrics)
            avg_duration_ms = (total_duration / len(metrics) * 1000) if metrics else 0
            success_rate = successful / len(metrics) if metrics else 1.0
            
            # Aggregate token usage
            total_prompt_tokens = sum(m.prompt_tokens or 0 for m in metrics)
            total_completion_tokens = sum(m.completion_tokens or 0 for m in metrics)
            
            metric = AgentHealthMetric(
                agent_role=agent_role,
                status=self._determine_agent_status(success_rate, avg_duration_ms, failed),
                last_heartbeat=datetime.now(),
                task_count=len(metrics),
                error_count=failed,
                avg_duration_ms=avg_duration_ms,
                success_rate=success_rate,
                token_usage={
                    "prompt_tokens": total_prompt_tokens,
                    "completion_tokens": total_completion_tokens
                },
                memory_usage_pct=0.0,  # Would be populated by agent heartbeat
            )
            
            self.health_metrics[agent_role] = metric
            
            # Check thresholds and raise alerts
            self._check_health_thresholds(metric)
            
            return metric
        finally:
            session.close()

    def _determine_agent_status(self, success_rate: float, avg_duration_ms: float, error_count: int) -> AgentStatus:
        """Determine operational status based on metrics."""
        if error_count > 5 and success_rate < 0.5:
            return AgentStatus.ERROR
        elif success_rate < 0.7 or avg_duration_ms > self.health_thresholds["max_avg_duration_ms"]:
            return AgentStatus.DEGRADED
        elif error_count > 0:
            return AgentStatus.DEGRADED
        else:
            return AgentStatus.IDLE

    def _check_health_thresholds(self, metric: AgentHealthMetric):
        """Check health metrics against configured thresholds."""
        error_rate = metric.error_count / metric.task_count if metric.task_count > 0 else 0
        
        if error_rate > self.health_thresholds["max_error_rate"]:
            self._raise_alert(
                severity="critical",
                message=f"High error rate detected",
                agent_role=metric.agent_role,
                metric="error_rate",
                threshold_value=self.health_thresholds["max_error_rate"],
                actual_value=error_rate
            )
        
        if metric.avg_duration_ms > self.health_thresholds["max_avg_duration_ms"]:
            self._raise_alert(
                severity="warning",
                message=f"Slow execution detected",
                agent_role=metric.agent_role,
                metric="avg_duration_ms",
                threshold_value=self.health_thresholds["max_avg_duration_ms"],
                actual_value=metric.avg_duration_ms
            )

    def _raise_alert(
        self,
        severity: str,
        message: str,
        agent_role: Optional[str],
        metric: str,
        threshold_value: float,
        actual_value: float
    ):
        """Raise a system alert."""
        alert = SystemAlert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            message=message,
            agent_role=agent_role,
            metric=metric,
            threshold_value=threshold_value,
            actual_value=actual_value,
            triggered_at=datetime.now()
        )
        self.active_alerts[alert.alert_id] = alert
        logger.warning(f"🚨 Alert raised | {severity.upper()} | {message} | {metric}: {actual_value:.2f}/{threshold_value:.2f}")

    async def auto_remediate_degraded_agent(self, agent_role: str) -> bool:
        """
        Auto-remediation: attempt to recover degraded agent.
        Steps: reconfigure, clear cache, restart if needed.
        """
        logger.warning(f"🔧 Auto-remediation triggered | Agent: {agent_role}")
        
        # Step 1: Clear configuration cache
        cache_key = f"config_{agent_role}"
        self.db.clear_cache()
        logger.info(f"  - Cleared config cache")
        
        # Step 2: Reset rate limiting (if applicable)
        # Step 3: Create restart command
        restart_cmd = ControlCommand(
            command_id=str(uuid.uuid4()),
            agent_role=agent_role,
            command_type="restart",
            payload={"reason": "auto_remediation"},
            priority=TaskPriority.URGENT,
            created_at=datetime.now()
        )
        
        self.pending_commands[restart_cmd.command_id] = restart_cmd
        logger.info(f"  - Restart command queued: {restart_cmd.command_id}")
        
        return True

    def get_system_dashboard(self) -> Dict[str, Any]:
        """
        Comprehensive system status dashboard.
        Similar to mission-control's 31 dashboard panels.
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                role: {
                    "status": metric.status.value,
                    "health": {
                        "success_rate": f"{metric.success_rate * 100:.1f}%",
                        "avg_duration_ms": f"{metric.avg_duration_ms:.0f}",
                        "error_count": metric.error_count,
                        "task_count": metric.task_count,
                    },
                    "tokens": metric.token_usage,
                    "last_heartbeat": metric.last_heartbeat.isoformat(),
                }
                for role, metric in self.health_metrics.items()
            },
            "alerts": {
                alert_id: {
                    "severity": alert.severity,
                    "message": alert.message,
                    "agent": alert.agent_role,
                    "metric": alert.metric,
                    "triggered_at": alert.triggered_at.isoformat(),
                }
                for alert_id, alert in self.active_alerts.items()
            },
            "pending_commands": len(self.pending_commands),
            "pending_approvals": len(self.pending_approvals),
        }

    def get_agent_communication_graph(self) -> Dict[str, Any]:
        """
        Analyze inter-agent communication patterns.
        Similar to mission-control's comms graph.
        """
        session = self.db.Session()
        try:
            from database import TaskRecord, ArtifactRecord
            
            # Get all task dependencies
            tasks = session.query(TaskRecord).all()
            
            edges = []
            for task in tasks:
                if task.parent_task_id:
                    edges.append({
                        "from": "system",  # or parent task's agent
                        "to": task.agent_role,
                        "count": 1,
                        "task_id": task.task_id
                    })
            
            return {
                "nodes": [
                    {"id": role, "label": role, "size": len(self.health_metrics.get(role, {}))}
                    for role in self.agent_registry.keys()
                ],
                "edges": edges,
                "communication_pattern": "DAG with multi-hop dependencies"
            }
        finally:
            session.close()

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        System Control Agent's main execution method.
        Routes control operations: monitoring, approval, remediation.
        """
        action = request.action
        payload = request.payload
        
        try:
            if action == TaskAction.MONITOR:
                # Health check operation
                agent_to_monitor = payload.get("agent_role")
                
                # Run monitoring asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                metric = loop.run_until_complete(self.monitor_agent_health(agent_to_monitor))
                
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "dashboard": self.get_system_dashboard(),
                        "agent_health": asdict(metric),
                        "comms_graph": self.get_agent_communication_graph()
                    },
                    meta={
                        "operation": "system_monitoring",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            elif action == TaskAction.AUDIT:
                # Approval gate check
                agent_role = payload.get("agent_role")
                action_type = payload.get("action_type")
                action_payload = payload.get("action_payload", {})
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                approved, approval_id = loop.run_until_complete(
                    self.execute_with_approval_gate(agent_role, action_type, action_payload)
                )
                
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "approved": approved,
                        "approval_id": approval_id,
                        "risk_assessment": self._assess_execution_risk(agent_role, action_type, action_payload).value
                    },
                    meta={
                        "operation": "execution_approval"
                    }
                )
            
            else:
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": f"Unknown control action: {action}"},
                    error_message=f"Action {action} not supported"
                )
        
        except Exception as e:
            logger.exception(f"System Control Agent Error: {e}")
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message=str(e)
            )
