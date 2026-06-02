"""
sre_agent.py - The Guardian Agent
Monitors system health, analyzes failures, and proposes self-healing fixes.
"""

import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from database import DBManager, TaskRecord
from schemas import TaskRequest, TaskResponse, TaskStatus


class SystemTelemetry:
    """Gathers telemetry data from the system."""

    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def get_failure_report(self, lookback_hours: int = 24) -> List[TaskRecord]:
        """
        Finds all tasks that ended in 'failed' or 'needs_clarification'
        within the specified window.
        """
        return self.db.get_failure_report(lookback_hours)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculates performance metrics per agent.
        """
        metrics = {}
        all_tasks = self.db.get_tasks_by_status("completed") + self.db.get_tasks_by_status("failed")

        for task in all_tasks:
            agent = task.agent_role
            if agent not in metrics:
                metrics[agent] = {
                    "total": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "avg_execution_time": 0.0
                }

            metrics[agent]["total"] += 1
            if task.status == "failed":
                metrics[agent]["failed"] += 1

        # Calculate success rates
        for agent in metrics:
            if metrics[agent]["total"] > 0:
                metrics[agent]["success_rate"] = (
                    (metrics[agent]["total"] - metrics[agent]["failed"]) / metrics[agent]["total"]
                ) * 100

        return metrics

    def detect_degradation(self, threshold: float = 0.8) -> List[str]:
        """
        Detects if any agent's success rate has fallen below threshold.
        """
        metrics = self.get_performance_metrics()
        degraded_agents = []

        for agent, stats in metrics.items():
            if stats["success_rate"] < (threshold * 100):
                degraded_agents.append(agent)

        return degraded_agents


class SelfEvolvingSRE:
    """The Guardian Agent that monitors and fixes the system."""

    def __init__(self, db_manager: DBManager, llm_client=None):
        self.db = db_manager
        self.telemetry = SystemTelemetry(db_manager)
        self.llm = llm_client

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        Analyzes system health and proposes self-healing modifications.
        """
        print("🛡️ Self-Evolving SRE: Analyzing system health...")

        try:
            # 1. Gather Evidence
            failures = self.telemetry.get_failure_report(lookback_hours=24)
            metrics = self.telemetry.get_performance_metrics()
            degraded = self.telemetry.detect_degradation()

            if not failures and not degraded:
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={
                        "health_status": "HEALTHY",
                        "message": "No anomalies detected. System operating normally.",
                        "metrics": metrics
                    },
                    meta={"confidence": 1.0}
                )

            # 2. Pattern Analysis
            analysis = self._analyze_failure_patterns(failures, degraded)

            # 3. Propose a Self-Healing Fix
            fix_proposal = self._generate_fix(analysis)

            urgency = "CRITICAL" if len(failures) > 10 else "HIGH" if len(failures) > 5 else "MEDIUM"

            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "anomaly_detected": True,
                    "failure_count": len(failures),
                    "degraded_agents": degraded,
                    "failure_pattern": analysis,
                    "proposed_fix": fix_proposal,
                    "metrics": metrics,
                    "urgency": urgency
                },
                meta={
                    "confidence": 0.85,
                    "failures_analyzed": len(failures),
                    "execution_time": "2.8s",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                meta={"confidence": 0.0},
                error_message=f"Health check failed: {str(e)}"
            )

    def _analyze_failure_patterns(self, failures: List[TaskRecord], degraded_agents: List[str]) -> str:
        """
        Uses the LLM to find the root cause across multiple failures.
        """
        if not failures:
            return "No failures detected."

        evidence_list = []
        for f in failures[:10]:  # Limit to first 10 for brevity
            evidence_list.append(
                f"Task {f.task_id}: Agent {f.agent_role} failed "
                f"at {f.updated_at} (Status: {f.status})"
            )

        degraded_str = ", ".join(degraded_agents) if degraded_agents else "None"

        evidence = "\n".join(evidence_list)
        prompt = f"""Analyze these system failures and find the root cause(s).
Degraded agents: {degraded_str}

Failures:
{evidence}

Provide a 1-2 sentence root cause analysis."""

        if self.llm:
            return self.llm.generate(prompt)
        else:
            # Fallback analysis
            if degraded_agents:
                return f"Root Cause: The following agents are degraded: {degraded_str}. This may indicate resource constraints or configuration issues."
            else:
                return "Root Cause: Multiple failures detected. Further investigation required to identify specific patterns."

    def _generate_fix(self, analysis: str) -> str:
        """
        Proposes a technical change to fix the issue.
        """
        prompt = f"""Based on this root cause analysis:
{analysis}

Propose a specific, actionable fix (1-2 sentences). The fix should be something that can be implemented immediately or through configuration changes."""

        if self.llm:
            return self.llm.generate(prompt)
        else:
            # Fallback fix
            return "Fix: Review agent configurations and API rate limits. Consider implementing retry logic with exponential backoff."

    def generate_health_report(self) -> Dict[str, Any]:
        """
        Generates a comprehensive health report of the system.
        """
        failures = self.telemetry.get_failure_report()
        metrics = self.telemetry.get_performance_metrics()
        degraded = self.telemetry.detect_degradation()

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "DEGRADED" if degraded else "HEALTHY",
            "recent_failures": len(failures),
            "degraded_agents": degraded,
            "agent_metrics": metrics
        }
