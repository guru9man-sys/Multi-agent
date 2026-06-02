"""
cloud_brain.py - The Planning Layer
Decomposes complex requests into a Directed Acyclic Graph (DAG) of sub-tasks.
Integrates Context Compression for handling long conversations without losing critical info.
"""

import json
import uuid
import requests
from typing import List, Dict, Any, Optional
from database import DBManager
from validator import ResponseValidator
from schemas import SubTask, MasterPlan
from config import config
from utils.resilience import retry_with_backoff
from context_compression import ContextCompressor
from utils.logger import logger


DECOMPOSITION_PROMPT = """You are an expert task planner. Your job is to break down a complex user request into a logical sequence of steps that different AI agents can execute.

AVAILABLE AGENTS:
1. knowledge_architect: Researches, finds information, creates diagrams/mindmaps
2. integrative_synthesis_expert: Analyzes and synthesizes information, finds contradictions
3. social_media_mastery: Creates engaging content for multiple platforms
4. self_evolving_sre: Monitors and fixes system issues

RULES:
- Tasks should be ordered based on dependencies (e.g., research must come before analysis)
- Each step should have a clear output that feeds into the next step
- Use "depends_on" to specify which steps must finish first (use step_number)
- Return ONLY a JSON object following this exact structure:

{{
  "plan_id": "UUID",
  "total_steps": number,
  "dag": [
    {{"step_number": 1, "agent_role": "knowledge_architect", "action": "research", "instruction": "...", "depends_on": []}},
    {{"step_number": 2, "agent_role": "integrative_synthesis_expert", "action": "analyze", "instruction": "...", "depends_on": [1]}}
  ],
  "expected_outcome": "Description of final result"
}}

User Request: {user_input}

Return ONLY valid JSON, no other text."""


class CloudBrain:
    """Uses Cloud LLM to decompose complex requests into executable DAGs.
    Integrates Context Compression to handle long conversations without context loss."""

    def __init__(self, db_manager: DBManager, llm_client=None):
        self.db = db_manager
        self.llm = llm_client
        self.validator = ResponseValidator()
        self.context_compressor = ContextCompressor()  # NEW: Context compression
        logger.info("CloudBrain initialized with ContextCompressor for long-running tasks")

    @retry_with_backoff(retries=3, backoff_factor=2.0)
    def call_cloud_llm(self, prompt: str) -> str:
        """
        Calls the Cloud LLM for high-reasoning tasks.
        Implements a Graceful Degradation Chain: OpenAI -> Gemini -> Qwen Cloud -> Local LLM -> Mock.
        """
        # 1. Try OpenAI (Primary)
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
            except Exception as e:
                print(f"⚠️ OpenAI Error: {e}. Falling back to Gemini...")

        # 2. Try Gemini (Secondary)
        if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your_gemini_api_key_here":
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={config.GEMINI_API_KEY}"
                response = requests.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=30
                )
                response.raise_for_status()
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                print(f"⚠️ Gemini Error: {e}. Falling back to Qwen Cloud...")

        # 3. Try Qwen Cloud (Tertiary)
        if config.QWEN_API_KEY and config.QWEN_API_KEY != "your_qwen_api_key_here":
            try:
                # Assuming DashScope/Alibaba Cloud API format
                response = requests.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/dashscope-llm/generation",
                    headers={"Authorization": f"Bearer {config.QWEN_API_KEY}"},
                    json={
                        "model": "qwen-max",
                        "input": {"prompt": prompt},
                        "parameters": {"temperature": 0.2}
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json()['output']['text']
            except Exception as e:
                print(f"⚠️ Qwen Cloud Error: {e}. Falling back to Local LLM...")

        # 4. Fallback to Local LLM (Ollama)
        if self.llm:
            try:
                response = self.llm.generate(prompt)
                return response
            except Exception as e:
                print(f"⚠️ Local LLM Error: {e}. Using final mock fallback.")

        # 5. Final Mock Fallback
        return json.dumps({
            "plan_id": str(uuid.uuid4()),
            "total_steps": 1,
            "dag": [{
                "step_number": 1,
                "agent_role": "knowledge_architect",
                "action": "research",
                "instruction": "Process the user request",
                "depends_on": []
            }],
            "expected_outcome": "Task completion"
        })

    def decompose_task(self, user_input: str, master_task_id: str, conversation_history: List[Dict] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Uses Cloud LLM to break down a complex prompt into a DAG of sub-tasks.
        NEW: Handles context compression for long conversation history.
        Persists the DAG into the database as individual tasks.
        """
        # NEW: Apply context compression if conversation history is provided
        if conversation_history and len(conversation_history) > 10:
            logger.info(f"Long conversation detected ({len(conversation_history)} messages). Applying context compression...")
            compression_result = self.context_compressor.handle_context_overflow(
                conversation_history,
                user_input,
                max_tokens=6000  # Reserve tokens for DAG decomposition
            )
            compressed_history = compression_result["optimized_context"]
            logger.info(f"Context compression: {compression_result['original_tokens']} → {compression_result['optimized_tokens']} tokens")
            
            # Include compressed context in the prompt
            augmented_input = f"CONVERSATION CONTEXT (COMPRESSED):\n{compressed_history}\n\nCURRENT REQUEST:\n{user_input}"
        else:
            augmented_input = user_input
        
        prompt = DECOMPOSITION_PROMPT.format(user_input=augmented_input)

        # Call Cloud LLM
        raw_plan = self.call_cloud_llm(prompt)

        try:
            # Validate JSON
            success, plan_data, error = self.validator.validate_generic_json(
                raw_plan,
                expected_keys=['plan_id', 'total_steps', 'dag', 'expected_outcome']
            )

            if not success:
                logger.error(f"Cloud Brain validation failed: {error}")
                return None

            # Validate with Pydantic
            validated_plan = MasterPlan(**plan_data)

            # Persist the DAG into the database as individual tasks
            self._persist_dag(master_task_id, validated_plan.dag)

            logger.info(f"DAG decomposed successfully | Steps: {len(validated_plan.dag)} | Master Task: {master_task_id}")
            return validated_plan.dag

        except Exception as e:
            logger.error(f"Cloud Brain failure: {e}")
            return None

    def _persist_dag(self, master_task_id: str, dag: List[SubTask]):
        """
        Converts the DAG into actual database records (sub-tasks).
        """
        for step in dag:
            sub_task_id = f"{master_task_id}_step_{step.step_number}"

            self.db.create_task({
                "task_id": sub_task_id,
                "priority": "medium",
                "agent_role": step.agent_role,
                "action": step.action,
                "payload": {
                    "instruction": step.instruction,
                    "parent_id": master_task_id
                },
                "status": "pending",
                "constraints": [f"depends_on: {step.depends_on}"],
                "parent_task_id": master_task_id
            })

    def get_execution_order(self, dag: List[SubTask]) -> List[int]:
        """
        Determines the execution order of tasks based on dependencies.
        Returns a list of step_numbers in the order they should be executed.
        """
        executed = set()
        order = []

        while len(executed) < len(dag):
            for step in dag:
                if step.step_number not in executed:
                    # Check if all dependencies are satisfied
                    if all(dep in executed for dep in step.depends_on):
                        order.append(step.step_number)
                        executed.add(step.step_number)

        return order
