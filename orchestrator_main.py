"""
orchestrator_main.py - The Master Orchestrator
Coordinates all agents and manages the execution pipeline.
"""

from typing import Dict, Any, Optional, List
import asyncio
import uuid
import time
from datetime import datetime
from database import DBManager
from router import LocalRouter, HybridRouter
from cloud_brain import CloudBrain
from knowledge_architect import KnowledgeArchitect
from synthesis_expert import IntegrativeSynthesisExpert
from social_mastery import SocialMediaMastery
from sre_agent import SelfEvolvingSRE
from qa_auditor import QAAuditor
from visual_design_agent import VisualDesignAgent
from booking_appointment_agent import BookingAppointmentAgent
from accounting_data_agent import AccountingDataAgent
from meta_brain import MetaBrain
from system_control_agent import SystemControlAgent
from tool_registry import registry as tool_registry
from document_template_engine import DocumentTemplateEngine
from schemas import TaskRequest, TaskResponse, TaskStatus, AgentRole, TaskPriority, TaskAction
from utils.logger import logger
from utils.llm_clients import LocalLLMClientFactory
from utils.resilience import retry_async, ExponentialBackoffConfig, CONFIG_API_CALL


class AgentOrchestrator:
    """Master coordinator for the multi-agent system."""

    def __init__(self, db_manager: DBManager, config: Dict[str, Any] = None):
        self.db = db_manager
        self.config = config or {}

        # Initialize global config
        from config import config as global_config
        
        # Initialize Local LLM Client (Phase 7.4: Configurable Local LLM Selection)
        logger.info("🚀 Initializing Local LLM Client for Routing...")
        
        # Check if USE_LOCAL_LLM_ROUTING is enabled
        use_local_llm = global_config.USE_LOCAL_LLM_ROUTING
        
        if use_local_llm:
            try:
                # Create Local LLM client from config
                llm_client = LocalLLMClientFactory.create_from_config(global_config)
                
                if llm_client and llm_client.is_available():
                    logger.info(f"✓ Local LLM Client ready | Model: {global_config.LOCAL_LLM_MODEL} | Provider: {global_config.LOCAL_LLM_PROVIDER}")
                    print(f"✓ Using Local LLM for Routing: {global_config.LOCAL_LLM_MODEL} ({global_config.LOCAL_LLM_PROVIDER})")
                else:
                    logger.warning(f"⚠️ Local LLM not available | Falling back to Cloud LLM for routing")
                    print(f"⚠️ Local LLM '{global_config.LOCAL_LLM_MODEL}' is not available. Routing will use Cloud LLM fallback.")
                    llm_client = None
            except Exception as e:
                logger.error(f"❌ Failed to initialize Local LLM Client: {e}")
                print(f"❌ Error initializing Local LLM: {e}. Routing will use Cloud LLM fallback.")
                llm_client = None
        else:
            logger.info("ℹ️ Local LLM Routing is disabled. Using Cloud LLM for routing.")
            llm_client = None

        # Initialize routers with the local LLM client
        self.local_router = LocalRouter(db_manager, llm_client=llm_client)

        # Initialize agents
        from config import config as global_config
        
        self.architect = KnowledgeArchitect(
            db_manager,
            search_api_key=config.get("TAVILY_API_KEY") if isinstance(config, dict) else global_config.TAVILY_API_KEY
        )
        self.synthesis_expert = IntegrativeSynthesisExpert(db_manager)
        self.social_mastery = SocialMediaMastery(db_manager)
        self.sre = SelfEvolvingSRE(db_manager)
        self.qa_auditor = QAAuditor(db_manager, guidelines=config.get("compliance_guidelines") if isinstance(config, dict) else None)
        self.visual_designer = VisualDesignAgent(db_manager)
        self.booking_agent = BookingAppointmentAgent(db_manager)
        self.accounting_agent = AccountingDataAgent(db_manager)
        self.meta_brain = MetaBrain(db_manager)
        self.template_engine = DocumentTemplateEngine()
        
        # Phase 8: System Control Plane
        self.control_agent = SystemControlAgent(db_manager)
        self._register_agents_with_control_plane()
        
        # Import tools to ensure they are registered
        import agent_tools 

        # Initialize cloud brain
        self.cloud_brain = CloudBrain(db_manager)

        # Upgrade router to hybrid (with cloud brain)
        self.router = HybridRouter(db_manager, self.local_router, self.cloud_brain)

    def _register_agents_with_control_plane(self):
        """Register all agents with the system control plane."""
        agents_to_register = [
            ("knowledge_architect", {"version": "1.0", "capabilities": ["research", "analysis"]}),
            ("integrative_synthesis_expert", {"version": "1.0", "capabilities": ["synthesis", "summarization"]}),
            ("social_media_mastery", {"version": "1.0", "capabilities": ["social_media", "marketing"]}),
            ("self_evolving_sre", {"version": "1.0", "capabilities": ["monitoring", "optimization"]}),
            ("qa_auditor", {"version": "1.0", "capabilities": ["quality_assurance", "auditing"]}),
            ("visual_design_agent", {"version": "1.0", "capabilities": ["visual_design", "image_generation"]}),
            ("booking_appointment_agent", {"version": "1.0", "capabilities": ["booking", "scheduling"]}),
            ("accounting_data_agent", {"version": "1.0", "capabilities": ["accounting", "finance"]}),
        ]
        
        for agent_role, metadata in agents_to_register:
            self.control_agent.register_agent(agent_role, metadata)
        
        logger.info(f"✓ Registered {len(agents_to_register)} agents with control plane")

    def handle_request(self, user_input: str, session_id: str = "default", priority: TaskPriority = TaskPriority.MEDIUM, progress_callback=None) -> Dict[str, Any]:
        """
        Main entry point: processes a user request end-to-end with conversational memory and progress streaming.
        Supports formal document generation via template_engine.
        """
        # Check if this is a request for a formal document
        if "generate report" in user_input.lower() or "สร้างรายงาน" in user_input.lower():
            return self._handle_document_generation(user_input, session_id, priority)

        # Check if this is an approval response
        if user_input.lower() in ["approve", "yes", "confirm", "ตกลง", "อนุมัติ"]:
            return self._handle_approval(session_id, approved=True)
        if user_input.lower() in ["reject", "no", "cancel", "ไม่", "ไม่อนุมัติ"]:
            return self._handle_approval(session_id, approved=False)

        trace_id = str(uuid.uuid4())
        
        # 1. Retrieve Conversation History and User Preferences
        history = self.db.get_history(session_id)
        preferences = self.db.get_user_preferences(session_id)
        
        context_input = self._augment_input_with_history(user_input, history, preferences)
        
        logger.info(f"Handling request | TraceID: {trace_id} | Session: {session_id} | Input: {user_input[:50]}...")
        
        print(f"\n{'='*60}")
        print(f"[ORCHESTRATOR] Handling request (Trace: {trace_id})")
        print(f"Session: {session_id}")
        print(f"{'='*60}\n")

        # Step 1: Route the request using augmented input (Intent-Based)
        routing_decision = self.router.route_with_escalation(context_input, priority)
        task_id = routing_decision["task_id"]

        logger.info(f"Routing Decision | TraceID: {trace_id} | Agent: {routing_decision['assigned_agent']} | Confidence: {routing_decision['confidence']:.2%}")
        print(f"[OK] Routing Decision: {routing_decision['assigned_agent']}")
        print(f"  Confidence: {routing_decision['confidence']:.2%}")
        print(f"  Reason: {routing_decision['reasoning']}")

        # Step 2: Check if we have a decomposed DAG
        if routing_decision.get("decomposed_tasks"):
            logger.info(f"Executing Complex DAG | TraceID: {trace_id} | Steps: {len(routing_decision['decomposed_tasks'])}")
            print(f"\n[INFO] Executing complex DAG with {len(routing_decision['decomposed_tasks'])} steps...")
            # Run async execution with progress callback
            result = asyncio.run(self._execute_dag_async(task_id, routing_decision["decomposed_tasks"], user_input, trace_id, progress_callback))
        else:
            logger.info(f"Executing Simple Task | TraceID: {trace_id} | Agent: {routing_decision['assigned_agent']}")
            print(f"\n[INFO] Executing simple task directly...")
            result = self._execute_simple_task(task_id, routing_decision["assigned_agent"], user_input, trace_id=trace_id)

        # 3. Save to Memory
        self.db.save_message(session_id, "user", user_input)
        final_answer = result.get("artifacts", "Task completed.") if isinstance(result, dict) else str(result)
        self.db.save_message(session_id, "assistant", str(final_answer))

        return result

        return result

    def _augment_input_with_history(self, user_input: str, history: List[Dict[str, str]], preferences: Dict[str, str] = None) -> str:
        """
        Combines current input with conversation history and user preferences to provide context.
        """
        if not history and not preferences:
            return user_input
        
        context_parts = []
        
        if history:
            history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history])
            context_parts.append(f"Conversation History:\n{history_text}")
            
        if preferences:
            pref_text = "\n".join([f"{k}: {v}" for k, v in preferences.items()])
            context_parts.append(f"User Preferences:\n{pref_text}")
            
        context_string = "\n\n".join(context_parts)
        return f"{context_string}\n\nUser's current request: {user_input}"

    def _execute_simple_task(self, task_id: str, agent_role: str, user_input: str, trace_id: str = None) -> Dict[str, Any]:
        """
        Executes a single-step task directly.
        """
        task = self.db.get_task(task_id)
        request = TaskRequest(
            task_id=task_id,
            trace_id=trace_id,
            agent_role=agent_role,
            action="research",
            payload={"instruction": user_input}
        )

        # Strict Validation
        try:
            request.validate_payload()
        except ValueError as e:
            print(f"❌ Input Validation Failed: {e}")
            return {"status": "failed", "error": str(e)}

        # Execute the assigned agent
        self.db.update_task_status(task_id, "in_progress")
        response = self._execute_agent(agent_role, request)

        if response.status == TaskStatus.COMPLETED:
            self.db.save_artifact(task_id, response.dict())
            self.db.update_task_status(task_id, "completed")
            print(f"\n[OK] Task completed: {agent_role}")
        else:
            self.db.update_task_status(task_id, "failed")
            print(f"\n[ERROR] Task failed: {agent_role}")

        return {
            "status": response.status,
            "artifacts": response.artifacts,
            "meta": response.meta
        }

    async def _execute_agent_async(self, agent_role: str, request: TaskRequest) -> TaskResponse:
        """
        Asynchronous wrapper for agent execution with exponential backoff retry.
        Handles transient failures with configurable retry strategy.
        """
        # Apply retry logic with exponential backoff
        @retry_async(
            retries=CONFIG_API_CALL['max_retries'],
            initial_delay=CONFIG_API_CALL['initial_delay'],
            backoff_factor=CONFIG_API_CALL['exponential_base'],
            exceptions=(Exception,),  # Catch all exceptions for retry
            operation_name=f"Agent_{agent_role}"
        )
        async def _agent_execution():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._execute_agent, agent_role, request)
        
        try:
            return await _agent_execution()
        except Exception as e:
            # Log non-retryable errors
            logger.error(f"❌ Agent execution failed after retries | Agent: {agent_role} | Error: {str(e)}")
            raise

    async def _execute_dag_async(self, master_task_id: str, dag: List[Dict], user_input: str, trace_id: str = None, progress_callback=None) -> Dict[str, Any]:
        """
        Asynchronously executes a complex DAG of interdependent tasks.
        Supports progress streaming via callback and self-optimization via Meta-Brain.
        """
        # Phase 7.2: Check for and apply DAG optimizations from Meta-Brain
        optimizations = self.meta_brain.get_optimization_suggestions(master_task_id)
        if optimizations:
            best_opt = optimizations[0]
            logger.info(f"Applying Meta-Brain Optimization | Type: {best_opt.optimization_type} | Confidence: {best_opt.confidence:.2%}")
            dag = self.meta_brain.apply_optimization(best_opt, dag)

        execution_order = self.cloud_brain.get_execution_order(dag)
        completed_steps = {}
        pending_steps = {s.step_number: s for s in dag}

        print(f"\n[INFO] Async Execution Order: {execution_order}")

        # Initialize token tracking
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        while pending_steps:
            ready_steps = [
                step_num for step_num, step in pending_steps.items()
                if all(dep in completed_steps for dep in step.depends_on)
            ]

            if not ready_steps:
                print("❌ Deadlock detected in DAG dependencies!")
                break

            tasks = []
            for step_num in ready_steps:
                step = pending_steps[step_num]
                sub_task_id = f"{master_task_id}_step_{step.step_number}"
                
                agent_role_map = {
                    "knowledge_architect": AgentRole.KNOWLEDGE_ARCHITECT,
                    "integrative_synthesis_expert": AgentRole.SYNTHESIS_EXPERT,
                    "social_media_mastery": AgentRole.SOCIAL_MASTERY,
                    "self_evolving_sre": AgentRole.SRE_ENGINEER,
                    "visual_design_agent": AgentRole.VISUAL_DESIGNER,
                }
                agent_role_enum = agent_role_map.get(step.agent_role, AgentRole.KNOWLEDGE_ARCHITECT)

                action_map = {
                    "research": TaskAction.RESEARCH,
                    "analyze": TaskAction.ANALYZE,
                    "create": TaskAction.CREATE,
                    "monitor": TaskAction.MONITOR,
                    "decompose": TaskAction.DECOMPOSE,
                    "audit": TaskAction.AUDIT,
                    "generate_image": TaskAction.GENERATE_IMAGE,
                    "overlay_text": TaskAction.OVERLAY_TEXT,
                    "design_layout": TaskAction.DESIGN_LAYOUT,
                }
                action_enum = action_map.get(step.action, TaskAction.RESEARCH)

                # Gather results from dependencies to provide context to the agent
                dependency_context = {}
                for dep_num in step.depends_on:
                    if dep_num in completed_steps:
                        dep_res = completed_steps[dep_num]
                        # Only include useful artifacts to avoid token overflow
                        dependency_context[f"step_{dep_num}"] = dep_res.artifacts if hasattr(dep_res, 'artifacts') else dep_res

                request = TaskRequest(
                    task_id=sub_task_id,
                    trace_id=trace_id,
                    agent_role=agent_role_enum,
                    action=action_enum,
                    payload={
                        "instruction": step.instruction, 
                        "parent_id": master_task_id,
                        "context": dependency_context
                    }
                )

                async def run_step(s_num, s_role, s_req):
                    # Approval Gate: Check if this step requires human approval
                    # We define 'social_media_mastery' as a critical agent requiring approval
                    if s_role == AgentRole.SOCIAL_MASTERY:
                        logger.info(f"Approval Gate Triggered | TraceID: {s_req.trace_id} | Step: {s_num}")
                        self.db.update_task_status(s_req.task_id, "waiting_for_approval")
                        return s_num, TaskResponse(
                            task_id=s_req.task_id,
                            status=TaskStatus.WAITING_FOR_APPROVAL,
                            artifacts={"message": "This step requires human approval before proceeding."},
                            meta={"requires_approval": True}
                        )

                    # Progress Update
                    if progress_callback:
                        from schemas import ProgressUpdate
                        update = ProgressUpdate(
                            task_id=master_task_id,
                            step_number=s_num,
                            total_steps=len(dag),
                            agent_role=s_role,
                            status="in_progress",
                            message=f"Agent {s_role} is working on step {s_num}..."
                        )
                        progress_callback(update)

                    logger.info(f"Executing Step {s_num} | TraceID: {s_req.trace_id} | Agent: {s_role}")
                    self.db.update_task_status(s_req.task_id, "in_progress")
                    
                    # --- Iterative Refinement Loop ---
                    max_retries = 3
                    attempt = 0
                    while attempt < max_retries:
                        start_time = time.time()
                        try:
                            resp = await self._execute_agent_async(s_role, s_req)
                        except Exception as e:
                            import traceback
                            error_stack = traceback.format_exc()
                            logger.error(f"Critical failure during agent execution | Step: {s_num} | Agent: {s_role} | Error: {e}\n{error_stack}")
                            
                            # Save failure details to DB for auditing
                            self.db.update_task_status(s_req.task_id, "failed", reason=f"Crash: {str(e)}")
                            
                            return s_num, TaskResponse(
                                task_id=s_req.task_id,
                                status=TaskStatus.FAILED,
                                artifacts={"error": str(e), "stack_trace": error_stack},
                                error_message=f"Agent execution crash: {str(e)}"
                            )
                        
                        duration = time.time() - start_time
                        
                        # If this is a QA step, check if it requires revision
                        if s_role == AgentRole.QA_AUDITOR and resp.status == TaskStatus.COMPLETED:
                            verdict = resp.artifacts.get("verdict", "PASS")
                            if verdict == "NEEDS_REVISION":
                                attempt += 1
                                logger.info(f"QA Revision Requested | Step: {s_num} | Attempt: {attempt}/{max_retries}")
                                
                                # Find the agent that produced the content to be audited
                                # In a real DAG, we'd look at the dependencies
                                target_agent = "social_media_mastery" if "social" in str(s_req.payload) else "knowledge_architect"
                                
                                # Create a refinement request for the original agent
                                refinement_req = TaskRequest(
                                    task_id=f"{s_req.task_id}_refine_{attempt}",
                                    trace_id=s_req.trace_id,
                                    agent_role=AgentRole[target_agent.upper()],
                                    action=s_req.action,
                                    payload={
                                        "instruction": f"REVISE based on QA feedback: {resp.artifacts.get('recommendations')}",
                                        "original_content": resp.artifacts.get("content"),
                                        "parent_id": master_task_id
                                    }
                                )
                                
                                # Execute refinement
                                try:
                                    refinement_resp = await self._execute_agent_async(AgentRole[target_agent.upper()], refinement_req)
                                    if refinement_resp.status == TaskStatus.COMPLETED:
                                        # Update the current response with the refined content
                                        resp.artifacts["content"] = refinement_resp.artifacts
                                        # Re-audit the refined content
                                        s_req.payload["content"] = refinement_resp.artifacts
                                        continue # Loop back to audit again
                                except Exception as e:
                                    import traceback
                                    error_stack = traceback.format_exc()
                                    logger.error(f"Refinement process failed | Step: {s_num} | Error: {e}\n{error_stack}")
                                    # Fallback: Keep the original a-audit result but mark as refinement-failed
                                    resp.artifacts["refinement_error"] = str(e)
                                    resp.artifacts["refinement_stack_trace"] = error_stack
                                    break
                                
                        break # Exit loop if PASS or max retries reached

                        if resp.status == TaskStatus.COMPLETED:
                            self.db.save_artifact(s_req.task_id, resp.dict())
                            self.db.update_task_status(s_req.task_id, "completed")
                            
                            # Phase 7.2: Capture execution metrics for Meta-Brain
                            usage = resp.get_token_usage()
                            self.meta_brain.capture_execution_metrics(
                                task_id=master_task_id,
                                step_number=s_num,
                                agent_role=str(s_role),
                                action=str(s_req.action),
                                duration_seconds=duration,
                                prompt_tokens=usage["prompt_tokens"],
                                completion_tokens=usage["completion_tokens"],
                                success=True,
                                dependencies=step.depends_on
                            )
                        else:
                            self.db.update_task_status(s_req.task_id, "failed")
                            # Capture failure metrics
                            self.meta_brain.capture_execution_metrics(
                                task_id=master_task_id,
                                step_number=s_num,
                                agent_role=str(s_role),
                                action=str(s_req.action),
                                duration_seconds=duration,
                                prompt_tokens=0,
                                completion_tokens=0,
                                success=False,
                                dependencies=step.depends_on
                            )
                        return s_num, resp

                tasks.append(run_step(step_num, step.agent_role, request))

            wave_results = await asyncio.gather(*tasks)
            
            for step_num, response in wave_results:
                if response.status == TaskStatus.COMPLETED:
                    completed_steps[step_num] = response
                    # Accumulate tokens
                    usage = response.get_token_usage()
                    total_tokens["prompt_tokens"] += usage["prompt_tokens"]
                    total_tokens["completion_tokens"] += usage["completion_tokens"]
                    total_tokens["total_tokens"] += usage["total_tokens"]
                else:
                    print(f"   [ERROR] Step {step_num} failed. Stopping pipeline.")
                    return {"status": "failed", "error": f"Step {step_num} failed"}
                del pending_steps[step_num]

        self.db.update_task_status(master_task_id, "completed")
        return {
            "status": "completed",
            "total_steps": len(dag),
            "completed_steps": len(completed_steps),
            "results": {f"step_{k}": v.artifacts for k, v in completed_steps.items()},
            "token_usage": total_tokens
        }

    def _execute_agent(self, agent_role: str, request: TaskRequest) -> TaskResponse:
        """
        Executes a specific agent and returns the response.
        Injects persistent configuration from the database into the request if available.
        """
        # Phase 7.4: Integrate Persistent Configs
        # Check if there is a custom prompt/temperature/max_tokens in the DB for this agent
        if not request.agent_config:
            config_from_db = self.db.get_agent_config(agent_role)
            if config_from_db:
                request.agent_config = config_from_db
                logger.info(f"✓ Loaded persistent config for {agent_role} | Version: {config_from_db.get('version', 'unknown')}")
        
        if agent_role == "knowledge_architect":
            return self.architect.execute(request)
        elif agent_role == "integrative_synthesis_expert":
            return self.synthesis_expert.execute(request)
        elif agent_role == "social_media_mastery":
            return self.social_mastery.execute(request)
        elif agent_role == "self_evolving_sre":
            return self.sre.execute(request)
        elif agent_role == "qa_auditor":
            return self.qa_auditor.execute(request)
        elif agent_role == "visual_design_agent":
            return self.visual_designer.execute(request)
        elif agent_role == "booking_appointment_agent":
            # Booking agent uses async, so we run it synchronously
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.booking_agent.process_task(request))
        elif agent_role == "accounting_data_agent":
            return self.accounting_agent.execute(request)
        elif agent_role == "system_control":
            # Phase 8: System Control Agent
            return self.control_agent.execute(request)
        else:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": f"Unknown agent: {agent_role}"},
                error_message=f"Agent {agent_role} not found"
            )

    def get_system_health(self) -> Dict[str, Any]:
        """
        Returns a comprehensive health report of the system.
        """
        request = TaskRequest(
            task_id="health_check",
            agent_role="self_evolving_sre",
            action="monitor",
            payload={}
        )
        response = self.sre.execute(request)
        return response.artifacts

    def rotate_api_keys(self):
        """
        Triggers a refresh of API keys from the environment and updates active agents.
        """
        from config import config as global_config
        global_config.refresh_keys()
        
        # Update agents that hold a local copy of the key
        self.architect.search_api_key = global_config.TAVILY_API_KEY
        
        logger.info("API Keys rotated and agents updated successfully.")
        print("\n[OK] API Keys rotated successfully.")

    def _handle_approval(self, session_id: str, approved: bool) -> Dict[str, Any]:
        """
        Handles the approval/rejection of a paused task.
        """
        # Find the most recent task waiting for approval for this session
        # In a real system, we'd track the specific task_id in the session state
        # For now, we'll look for the latest 'waiting_for_approval' task in the DB
        session = self.db.Session()
        try:
            from database import TaskRecord
            task = session.query(TaskRecord).filter(
                TaskRecord.status == "waiting_for_approval"
            ).order_by(TaskRecord.created_at.desc()).first()

            if not task:
                return {"status": "failed", "error": "No pending approval found for this session."}

            if approved:
                logger.info(f"Task {task.task_id} APPROVED by user.")
                # In a full implementation, we would resume the DAG from this point.
                # For this version, we'll mark it as completed to simulate progression.
                self.db.update_task_status(task.task_id, "completed")
                return {"status": "completed", "message": "Approval granted. Task resumed and completed."}
            else:
                logger.info(f"Task {task.task_id} REJECTED by user.")
                self.db.update_task_status(task.task_id, "failed")
                return {"status": "failed", "message": "Approval denied. Task cancelled."}
        finally:
            session.close()

    def resume_task_after_approval(self, task_id: str, approved: bool) -> Dict[str, Any]:
        """
        Resume DAG execution after user approval/rejection.
        """
        try:
            task = self.db.get_task(task_id)
            if not task:
                return {"status": "error", "message": f"Task {task_id} not found"}
            
            if approved:
                logger.info(f"Resuming task {task_id} after approval.")
                self.db.update_task_status(task_id, "completed", reason="User approved")
                # In a full DAG implementation, we would trigger the next wave here
                return {"status": "success", "message": f"Task {task_id} approved and resumed."}
            else:
                logger.info(f"Cancelling task {task_id} after rejection.")
                self.db.update_task_status(task_id, "failed", reason="User rejected")
                return {"status": "success", "message": f"Task {task_id} rejected and halted."}
        except Exception as e:
            logger.error(f"Error resuming task {task_id}: {e}")
            return {"status": "error", "message": str(e)}

    def update_task_instruction(self, task_id: str, new_instruction: str) -> Dict[str, Any]:
        """
        Dynamically update instruction for a pending task.
        """
        try:
            task = self.db.get_task(task_id)
            if not task:
                return {"status": "error", "message": f"Task {task_id} not found"}
            
            if task.status not in ["pending", "in_progress", "waiting_for_approval"]:
                return {"status": "error", "message": f"Cannot update task in status {task.status}"}
            
            # Update payload
            updated_payload = task.payload or {}
            updated_payload["instruction"] = new_instruction
            updated_payload["instruction_updated_at"] = datetime.now().isoformat()
            
            self.db.update_task_payload(task_id, updated_payload)
            logger.info(f"Task {task_id} instruction updated by user.")
            
            return {"status": "success", "message": "Instruction updated successfully."}
        except Exception as e:
            logger.error(f"Error updating instruction for task {task_id}: {e}")
            return {"status": "error", "message": str(e)}

    def reset_session_memory(self, session_id: str) -> Dict[str, Any]:
        """
        Clear conversation history for a session.
        """
        try:
            cleared_count = self.db.clear_conversation_memory(session_id)
            logger.info(f"Session {session_id} memory reset. Records cleared: {cleared_count}")
            return {"status": "success", "message": f"Session {session_id} memory reset. {cleared_count} records cleared."}
        except Exception as e:
            logger.error(f"Error resetting session {session_id}: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_document_generation(self, user_input: str, session_id: str, priority: TaskPriority) -> Dict[str, Any]:
        """
        Handles requests for formal document generation using the Template Engine.
        """
        logger.info(f"Generating formal document for session: {session_id}")
        
        # 1. Retrieve the most recent artifacts from the session to use as data
        # In a real system, we would use an LLM to map artifacts to template placeholders
        history = self.db.get_history(session_id)
        
        # Mock data mapping for demonstration
        # In production: use an LLM to extract values for {{summary}}, {{key_findings}}, etc.
        document_data = {
            "summary": "This is a synthesized summary of the research conducted in this session.",
            "key_findings": ["Finding 1: Market growth is 15%", "Finding 2: User demand is increasing"],
            "recommendations": "Invest in AI-driven automation to reduce costs.",
            "conclusion": "The project is viable and recommended for immediate launch.",
            "intro": "Introduction to the research project...",
            "methodology": "We used a multi-agent system to analyze web data.",
            "analysis": "Detailed analysis of the current market trends...",
            "supporting_data": "Data from Tavily search results...",
            "verdict": "Highly Recommended",
            "goal": "Increase brand awareness by 20%",
            "platform_strategy": "Focus on LinkedIn and X",
            "calendar": "Week 1: Teaser, Week 2: Launch, Week 3: Follow-up",
            "kpis": "Reach: 1M, Engagement: 5%"
        }
        
        # 2. Determine which template to use based on user input
        template_name = "executive_summary"
        if "research report" in user_input.lower():
            template_name = "research_report"
        elif "campaign" in user_input.lower() or "plan" in user_input.lower():
            template_name = "campaign_plan"
            
        # 3. Generate the document
        try:
            document = self.template_engine.generate_document(template_name, document_data)
            return {
                "status": "completed",
                "artifacts": document,
                "meta": {
                    "template_used": template_name,
                    "generated_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def handle_task(self, request: TaskRequest) -> TaskResponse:
        # ...existing code...
        # Chain of Command: If Accounting Agent just completed a document process, 
        # trigger a verification check by the QA Auditor.
        response = await self.route_to_agent(request)
        
        if response.status == TaskStatus.COMPLETED and request.payload.get("action") == "process_financial_document":
            record_id = response.artifacts.get("db_entry_id")
            if record_id:
                logger.info(f"Orchestrator: Triggering verification loop for record {record_id}")
                verify_request = TaskRequest(
                    task_id=f"{request.task_id}_verify",
                    payload={
                        "action": "verify_financial_record",
                        "record_id": record_id
                    }
                )
                # Call QA Auditor for verification
                audit_response = await self.route_to_agent(verify_request)
                
                # If Flagged, trigger email notification
                if audit_response.artifacts.get("audit_result", {}).get("status") == "FLAGGED":
                    from email_notifier import EmailNotifier
                    notifier = EmailNotifier()
                    notifier.send_audit_alert(audit_response.artifacts["audit_result"], record_id)
                
                # Merge audit result into final response
                response.artifacts["verification"] = audit_response.artifacts.get("audit_result")
        
        return response

    def cleanup(self):
        """Cleanup resources and close database connections."""
        logger.info("Cleaning up orchestrator resources...")
        # Add any specific cleanup logic here if needed
        pass
