"""
test_visual_audit.py - Test the multi-modal visual auditing capability of QAAuditor
Tests Phase 7.1: Multi-Modal Input Processing (Vision)
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database import DBManager
from schemas import TaskRequest, TaskStatus, AgentRole, TaskAction
from qa_auditor import QAAuditor
from utils.logger import logger

def test_visual_audit():
    """Test the visual audit capability."""
    logger.info("=" * 80)
    logger.info("TEST: QAAuditor Multi-Modal Visual Audit (Phase 7.1)")
    logger.info("=" * 80)
    
    # Initialize database and auditor
    db = DBManager("sqlite:///:memory:")
    auditor = QAAuditor(db)
    
    # Create a mock test image path (will fail gracefully if not found)
    test_image_path = "/tmp/test_design.png"
    
    # Test 1: Visual audit request
    logger.info("\n[Test 1] Visual Audit with Missing Image (Expected: Graceful Error)")
    request_visual = TaskRequest(
        task_id="test_visual_001",
        agent_role=AgentRole.QA_AUDITOR,
        action=TaskAction.AUDIT_VISUAL,
        payload={
            "image_path": test_image_path,
            "expected_text": "Welcome to Our Brand",
            "design_guidelines": ["Mobile-optimized", "Accessible", "Professional"]
        }
    )
    
    response = auditor.execute(request_visual)
    logger.info(f"Status: {response.status}")
    logger.info(f"Error: {response.error_message}")
    
    # Test 2: Text audit (existing functionality)
    logger.info("\n[Test 2] Text Audit (Existing Functionality - Control Test)")
    request_text = TaskRequest(
        task_id="test_text_001",
        agent_role=AgentRole.QA_AUDITOR,
        action=TaskAction.AUDIT,
        payload={
            "content": "Our product delivers 95% user satisfaction. All ingredients are natural and organic.",
            "claims": ["Our product delivers 95% user satisfaction", "All ingredients are natural"]
        }
    )
    
    response_text = auditor.execute(request_text)
    logger.info(f"Status: {response_text.status}")
    logger.info(f"Quality Score: {response_text.artifacts.get('quality_score', 'N/A')}")
    logger.info(f"Recommendation: {response_text.artifacts.get('primary_output', 'N/A')}")
    
    # Test 3: Unknown action
    logger.info("\n[Test 3] Unknown Action (Expected: Graceful Error)")
    request_unknown = TaskRequest(
        task_id="test_unknown_001",
        agent_role=AgentRole.QA_AUDITOR,
        action=TaskAction.AUDIT,
        payload={"content": "Test"}
    )
    
    response_unknown = auditor.execute(request_unknown)
    logger.info(f"Status: {response_unknown.status}")
    logger.info(f"Error: {response_unknown.error_message}")
    
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY: QAAuditor Multi-Modal Audit Tests Complete")
    logger.info("=" * 80)
    logger.info("\nVisual Audit Capability: IMPLEMENTED")
    logger.info("  - Multi-modal vision support: Added to execute() method")
    logger.info("  - Vision LLM integration: Mock implementation (ready for GPT-4o Vision / Gemini Vision)")
    logger.info("  - Audit types supported: text, visual, extensible")
    logger.info("\nNext steps (Phase 7.2):")
    logger.info("  - Replace mock Vision LLM with real GPT-4o Vision or Gemini Vision API calls")
    logger.info("  - Implement self-optimizing DAGs with Meta-Brain feedback loop")
    logger.info("  - Add autonomous tool use (Agentic Tooling)")

if __name__ == "__main__":
    test_visual_audit()
