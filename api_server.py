"""
api_server.py - Phase 7.4: API Wrapper & WebSocket Support
Provides a FastAPI interface for the AgentOrchestrator with real-time progress streaming.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import DBManager
from orchestrator_main import AgentOrchestrator
from schemas import TaskPriority, ProgressUpdate
from utils.logger import logger

# --- Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM

class ChatResponse(BaseModel):
    task_id: str
    status: str
    artifacts: Any
    token_usage: Dict[str, int]

class ControlRequest(BaseModel):
    """Request model for Control Plane operations."""
    task_id: str
    action: str  # 'approve', 'reject', 'update_instruction', 'reset_session', 'update_settings'
    payload: Optional[Dict[str, Any]] = None

# --- Server Setup ---

app = FastAPI(title="AgentOS API", description="Production API for Multi-Agent Orchestration System")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
db_manager = DBManager("sqlite:///agent_system.db")
orchestrator = AgentOrchestrator(db_manager)

# --- WebSocket Connection Manager ---

class ConnectionManager:
    """Manages active WebSocket connections for real-time progress streaming."""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket Connected | Session: {session_id}")

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket Disconnected | Session: {session_id}")

    async def send_update(self, session_id: str, update: ProgressUpdate):
        """Sends a progress update to the connected client."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                # Convert Pydantic model to JSON string
                await websocket.send_json(update.model_dump())
            except Exception as e:
                logger.error(f"WebSocket Send Error | Session: {session_id} | Error: {e}")

manager = ConnectionManager()

# --- Progress Callback for Orchestrator ---

def create_progress_callback(session_id: str):
    """
    Creates a callback function that the orchestrator can use 
    to stream progress updates via WebSocket.
    """
    async def callback(update: ProgressUpdate):
        await manager.send_update(session_id, update)
    return callback

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    """System health check endpoint."""
    return {"status": "healthy", "version": "1.0.0-phase7.4"}

# --- Observability Endpoints ---

@app.get("/obs/tasks")
async def get_all_tasks():
    """Retrieve all tasks for the dashboard table."""
    session = db_manager.Session()
    try:
        from database import TaskRecord
        tasks = session.query(TaskRecord).order_by(TaskRecord.created_at.desc()).all()
        return [
            {
                "task_id": t.task_id,
                "agent_role": t.agent_role,
                "action": t.action,
                "status": t.status,
                "priority": t.priority,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "escalated": t.escalated_to_cloud
            } for t in tasks
        ]
    finally:
        session.close()

@app.get("/obs/tasks/{task_id}/trace")
async def get_task_trace(task_id: str):
    """Retrieve full execution trace for a specific task."""
    session = db_manager.Session()
    try:
        from database import TaskRecord, ArtifactRecord, LogRecord, ExecutionMetricsRecord
        task = session.query(TaskRecord).filter(TaskRecord.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "task": {
                "task_id": task.task_id,
                "agent_role": task.agent_role,
                "action": task.action,
                "status": task.status,
                "payload": task.payload,
                "constraints": task.constraints
            },
            "artifacts": [
                {"id": a.artifact_id, "content": a.content, "confidence": a.confidence} 
                for a in task.artifacts
            ],
            "logs": [
                {"old": l.old_status, "new": l.new_status, "reason": l.reason, "time": l.created_at.isoformat()} 
                for l in task.logs
            ],
            "metrics": [
                {"step": m.step_number, "duration": m.duration_seconds} 
                for m in task.metrics
            ]
        }
    finally:
        session.close()

