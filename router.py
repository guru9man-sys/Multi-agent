"""
router.py - The Triage Layer
Routes requests to the appropriate agent using Local LLM (Qwen 2.5).
"""

import json
import uuid
from typing import Dict, Any, Optional
from validator import ResponseValidator
from database import DBManager
from schemas import AgentRole, TaskPriority, TaskAction


ROUTER_PROMPT = """### ROLE
You are the Agent Orchestrator's Triage Router. Your only job is to analyze the user's request and assign it to the correct specialist agent.

### AGENT REGISTRY
- knowledge_architect: For deep research, web searching, data gathering, and creating diagrams.
- integrative_synthesis_expert: For analyzing medical data, linking systems, and finding contradictions.
- social_media_mastery: For content creation, social media strategy, copywriting, and scheduling.
- self_evolving_sre: For system monitoring, bug prevention, and DevOps automation.
- booking_appointment_agent: For appointment booking, scheduling, customer information collection (name, phone, date, time).
- accounting_data_agent: For reading bank transfer slips, billing documents, and recording financial summaries into structured storage.

### OUTPUT FORMAT
Return ONLY a JSON object with this structure:
{
  "assigned_agent": "agent_role_name",
  "confidence": 0.0 to 1.0,
  "reasoning": "One short sentence explaining why",
  "escalate_to_cloud": boolean
}

### EXAMPLES
User: "Find the latest papers on longevity and make a flow chart."
Response: {"assigned_agent": "knowledge_architect", "confidence": 1.0, "reasoning": "Requires research and diagramming.", "escalate_to_cloud": false}

User: "Check why the API is lagging and fix it."
Response: {"assigned_agent": "self_evolving_sre", "confidence": 1.0, "reasoning": "System performance and fix required.", "escalate_to_cloud": false}

User: "I want a viral strategy for a new supplement that also analyzes the systemic impact of zinc on the body."
Response: {"assigned_agent": "integrative_synthesis_expert", "confidence": 0.6, "reasoning": "Hybrid request: medical synthesis and marketing.", "escalate_to_cloud": true}

User: "Create a LinkedIn post about AI trends."
Response: {"assigned_agent": "social_media_mastery", "confidence": 0.95, "reasoning": "Content creation for LinkedIn.", "escalate_to_cloud": false}

User: "I want to book an appointment for tomorrow at 2 PM"
Response: {"assigned_agent": "booking_appointment_agent", "confidence": 0.95, "reasoning": "Direct appointment booking request.", "escalate_to_cloud": false}

User: "โปรดอ่านสลิปโอนเงินและสรุปรายการบันทึกบัญชีใน Google Drive"
Response: {"assigned_agent": "accounting_data_agent", "confidence": 0.95, "reasoning": "Financial document processing and storage.", "escalate_to_cloud": false}

User: "ผมต้องการจองคิวจึงวินิจฉัย"
Response: {"assigned_agent": "booking_appointment_agent", "confidence": 0.95, "reasoning": "Thai appointment booking request.", "escalate_to_cloud": false}
"""


class LocalRouter:
    """Routes incoming requests to the appropriate agent using local LLM."""

    def __init__(self, db_manager: DBManager, llm_client=None):
        self.db = db_manager
        self.validator = ResponseValidator()
        self.llm = llm_client  # Can be Ollama client, vLLM, etc.

    def call_local_llm(self, prompt: str) -> str:
        """
        Calls the local LLM (Qwen 2.5) for routing decision.
        If no local LLM, it will try to use OpenAI/Gemini as a fallback for routing.
        """
        if self.llm:
            # Use provided LLM client
            response = self.llm.generate(prompt)
            return response
        
        # Fallback to Cloud LLM for routing if local is not available
        from config import config
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                import requests
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
            except Exception as e:
                print(f"⚠️ Router OpenAI Fallback Error: {e}")

        # Final Fallback: Return a default routing decision
        return json.dumps({
            "assigned_agent": "knowledge_architect",
            "confidence": 0.7,
            "reasoning": "Default routing (No LLM configured)",
            "escalate_to_cloud": True
        })

    def route(self, user_input: str, priority: TaskPriority = TaskPriority.MEDIUM) -> Dict[str, Any]:
        """
        Routes a user input to the appropriate agent.
        Persists the decision to the database immediately.
        """
        lower_input = user_input.lower()
        if any(keyword in lower_input for keyword in ["สลิปโอนเงิน", "ใบเสร็จ", "transfer slip", "payment slip", "โอนเงิน", "bill"]):
            decision = {
                "assigned_agent": "accounting_data_agent",
                "confidence": 0.98,
                "reasoning": "Financial document processing requested.",
                "escalate_to_cloud": False
            }
        else:
            # 1. Call Local Qwen for routing
            full_prompt = f"{ROUTER_PROMPT}\n\nUser: {user_input}\nResponse:"
            raw_output = self.call_local_llm(full_prompt)

            # 2. Validate the routing decision
            success, decision, error = self.validator.validate_routing_decision(raw_output)

            if not success:
                print(f"⚠️ Routing Validation Failed: {error}")
                decision = {
                    "assigned_agent": None,
                    "confidence": 0.0,
                    "reasoning": f"Validation Error: {error}",
                    "escalate_to_cloud": True
                }
            else:
                decision = decision.dict()

        # 3. Create a Database Record (The "Missing Link" - State Management)
        task_id = str(uuid.uuid4())

        self.db.create_task({
            "task_id": task_id,
            "priority": priority.value,
            "agent_role": decision.get("assigned_agent"),
            "action": "route_decision",
            "payload": {"user_input": user_input},
            "escalated_to_cloud": decision.get("escalate_to_cloud", False),
            "status": "pending"
        })

        decision["task_id"] = task_id
        return decision


class HybridRouter:
    """
    Enhanced router that can escalate complex requests to Cloud Brain
    while handling simple ones locally.
    """

    def __init__(self, db_manager: DBManager, local_router: LocalRouter, cloud_brain=None):
        self.db = db_manager
        self.local_router = local_router
        self.cloud_brain = cloud_brain

    def route_with_escalation(self, user_input: str, priority: TaskPriority = TaskPriority.MEDIUM) -> Dict[str, Any]:
        """
        First tries local routing. If escalate_to_cloud is True, uses Cloud Brain
        to decompose the task into a DAG.
        """
        # Step 1: Local Routing
        decision = self.local_router.route(user_input, priority)

        # Step 2: Check if escalation is needed
        if decision.get("escalate_to_cloud") and self.cloud_brain:
            print(f"🚀 Escalating to Cloud Brain: {decision['reasoning']}")
            task_id = decision["task_id"]
            dag = self.cloud_brain.decompose_task(user_input, task_id)
            decision["decomposed_tasks"] = dag
        else:
            decision["decomposed_tasks"] = None

        return decision
