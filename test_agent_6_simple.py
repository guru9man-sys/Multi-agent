# -*- coding: utf-8 -*-
"""
test_agent_6_qa_auditor_simple.py - Simple Verification Tests for Agent 6
Tests the QA & Ethics Auditor agent functionality.
"""

import json
import sys
from datetime import datetime


def test_agent_6_basic_verification():
    """Basic verification that Agent 6 files exist and have correct structure."""
    print("\n" + "="*70)
    print("AGENT 6: QA & ETHICS AUDITOR - VERIFICATION")
    print("="*70 + "\n")
    
    # Try importing the modules
    try:
        from qa_auditor import QAAuditor, FactChecker, BiasDetector, ComplianceValidator
        print("[PASS] Successfully imported QA Auditor components")
    except ImportError as e:
        print(f"[FAIL] Could not import qa_auditor: {e}")
        return False
    
    try:
        from schemas import (
            TaskRequest, TaskResponse, TaskStatus, 
            AgentRole, TaskAction, AgentRole,
            FactCheckResult, BiasAnalysis, ComplianceReport, AuditResult
        )
        print("[PASS] Successfully imported new schemas")
    except ImportError as e:
        print(f"[FAIL] Could not import schemas: {e}")
        return False
    
    try:
        from database import DBManager
        print("[PASS] Successfully imported DBManager")
    except ImportError as e:
        print(f"[FAIL] Could not import database: {e}")
        return False
    
    # Verify enums
    try:
        assert hasattr(AgentRole, 'QA_AUDITOR'), "QA_AUDITOR role not found"
        assert hasattr(TaskAction, 'AUDIT'), "AUDIT action not found"
        print("[PASS] New enum values added to schemas")
    except AssertionError as e:
        print(f"[FAIL] Enum verification: {e}")
        return False
    
    # Test FactChecker initialization
    try:
        db = DBManager()
        checker = FactChecker(db)
        print("[PASS] FactChecker initialized successfully")
    except Exception as e:
        print(f"[FAIL] FactChecker initialization: {e}")
        return False
    
    # Test BiasDetector initialization
    try:
        detector = BiasDetector()
        print("[PASS] BiasDetector initialized successfully")
    except Exception as e:
        print(f"[FAIL] BiasDetector initialization: {e}")
        return False
    
    # Test ComplianceValidator initialization
    try:
        validator = ComplianceValidator()
        print("[PASS] ComplianceValidator initialized successfully")
    except Exception as e:
        print(f"[FAIL] ComplianceValidator initialization: {e}")
        return False
    
    # Test QAAuditor initialization
    try:
        db = DBManager()
        auditor = QAAuditor(db)
        print("[PASS] QAAuditor initialized successfully")
    except Exception as e:
        print(f"[FAIL] QAAuditor initialization: {e}")
        return False
    
    # Test method existence
    try:
        assert hasattr(auditor, 'execute'), "execute method not found in QAAuditor"
        assert hasattr(checker, 'fact_check_claim'), "fact_check_claim method not found"
        assert hasattr(detector, 'detect_bias'), "detect_bias method not found"
        assert hasattr(validator, 'validate_compliance'), "validate_compliance method not found"
        print("[PASS] All required methods exist")
    except AssertionError as e:
        print(f"[FAIL] Method verification: {e}")
        return False
    
    # Test orchestrator integration
    try:
        from orchestrator_main import AgentOrchestrator
        orch = AgentOrchestrator(db)
        assert hasattr(orch, 'qa_auditor'), "qa_auditor not found in orchestrator"
        print("[PASS] QA Auditor integrated into Orchestrator")
    except Exception as e:
        print(f"[FAIL] Orchestrator integration: {e}")
        return False
    
    print("\n" + "="*70)
    print("SUCCESS: All verification tests passed!")
    print("Agent 6 (QA & Ethics Auditor) is ready for use.")
    print("="*70 + "\n")
    return True


if __name__ == "__main__":
    try:
        success = test_agent_6_basic_verification()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
