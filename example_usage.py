"""
example_usage.py - Comprehensive Example
Demonstrates how to use the multi-agent system for a complex campaign.
"""

from database import DBManager
from orchestrator_main import AgentOrchestrator
from config import config
from schemas import TaskPriority


def main():
    """
    Example: Create a viral campaign for a health supplement
    This demonstrates the full pipeline:
    1. Research (Knowledge Architect)
    2. Analysis (Synthesis Expert)
    3. Content Creation (Social Media Mastery)
    4. System Health Check (SRE)
    """

    print("\n" + "="*70)
    print("MULTI-AGENT SYSTEM EXAMPLE: Health Supplement Campaign")
    print("="*70 + "\n")

    # Initialize system
    db = DBManager(config.DATABASE_URL)
    orchestrator = AgentOrchestrator(db, {
        "tavily_api_key": config.TAVILY_API_KEY,
    })

    # Example 1: Simple Task (Direct Routing)
    print("\n" + "-"*70)
    print("EXAMPLE 1: Simple Task - Create Social Media Content")
    print("-"*70)

    simple_request = "Create a LinkedIn post about the benefits of magnesium for sleep."
    result1 = orchestrator.handle_request(simple_request, priority=TaskPriority.HIGH)
    print(f"\nResult Status: {result1.get('status')}")
    print(f"Generated Content:\n{result1.get('artifacts', {}).get('campaign_package', {})}")

    # Example 2: Complex Task (Cloud Brain Decomposition)
    print("\n" + "-"*70)
    print("EXAMPLE 2: Complex Task - Full Campaign Pipeline")
    print("-"*70)

    complex_request = """
    Research the latest scientific findings on zinc supplementation,
    analyze if there are any contradictions in recent studies,
    and create viral content for LinkedIn, Twitter, and TikTok about the benefits.
    """

    result2 = orchestrator.handle_request(complex_request, priority=TaskPriority.HIGH)
    print(f"\nResult Status: {result2.get('status')}")
    print(f"Total Steps: {result2.get('total_steps')}")
    print(f"Completed Steps: {result2.get('completed_steps')}")

    # Print detailed results
    if result2.get('results'):
        for step, artifacts in result2.get('results').items():
            print(f"\n{step}:")
            print(f"  Primary Output: {str(artifacts.get('primary_output', ''))[:100]}...")

    # Example 3: System Health Check
    print("\n" + "-"*70)
    print("EXAMPLE 3: System Health Check")
    print("-"*70)

    health = orchestrator.get_system_health()
    print(f"\nSystem Health Status: {health.get('health_status')}")
    print(f"Recent Failures: {health.get('failure_count', 0)}")

    if health.get('metrics'):
        print("\nAgent Performance Metrics:")
        for agent, metrics in health.get('metrics').items():
            success_rate = metrics.get('success_rate', 0)
            print(f"  {agent}: {success_rate:.1f}% success rate ({metrics.get('total')} tasks)")

    # Example 4: Database Inspection
    print("\n" + "-"*70)
    print("EXAMPLE 4: Task History")
    print("-"*70)

    all_tasks = db.get_tasks_by_status("completed")
    print(f"\nTotal Completed Tasks: {len(all_tasks)}")

    if all_tasks:
        print("\nLast 5 Completed Tasks:")
        for task in all_tasks[-5:]:
            print(f"  - {task.task_id}: {task.agent_role} (Priority: {task.priority})")

    # Cleanup
    orchestrator.cleanup()

    print("\n" + "="*70)
    print("Example execution completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