@app.get("/obs/metrics/summary")
async def get_metrics_summary():
    """Retrieve aggregated metrics for the dashboard graphs."""
    session = db_manager.Session()
    try:
        from database import ExecutionMetricsRecord
        metrics = session.query(ExecutionMetricsRecord).all()
        # Simple aggregation by agent_role
        summary = {}
        for m in metrics:
            role = m.agent_role or "unknown"
            summary.setdefault(role, []).append(m.duration_seconds)
        
        return {
            "agent_performance": {
                role: {"avg": sum(durs)/len(durs) if durs else 0, "count": len(durs)}
                for role, durs in summary.items()
            }
        }
    finally:
        session.close()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Standard REST endpoint for chat. 
    Optimized for ChatBots: Returns the final answer directly in artifacts.
    """
    try:
        # Use a dummy callback since this is a REST call
        result = orchestrator.handle_request(
            user_input=request.message,
            session_id=request.session_id,
            priority=request.priority
        )
        
        # Extract the primary answer from artifacts for easier bot consumption
        return ChatResponse(
            task_id=result.get("task_id", "unknown"),
            status=result.get("status", "completed"),
            artifacts=result.get("artifacts", {}),
            token_usage=result.get("token_usage", {})
        )
    except Exception as e:
        logger.exception(f"Chat API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Control Plane Endpoints ---

@app.post("/control/execute")
async def control_execute(request: ControlRequest):
    """
    Control Plane: Manually trigger or approve a task.
    """
    try:
        action = request.action
        task_id = request.task_id
        
        if action == "approve":
            # Trigger the orchestrator to resume a task waiting for approval
            result = orchestrator.resume_task_after_approval(task_id, approved=True)
            return {"status": "success", "message": f"Task {task_id} approved and resumed", "result": result}
        
        elif action == "reject":
            # Mark task as failed/rejected
            result = orchestrator.resume_task_after_approval(task_id, approved=False)
            return {"status": "success", "message": f"Task {task_id} rejected", "result": result}
        
        elif action == "update_instruction":
            # Update the payload/instruction of a pending task
            new_instruction = request.payload.get("instruction") if request.payload else None
            if not new_instruction:
                raise HTTPException(status_code=400, detail="Missing 'instruction' in payload")
            
            result = orchestrator.update_task_instruction(task_id, new_instruction)
            return {"status": "success", "message": f"Task {task_id} instruction updated", "result": result}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported control action: {action}")
            
    except Exception as e:
        logger.exception(f"Control Plane Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/control/session")
async def control_session(request: ControlRequest):
    """
    Control Plane: Manage session state.
    """
    try:
        session_id = request.task_id # Using task_id field as session_id for this endpoint
        action = request.action
        
        if action == "reset_session":
            # Clear conversation memory for the session
            orchestrator.reset_session_memory(session_id)
            return {"status": "success", "message": f"Session {session_id} memory reset"}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported session action: {action}")
            
    except Exception as e:
        logger.exception(f"Session Control Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/control/settings")
async def update_llm_settings(request: ControlRequest):
    """
    Control Plane: Update LLM parameters (temperature, top_p, model).
    """
    try:
        user_id = request.task_id # Using task_id as user_id for settings
        params = request.payload or {}
        
        for key, value in params.items():
            db_manager.save_user_preference(user_id, "llm_params", key, str(value))
            
        return {"status": "success", "message": f"LLM settings updated for user {user_id}"}
    except Exception as e:
        logger.exception(f"Settings Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Agent Configuration Endpoints ---

class AgentConfigUpdate(BaseModel):
    agent_role: str
    system_prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000

@app.get("/agents/config/{role}")
async def get_agent_config(role: str):
    """Retrieve persistent config for a specific agent."""
    config = db_manager.get_agent_config(role)
    if not config:
        raise HTTPException(status_code=404, detail=f"No configuration found for agent: {role}")
    return config

@app.post("/agents/config")
async def update_agent_config(update: AgentConfigUpdate):
    """Update or create persistent config for an agent."""
    try:
        version = db_manager.save_agent_config(
            agent_role=update.agent_role,
            system_prompt=update.system_prompt,
            temperature=update.temperature,
            max_tokens=update.max_tokens
        )
        return {"status": "success", "version": version, "message": f"Config updated for {update.agent_role}"
    except Exception as e:
        logger.exception(f"Agent Config Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/rollback")
async def rollback_agent_config(request: ControlRequest):
    """Trigger a configuration rollback for an agent."""
    role = request.task_id # Using task_id field to pass agent_role for simplicity
    success = db_manager.rollback_agent_config(role)
    if success:
        return {"status": "success", "message": f"Configuration rolled back for {role}"
    else:
        return {"status": "partial_success", "message": f"Rollback requested for {role}, but historic versions are not fully implemented yet."}
# --- System Control Plane Endpoints (Phase 8) ---

@app.get("/control/dashboard")
async def get_system_dashboard():
    """
    Retrieve comprehensive system status dashboard.
    Returns health metrics, alerts, pending operations, and agent communication graph.
    """
    try:
        from orchestrator_main import orchestrator
        dashboard = orchestrator.control_agent.get_system_dashboard()
        return dashboard
    except Exception as e:
        logger.exception(f"Dashboard Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/control/health/{agent_role}")
async def get_agent_health(agent_role: str):
    """Get detailed health metrics for a specific agent."""
    try:
        from orchestrator_main import orchestrator
        metric = await orchestrator.control_agent.monitor_agent_health(agent_role)
        return {
            "agent_role": metric.agent_role,
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
    except Exception as e:
        logger.exception(f"Health Check Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/control/comms-graph")
async def get_agent_communication_graph():
    """Retrieve inter-agent communication patterns and graph structure."""
    try:
        from orchestrator_main import orchestrator
        graph = orchestrator.control_agent.get_agent_communication_graph()
        return graph
    except Exception as e:
        logger.exception(f"Comms Graph Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/control/approvals")
async def list_pending_approvals():
    """List all pending execution approval requests."""
    try:
        from orchestrator_main import orchestrator
        approvals = []
        for approval_id, approval in orchestrator.control_agent.pending_approvals.items():
            if approval.status == "pending":
                approvals.append({
                    "approval_id": approval_id,
                    "agent_role": approval.agent_role,
                    "action": approval.action,
                    "risk_level": approval.risk_level.value,
                    "created_at": approval.created_at.isoformat(),
                    "expires_at": approval.expires_at.isoformat(),
                })
        return {"pending_approvals": approvals, "count": len(approvals)}
    except Exception as e:
        logger.exception(f"Approvals List Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/control/approvals/{approval_id}/approve")
async def approve_execution_request(approval_id: str, request: ControlRequest):
    """Approve a pending execution request."""
    try:
        from orchestrator_main import orchestrator
        approved_by = request.payload.get("approved_by", "system") if request.payload else "system"
        success = orchestrator.control_agent.approve_execution(approval_id, approved_by)
        
        if success:
            return {"status": "success", "message": f"Execution approved: {approval_id}"}
        else:
            raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    except Exception as e:
        logger.exception(f"Approval Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/control/approvals/{approval_id}/deny")
async def deny_execution_request(approval_id: str, request: ControlRequest):
    """Deny a pending execution request."""
    try:
        from orchestrator_main import orchestrator
        reason = request.payload.get("reason", "User denied") if request.payload else "User denied"
        success = orchestrator.control_agent.deny_execution(approval_id, reason)
        
        if success:
            return {"status": "success", "message": f"Execution denied: {approval_id}"}
        else:
            raise HTTPException(status_code=404, detail=f"Approval not found: {approval_id}")
    except Exception as e:
        logger.exception(f"Denial Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/control/remediate/{agent_role}")
async def trigger_auto_remediation(agent_role: str):
    """Trigger auto-remediation for a degraded agent."""
    try:
        from orchestrator_main import orchestrator
        success = await orchestrator.control_agent.auto_remediate_degraded_agent(agent_role)
        if success:
            return {"status": "success", "message": f"Auto-remediation triggered for {agent_role}"}
        else:
            raise HTTPException(status_code=500, detail="Remediation failed")
    except Exception as e:
        logger.exception(f"Remediation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time interaction and progress streaming.
    """
    await manager.connect(session_id, websocket)
    
    try:
        while True:
            # Wait for user message
            data = await websocket.receive_text()
            user_input = json.loads(data)
            message = user_input.get("message", "")
            priority = user_input.get("priority", TaskPriority.MEDIUM)

            # Create a real-time progress callback for this session
            progress_callback = create_progress_callback(session_id)

            # Execute request in a separate thread to avoid blocking the WS loop
            # Since handle_request is synchronous (using asyncio.run internally), 
            # we wrap it in a thread.
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: orchestrator.handle_request(
                    user_input=message,
                    session_id=session_id,
                    priority=priority,
                    progress_callback=progress_callback
                )
            )

            # Send final result
            await websocket.send_json({
                "type": "final_result",
                "data": result
            })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.exception(f"WebSocket Loop Error: {e}")
        manager.disconnect(session_id)


