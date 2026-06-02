"""
meta_brain.py - Phase 7.2: Self-Optimizing DAGs with Meta-Brain Feedback Loop
Analyzes execution patterns and suggests DAG optimizations based on historical performance data.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from database import DBManager
from config import config
from utils.logger import logger
import requests
from utils.resilience import retry_with_backoff


@dataclass
class ExecutionMetrics:
    """Captures metrics for a single DAG execution."""
    task_id: str
    step_number: int
    agent_role: str
    action: str
    duration_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    success: bool
    dependencies: List[int]
    parallelizable_with: List[int]  # Steps that could run in parallel
    created_at: str


@dataclass
class DAGOptimization:
    """Suggests optimizations for DAG decomposition."""
    optimization_id: str
    optimization_type: str  # "reorder", "consolidate", "parallelize", "split"
    current_order: List[int]
    suggested_order: List[int]
    reason: str
    estimated_speedup: float  # Expected time reduction (0.0-1.0)
    estimated_token_savings: int
    confidence: float  # 0.0-1.0
    success_history: int  # Number of times this worked
    created_at: str

@dataclass
class LearnedSkill:
    """Represents a skill learned from successful execution patterns."""
    skill_id: str
    skill_name: str
    category: str  # "research", "analysis", "content", "system"
    pattern_description: str
    associated_agents: List[str]
    success_rate: float
    avg_token_efficiency: float
    usage_count: int
    last_used: str
    metadata: Dict[str, Any]

@dataclass
class SkillPerformance:
    """Tracks the performance of a specific skill over time."""
    skill_id: str
    execution_id: str
    success: bool
    duration_seconds: float
    tokens_used: int
    timestamp: str



class MetaBrain:
    """
    Analyzes execution patterns and proposes DAG optimizations.
    Learns from historical executions to improve decomposition strategies.
    """

    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.cache_duration = 3600  # 1 hour
        self.min_historical_samples = 5  # Need 5+ samples before suggesting optimizations
        self.skill_registry: Dict[str, LearnedSkill] = {}
        self._load_skill_registry()

    def _load_skill_registry(self):
        """Loads learned skills from the database."""
        try:
            data = self.db.get_cached_data("skill_registry")
            if data:
                skills_list = json.loads(data)
                for s in skills_list:
                    self.skill_registry[s['skill_id']] = LearnedSkill(**s)
                logger.info(f"Loaded {len(self.skill_registry)} learned skills from DB")
        except Exception as e:
            logger.error(f"Failed to load skill registry: {e}")

    def _save_skill_registry(self):
        """Saves current skill registry to the database."""
        try:
            skills_data = [asdict(s) for s in self.skill_registry.values()]
            self.db.store_cached_data("skill_registry", json.dumps(skills_data))
        except Exception as e:
            logger.error(f"Failed to save skill registry: {e}")

    def learn_from_execution(self, task_id: str, execution_metrics: List[ExecutionMetrics]) -> Optional[LearnedSkill]:
        """
        Analyzes a successful execution sequence to extract a 'skill'.
        A skill is defined as a pattern of agent interactions that led to a high-confidence success.
        """
        # Only learn from fully successful sequences
        if not all(m.success for m in execution_metrics):
            return None

        # Extract pattern: Agent Sequence + Actions
        pattern = " -> ".join([f"{m.agent_role}:{m.action}" for m in execution_metrics])
        
        # Calculate efficiency
        total_tokens = sum(m.total_tokens for m in execution_metrics)
        avg_efficiency = total_tokens / len(execution_metrics) if execution_metrics else 0

        # Create a unique skill ID based on the pattern
        import hashlib
        skill_id = "skill_" + hashlib.md5(pattern.encode()).hexdigest()[:8]

        if skill_id in self.skill_registry:
            # Update existing skill
            skill = self.skill_registry[skill_id]
            skill.usage_count += 1
            skill.last_used = datetime.now().isoformat()
            # Moving average for efficiency
            skill.avg_token_efficiency = (skill.avg_token_efficiency + avg_efficiency) / 2
            logger.info(f"Updated existing skill: {skill.skill_name} ({skill_id})")
        else:
            # Learn new skill
            new_skill = LearnedSkill(
                skill_id=skill_id,
                skill_name=f"Pattern_{skill_id}",
                category=self._determine_category(execution_metrics),
                pattern_description=pattern,
                associated_agents=[m.agent_role for m in execution_metrics],
                success_rate=1.0,
                avg_token_efficiency=avg_efficiency,
                usage_count=1,
                last_used=datetime.now().isoformat(),
                metadata={"initial_task_id": task_id}
            )
            self.skill_registry[skill_id] = new_skill
            logger.info(f"Learned new skill: {new_skill.skill_name} | Pattern: {pattern}")
            self._save_skill_registry()

        return self.skill_registry[skill_id]

    def track_skill_performance(self, skill_id: str, execution_id: str, success: bool, duration: float, tokens: int):
        """
        Records the performance of a specific skill usage.
        """
        perf = SkillPerformance(
            skill_id=skill_id,
            execution_id=execution_id,
            success=success,
            duration_seconds=duration,
            tokens_used=tokens,
            timestamp=datetime.now().isoformat()
        )
        
        # Store performance record
        self.db.store_execution_metrics(f"perf_{skill_id}_{execution_id}", asdict(perf))
        
        # Update skill stats
        if skill_id in self.skill_registry:
            skill = self.skill_registry[skill_id]
            # Update success rate (simple moving average)
            skill.success_rate = (skill.success_rate * skill.usage_count + (1.0 if success else 0.0)) / (skill.usage_count + 1)
            skill.usage_count += 1
            skill.last_used = datetime.now().isoformat()
            self._save_skill_registry()

    def get_recommended_skills(self, category: str, min_confidence: float = 0.7) -> List[LearnedSkill]:
        """
        Returns the most effective skills for a given category.
        """
        matching_skills = [
            s for s in self.skill_registry.values() 
            if s.category == category and s.success_rate >= min_confidence
        ]
        # Sort by success rate and then by token efficiency
        return sorted(matching_skills, key=lambda x: (x.success_rate, -x.avg_token_efficiency), reverse=True)

    def suggest_skill_based_optimization(self, current_pattern: str) -> Optional[Tuple[str, str]]:
        """
        Compares current execution pattern with learned skills to suggest a better one.
        Returns (suggested_skill_id, reason) or None.
        """
        if not self.skill_registry:
            return None

        for skill_id, skill in self.skill_registry.items():
            if skill.pattern_description == current_pattern:
                # If we found the same pattern, we can't "optimize" it, but we can confirm it's a known skill
                return None
            
            # If the pattern is similar (shares agents) but the skill has much higher success rate
            current_agents = set([a for a in current_pattern.split(" -> ")]) # Simplified
            skill_agents = set(skill.associated_agents)
            
            if current_agents.issubset(skill_agents) and skill.success_rate > 0.9:
                return skill_id, f"Learned skill {skill.skill_name} has higher success rate for this agent set."

        return None



    def capture_execution_metrics(
        self,
        task_id: str,
        step_number: int,
        agent_role: str,
        action: str,
        duration_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        success: bool,
        dependencies: List[int],
        parallelizable_with: List[int] = None
    ) -> ExecutionMetrics:
        """
        Captures metrics from a completed step for later analysis.
        Called after each step in a DAG execution.
        """
        if parallelizable_with is None:
            parallelizable_with = []

        metrics = ExecutionMetrics(
            task_id=task_id,
            step_number=step_number,
            agent_role=agent_role,
            action=action,
            duration_seconds=duration_seconds,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            success=success,
            dependencies=dependencies,
            parallelizable_with=parallelizable_with,
            created_at=datetime.now().isoformat()
        )

        # Store in database
        self.db.store_execution_metrics(metrics.task_id, asdict(metrics))
        logger.info(f"Execution Metrics Captured | Step: {step_number} | Agent: {agent_role} | Duration: {duration_seconds:.2f}s | Tokens: {metrics.total_tokens}")

        return metrics

    def analyze_dag_pattern(self, dag_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes a DAG structure to identify optimization opportunities.
        Returns analysis with potential improvements.
        """
        step_numbers = [s.get("step_number") for s in dag_steps]
        dependencies = {s.get("step_number"): s.get("depends_on", []) for s in dag_steps}

        analysis = {
            "total_steps": len(dag_steps),
            "critical_path_length": self._calculate_critical_path(dependencies),
            "parallelization_opportunities": self._find_parallelizable_steps(dependencies),
            "consolidation_candidates": self._find_consolidation_candidates(dag_steps),
            "reordering_suggestions": self._suggest_reordering(dag_steps, dependencies),
            "analysis_timestamp": datetime.now().isoformat()
        }

        return analysis

    def _calculate_critical_path(self, dependencies: Dict[int, List[int]]) -> int:
        """
        Calculates the critical path (longest dependency chain) in the DAG.
        This determines minimum possible execution time.
        """
        memo = {}

        def longest_path_to(node):
            if node in memo:
                return memo[node]
            
            deps = dependencies.get(node, [])
            if not deps:
                return 1
            
            result = 1 + max(longest_path_to(d) for d in deps)
            memo[node] = result
            return result

        all_nodes = set(dependencies.keys())
        critical_length = max(longest_path_to(node) for node in all_nodes) if all_nodes else 1
        return critical_length

    def _find_parallelizable_steps(self, dependencies: Dict[int, List[int]]) -> List[Tuple[int, int]]:
        """
        Identifies pairs of steps that have no dependencies between them and can run in parallel.
        Returns list of (step1, step2) pairs.
        """
        parallelizable = []
        steps = list(dependencies.keys())

        for i, step1 in enumerate(steps):
            for step2 in steps[i+1:]:
                # Check if step1 depends on step2
                if step2 not in dependencies.get(step1, []):
                    # Check if step2 depends on step1
                    if step1 not in dependencies.get(step2, []):
                        parallelizable.append((step1, step2))

        return parallelizable

    def _find_consolidation_candidates(self, dag_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifies steps that could be consolidated (combined into a single agent call).
        Typically consecutive steps with the same agent or simple dependencies.
        """
        candidates = []

        for i, step in enumerate(dag_steps):
            if i + 1 < len(dag_steps):
                next_step = dag_steps[i + 1]
                
                # Check if next step depends only on current step
                if next_step.get("depends_on") == [step.get("step_number")]:
                    # Check if same agent or compatible agents
                    same_agent = step.get("agent_role") == next_step.get("agent_role")
                    
                    if same_agent:
                        candidates.append({
                            "steps": [step.get("step_number"), next_step.get("step_number")],
                            "reason": "Same agent with linear dependency",
                            "potential_savings": "1-2 seconds (context retention)"
                        })

        return candidates

    def _suggest_reordering(
        self,
        dag_steps: List[Dict[str, Any]],
        dependencies: Dict[int, List[int]]
    ) -> List[DAGOptimization]:
        """
        Suggests better orderings based on:
        1. Estimated execution time (longer tasks first to parallelize)
        2. Token efficiency
        3. Historical success patterns
        """
        suggestions = []

        # Strategy 1: Execute longer tasks first to maximize parallel execution
        step_by_duration = sorted(
            dag_steps,
            key=lambda s: s.get("estimated_duration", 0),
            reverse=True
        )

        if step_by_duration != dag_steps:
            current_order = [s.get("step_number") for s in dag_steps]
            suggested_order = [s.get("step_number") for s in step_by_duration]

            suggestion = DAGOptimization(
                optimization_id=f"reorder_{datetime.now().timestamp()}",
                optimization_type="reorder",
                current_order=current_order,
                suggested_order=suggested_order,
                reason="Execute longer tasks first to maximize parallel execution opportunities",
                estimated_speedup=0.15,  # Estimated 15% speedup
                estimated_token_savings=0,
                confidence=0.7,
                success_history=0,
                created_at=datetime.now().isoformat()
            )
            suggestions.append(suggestion)

        return suggestions

    def get_optimization_suggestions(self, dag_id: str) -> List[DAGOptimization]:
        """
        Retrieves cached optimization suggestions for a DAG pattern.
        Returns empty list if not enough historical data yet.
        """
        metrics = self.db.get_execution_metrics_for_dag(dag_id)

        if len(metrics) < self.min_historical_samples:
            logger.info(f"Not enough historical data for {dag_id}. Samples: {len(metrics)}/{self.min_historical_samples}")
            return []

        # Analyze patterns
        success_rate = sum(1 for m in metrics if m.get("success")) / len(metrics)
        avg_duration = sum(m.get("duration_seconds", 0) for m in metrics) / len(metrics)
        avg_tokens = sum(m.get("total_tokens", 0) for m in metrics) / len(metrics)

        suggestions = []

        # Suggest consolidation if same agent runs consecutively
        agent_sequence = [m.get("agent_role") for m in sorted(metrics, key=lambda x: x.get("step_number", 0))]
        for i, agent in enumerate(agent_sequence):
            if i + 1 < len(agent_sequence) and agent == agent_sequence[i + 1]:
                suggestion = DAGOptimization(
                    optimization_id=f"consolidate_{dag_id}_{i}",
                    optimization_type="consolidate",
                    current_order=[i, i + 1],
                    suggested_order=[i],  # Merge into one step
                    reason=f"Same agent ({agent}) running consecutively - can be consolidated",
                    estimated_speedup=0.1,  # Estimated 10% speedup from context reuse
                    estimated_token_savings=int(avg_tokens * 0.05),  # 5% token savings
                    confidence=0.85,
                    success_history=sum(1 for m in metrics if m.get("success")),
                    created_at=datetime.now().isoformat()
                )
                suggestions.append(suggestion)

        logger.info(f"Generated {len(suggestions)} optimization suggestions for {dag_id}")
        return suggestions

    def apply_optimization(self, optimization: DAGOptimization, dag: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applies an optimization suggestion to a DAG, returning the modified DAG.
        """
        if optimization.optimization_type == "reorder":
            # Reorder steps according to suggestion
            step_map = {s.get("step_number"): s for s in dag}
            reordered = [step_map[step_num] for step_num in optimization.suggested_order]
            return reordered

        elif optimization.optimization_type == "consolidate":
            # Merge suggested steps
            steps_to_merge = optimization.current_order
            consolidated_step = {
                "step_number": steps_to_merge[0],
                "agent_role": dag[steps_to_merge[0] - 1].get("agent_role"),
                "action": "consolidated",
                "instruction": f"Execute steps {steps_to_merge} as a single operation",
                "depends_on": dag[steps_to_merge[0] - 1].get("depends_on", [])
            }
            
            # Remove old steps and insert consolidated
            new_dag = [s for s in dag if s.get("step_number") not in steps_to_merge]
            new_dag.insert(steps_to_merge[0] - 1, consolidated_step)
            return new_dag

        elif optimization.optimization_type == "parallelize":
            # This typically doesn't modify DAG structure, but updates execution hints
            return dag

        return dag

    def generate_optimization_report(self, dag_id: str) -> Dict[str, Any]:
        """
        Generates a comprehensive report on DAG performance and optimization opportunities.
        """
        metrics = self.db.get_execution_metrics_for_dag(dag_id)

        if not metrics:
            return {"status": "no_data", "message": f"No execution data for {dag_id}"}

        total_executions = len(metrics)
        successful_executions = sum(1 for m in metrics if m.get("success"))
        failed_executions = total_executions - successful_executions

        total_duration = sum(m.get("duration_seconds", 0) for m in metrics)
        avg_duration = total_duration / total_executions
        total_tokens = sum(m.get("total_tokens", 0) for m in metrics)
        avg_tokens = total_tokens / total_executions

        # Agent performance
        agent_performance = {}
        for metric in metrics:
            agent = metric.get("agent_role")
            if agent not in agent_performance:
                agent_performance[agent] = {
                    "executions": 0,
                    "successes": 0,
                    "total_duration": 0,
                    "total_tokens": 0
                }
            
            agent_performance[agent]["executions"] += 1
            if metric.get("success"):
                agent_performance[agent]["successes"] += 1
            agent_performance[agent]["total_duration"] += metric.get("duration_seconds", 0)
            agent_performance[agent]["total_tokens"] += metric.get("total_tokens", 0)

        report = {
            "dag_id": dag_id,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "total_execution_time": total_duration,
            "average_execution_time": avg_duration,
            "total_tokens_used": total_tokens,
            "average_tokens_per_execution": avg_tokens,
            "agent_performance": agent_performance,
            "recommendations": self.get_optimization_suggestions(dag_id),
            "report_generated": datetime.now().isoformat()
        }

        return report

    @retry_with_backoff(retries=3, backoff_factor=2.0)
    def get_ai_insights(self, optimization_report: Dict[str, Any]) -> str:
        """
        Uses an LLM to analyze the optimization report and provide human-readable insights.
        """
        prompt = f"""Analyze this DAG execution report and provide actionable optimization insights:

Report Summary:
- Total Executions: {optimization_report.get('total_executions')}
- Success Rate: {optimization_report.get('success_rate', 0):.1%}
- Average Duration: {optimization_report.get('average_execution_time', 0):.2f}s
- Average Tokens: {optimization_report.get('average_tokens_per_execution', 0):.0f}

Agent Performance:
{json.dumps(optimization_report.get('agent_performance', {}), indent=2)}

Provide 2-3 specific, actionable recommendations to improve performance."""

        # Try to get AI insights
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY != "your_openai_api_key_here":
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 500
                    },
                    timeout=30
                )
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
            except Exception as e:
                logger.warning(f"Failed to get AI insights: {e}")
                return "AI insights unavailable"

        return "AI insights unavailable (no LLM configured)"
