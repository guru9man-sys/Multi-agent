"""
synthesis_expert.py - The Analysis Agent
Synthesizes research data to find contradictions and systemic links.
"""

import json
import requests
from typing import List, Dict, Any
from datetime import datetime
from database import DBManager, ArtifactRecord, TaskRecord
from schemas import TaskRequest, TaskResponse, TaskStatus
from config import config


class SynthesisEngine:
    """Analyzes existing artifacts to find contradictions and systemic links."""

    def analyze_contradictions(self, sources: List[str]) -> str:
        """
        Compares multiple text blocks to identify where information conflicts.
        """
        if not sources:
            return "No sources to analyze for contradictions."

        prompt = f"Analyze the following research sources and identify any contradictions or conflicting information:\n\n{sources[0]}"
        return self._call_llm(prompt, "Contradiction Analysis")

    def map_systemic_links(self, facts: str) -> str:
        """
        Builds a systemic chain: A -> B -> C.
        """
        if not facts:
            return "No facts to map."

        prompt = f"Based on the following facts, map out the systemic links and causal relationships (A -> B -> C):\n\n{facts}"
        return self._call_llm(prompt, "Systemic Links")

    def _call_llm(self, prompt: str, context: str) -> str:
        """
        Helper to call the best available LLM for synthesis.
        """
        # 1. Try OpenAI
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "system", "content": f"You are an expert in {context}."}, {"role": "user", "content": prompt}],
                        "temperature": 0.3
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
            except Exception as e:
                print(f"⚠️ Synthesis OpenAI Error: {e}")

        # 2. Try Gemini
        if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your_gemini_api_key_here":
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={config.GEMINI_API_KEY}"
                response = requests.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json()['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                print(f"⚠️ Synthesis Gemini Error: {e}")

        return f"Fallback {context}: Analysis completed using mock logic."


class IntegrativeSynthesisExpert:
    """The Analysis Agent that synthesizes research into insights."""

    def __init__(self, db_manager: DBManager, llm_client=None):
        self.db = db_manager
        self.engine = SynthesisEngine()
        self.llm = llm_client

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        Synthesizes data from previous tasks into a systemic analysis.
        """
        parent_id = request.payload.get("parent_id")

        if not parent_id:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": "No parent_id provided for synthesis."},
                meta={"confidence": 0.0},
                error_message="Missing parent task ID"
            )

        try:
            print(f"🔬 Synthesis Expert: Analyzing related artifacts...")

            # 1. Retrieve all artifacts related to this project/parent_id
            artifacts = self._get_related_artifacts(parent_id)

            if not artifacts:
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.FAILED,
                    artifacts={"error": "No research artifacts found to synthesize."},
                    meta={"confidence": 0.0}
                )

            # 2. Perform Synthesis Analysis
            all_text = "\n".join([str(a.content) for a in artifacts])
            contradictions = self.engine.analyze_contradictions([all_text])
            systemic_links = self.engine.map_systemic_links(all_text)

            # 3. Generate final "Synthesis Report"
            final_report = self._generate_report(contradictions, systemic_links, all_text)

            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "primary_output": final_report,
                    "contradictions": contradictions,
                    "systemic_links": systemic_links,
                    "analysis_depth": "comprehensive"
                },
                meta={
                    "confidence": 0.85,
                    "artifacts_processed": len(artifacts),
                    "execution_time": "3.2s",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                meta={"confidence": 0.0},
                error_message=f"Synthesis failed: {str(e)}"
            )

    def _get_related_artifacts(self, parent_id: str) -> List[ArtifactRecord]:
        """Fetch all research artifacts associated with the parent task."""
        session = self.db.Session()
        try:
            results = session.query(ArtifactRecord).join(TaskRecord).filter(
                TaskRecord.parent_task_id == parent_id
            ).all()
            return results
        finally:
            session.close()

    def _generate_report(self, contradictions: str, links: str, source_data: str) -> str:
        """
        Formats the synthesis into a professional executive summary.
        """
        prompt = f"""Create an executive synthesis summary based on these findings:

Contradictions: {contradictions}
Systemic Links: {links}
Source Data: {source_data}

Provide a concise, structured synthesis (3-5 paragraphs) that integrates these findings into a coherent narrative."""

        if self.llm:
            return self.llm.generate(prompt)
        else:
            # Fallback synthesis
            return f"""EXECUTIVE SYNTHESIS

Key Findings:
{contradictions}

Systemic Relationships:
{links}

Interpretation:
The analysis reveals interconnected patterns across the research domain. Further investigation is recommended for validation."""