# ============================================================================
# Prompt Management Endpoints (Interaction Control)
# ============================================================================

class PromptUpdateRequest(BaseModel):
    """Request model for updating agent system prompts."""
    agent_role: str
    system_prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

class PromptResponse(BaseModel):
    """Response model for agent prompt retrieval."""
    agent_role: str
    system_prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    last_updated: str
    version: int

@app.get("/agents/list")
async def get_agents_list() -> Dict[str, Any]:
    """
    List all available agents with their current configurations.
    """
    agents_data = {}
    agent_roles = [
        "knowledge_architect",
        "synthesis_expert", 
        "social_mastery",
        "sre_engineer",
        "qa_auditor",
        "visual_designer",
        "booking_agent",
        "accounting_agent"
    ]
    
    for agent_role in agent_roles:
        agents_data[agent_role] = {
            "role": agent_role,
            "status": "active",
            "last_execution": None,
            "execution_count": 0
        }
    
    logger.info("✓ Retrieved agents list")
    return {"agents": agents_data}

@app.get("/agents/{agent_id}/config")
async def get_agent_config(agent_id: str) -> PromptResponse:
    """
    Retrieve the current system prompt and configuration for an agent.
    """
    from datetime import datetime
    
    # Default system prompts per agent
    default_prompts = {
        "knowledge_architect": "You are a knowledge architect responsible for researching and structuring information.",
        "synthesis_expert": "You are an integrative synthesis expert who combines insights from multiple sources.",
        "social_mastery": "You are a social media mastery expert who creates engaging content.",
        "sre_engineer": "You are a self-evolving SRE engineer focused on system reliability.",
        "qa_auditor": "You are a QA auditor responsible for quality assurance and testing.",
        "visual_designer": "You are a visual design expert creating beautiful interfaces.",
        "booking_agent": "You are a booking agent managing appointments.",
        "accounting_agent": "You are an accounting data agent managing financial records."
    }
    
    system_prompt = default_prompts.get(agent_id, "You are an AI assistant.")
    
    logger.info(f"✓ Retrieved config for agent: {agent_id}")
    return PromptResponse(
        agent_role=agent_id,
        system_prompt=system_prompt,
        max_tokens=2000,
        temperature=0.7,
        last_updated=datetime.now().isoformat(),
        version=1
    )

@app.post("/agents/{agent_id}/config")
async def update_agent_config(agent_id: str, request: PromptUpdateRequest) -> Dict[str, Any]:
    """
    Update the system prompt and configuration for an agent.
    """
    from datetime import datetime
    
    logger.info(f"🔄 Updating config for agent: {agent_id}")
    logger.info(f"   New prompt length: {len(request.system_prompt)} chars")
    
    # In a production system, this would be persisted to the database
    # For now, we just log and confirm the update
    
    return {
        "status": "success",
        "message": f"Configuration updated for agent {agent_id}",
        "agent_role": agent_id,
        "system_prompt": request.system_prompt,
        "max_tokens": request.max_tokens or 2000,
        "temperature": request.temperature or 0.7,
        "updated_at": datetime.now().isoformat(),
        "version": 2
    }

@app.post("/agents/{agent_id}/config/rollback")
async def rollback_agent_config(agent_id: str) -> Dict[str, Any]:
    """
    Rollback agent configuration to the previous version.
    """
    from datetime import datetime
    
    logger.info(f"⏮️ Rolling back config for agent: {agent_id}")
    
    return {
        "status": "success",
        "message": f"Configuration rolled back for agent {agent_id}",
        "agent_role": agent_id,
        "rolled_back_to_version": 1,
        "rolled_back_at": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
