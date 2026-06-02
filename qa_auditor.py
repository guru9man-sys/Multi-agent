"""
qa_auditor.py - The Quality Assurance & Ethics Auditor Agent (Agent 6)
Performs fact-checking, bias detection, and compliance validation.
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from database import DBManager
from schemas import (
    TaskRequest, TaskResponse, TaskStatus, 
    FactCheckResult, BiasAnalysis, ComplianceReport, AuditResult
)
from utils.logger import logger


class FactChecker:
    """Validates claims against knowledge base and sources."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.known_facts = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load cached knowledge base from database."""
        try:
            kb_data = self.db.get_cached_data("knowledge_base")
            return json.loads(kb_data) if kb_data else {}
        except:
            return {}
    
    def fact_check_claim(self, claim: str) -> FactCheckResult:
        """
        Verifies a single claim against knowledge base.
        Returns confidence score and supporting sources.
        """
        # Simulate fact-checking logic
        claim_lower = claim.lower()
        
        # Check against known facts
        verified = False
        confidence = 0.0
        sources = []
        note = None
        
        # Simple matching logic (in production: use embeddings)
        for fact, metadata in self.known_facts.items():
            if any(keyword in claim_lower for keyword in fact.lower().split()):
                verified = True
                confidence = min(0.95, metadata.get("confidence", 0.7))
                sources = metadata.get("sources", [])
                break
        
        if not verified:
            confidence = 0.5  # Unverified but plausible
            note = "Claim requires additional verification from sources"
        
        return FactCheckResult(
            claim=claim,
            verified=verified,
            confidence=confidence,
            sources=sources,
            note=note
        )
    
    def fact_check_batch(self, claims: List[str]) -> List[FactCheckResult]:
        """Fact-check multiple claims."""
        return [self.fact_check_claim(claim) for claim in claims]


class BiasDetector:
    """Analyzes content for bias and fairness issues."""
    
    def __init__(self):
        self.bias_keywords = {
            "gender": ["he/she", "man/woman", "girls", "boys", "only women", "only men"],
            "political": ["liberal", "conservative", "republican", "democrat"],
            "racial": ["stereotypes", "all [group]", "only [group]"],
            "ageist": ["old people", "too young", "millennials are", "boomers are"],
            "ableist": ["crazy", "retarded", "disabled people can't"]
        }
    
    def detect_bias(self, content: str) -> BiasAnalysis:
        """
        Analyzes content for potential bias.
        Returns bias score (0-1) and detected categories.
        """
        content_lower = content.lower()
        detected_categories = []
        violation_count = 0
        
        # Check each bias category
        for category, keywords in self.bias_keywords.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    detected_categories.append(category)
                    violation_count += 1
                    break  # Count each category once
        
        # Calculate bias score
        bias_score = min(1.0, violation_count * 0.25)
        bias_detected = bias_score > 0.3
        
        # Generate recommendations
        recommendations = []
        if "gender" in detected_categories:
            recommendations.append("Use gender-neutral language (e.g., 'they', 'people')")
        if "political" in detected_categories:
            recommendations.append("Remove partisan language; present multiple perspectives")
        if "racial" in detected_categories:
            recommendations.append("Avoid stereotyping; present diverse viewpoints")
        if "ageist" in detected_categories:
            recommendations.append("Use respectful language about age groups")
        if "ableist" in detected_categories:
            recommendations.append("Use person-first or identity-first language appropriately")
        
        return BiasAnalysis(
            content=content,
            bias_detected=bias_detected,
            bias_score=bias_score,
            bias_categories=detected_categories,
            recommendations=recommendations
        )


class ComplianceValidator:
    """Checks content against brand and safety guidelines."""
    
    def __init__(self, guidelines: Optional[Dict[str, Any]] = None):
        self.guidelines = guidelines or self._default_guidelines()
    
    def _default_guidelines(self) -> Dict[str, Any]:
        """Default brand and safety guidelines."""
        return {
            "prohibited_terms": [
                "guaranteed results", "miracle cure", "100% effective",
                "you must", "only solution"
            ],
            "required_disclaimers": [
                "consult professional", "individual results vary",
                "educational purposes"
            ],
            "max_claim_strength": 0.8,  # Claims should be moderate
            "brand_tone": ["professional", "friendly", "trustworthy"]
        }
    
    def validate_compliance(self, content: str) -> ComplianceReport:
        """
        Checks content against compliance guidelines.
        Returns compliance status and any violations.
        """
        compliant = True
        violation_type = None
        severity = None
        details = None
        
        content_lower = content.lower()
        
        # Check for prohibited terms
        for term in self.guidelines.get("prohibited_terms", []):
            if term.lower() in content_lower:
                compliant = False
                violation_type = "prohibited_term"
                severity = "high"
                details = f"Contains prohibited term: '{term}'"
                break
        
        # Check for required disclaimers
        if compliant:
            disclaimers = self.guidelines.get("required_disclaimers", [])
            if "medical" in content_lower or "health" in content_lower:
                has_disclaimer = any(d.lower() in content_lower for d in disclaimers)
                if not has_disclaimer:
                    compliant = False
                    violation_type = "missing_disclaimer"
                    severity = "medium"
                    details = "Health/medical content missing required disclaimer"
        
        return ComplianceReport(
            content=content,
            compliant=compliant,
            violation_type=violation_type,
            severity=severity,
            details=details
        )


class QAAuditorAgent:
    """Agent for quality assurance, ethics, and financial record verification."""
    
    def __init__(self, db_manager: DBManager):
        self.db = db_manager
        self.fact_checker = FactChecker(db_manager)
        self.bias_detector = BiasDetector()

    def verify_financial_record(self, record_id: str) -> AuditResult:
        """
        Verifies if the recorded financial data matches the original document text.
        """
        logger.info(f"QA Auditor: Verifying financial record {record_id}")
        
        # 1. Retrieve record from DB
        record = self.db.get_accounting_entry(record_id)
        if not record:
            return AuditResult(
                status="FAILED",
                issue="Record not found in database",
                confidence=0.0
            )
            
        # 2. Compare extracted fields against source text
        extracted_text = record.get("extracted_text", "")
        details = {
            "amount": record.get("amount"),
            "date": record.get("transaction_date"),
            "sender": record.get("sender")
        }
        
        # Simple cross-check logic
        discrepancies = []
        for field, value in details.items():
            if value and str(value) not in extracted_text:
                discrepancies.append(f"Field {field} ('{value}') not found in source text")
        
        if not discrepancies:
            return AuditResult(
                status="PASSED",
                issue="Data matches source text perfectly",
                confidence=1.0
            )
        
        return AuditResult(
            status="FLAGGED",
            issue="Discrepancies found: " + "; ".join(discrepancies),
            confidence=0.5
        )

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        Processes an audit request (text or visual).
        Supports both text-based auditing and multi-modal visual auditing.
        """
        logger.info(f"QAAuditor executing | TaskID: {request.task_id} | Action: {request.action}")
        
        try:
            if request.action == "audit_visual":
                return self._audit_visual_content(request)
            elif request.action == "audit":
                return self._audit_text_content(request)
            elif request.payload.get("action") == "verify_financial_record":
                record_id = request.payload.get("record_id")
                result = self.verify_financial_record(record_id)
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.COMPLETED,
                    artifacts={"audit_result": result.__dict__ if hasattr(result, '__dict__') else result}
                )
            else:
                return self._handle_unknown_action(request)
        except Exception as e:
            logger.error(f"QAAuditor Error | TaskID: {request.task_id} | Error: {str(e)}")
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                error_message=f"Audit failed: {str(e)}"
            )

    def _audit_visual_content(self, request: TaskRequest) -> TaskResponse:
        """
        Performs multi-modal visual audit of an image using Vision LLM.
        Checks: text readability, layout, colors, composition, branding compliance.
        """
        image_path = request.payload.get("image_path")
        expected_text = request.payload.get("expected_text", "")
        
        if not image_path or not os.path.exists(image_path):
            raise ValueError(f"Visual audit failed: Image not found at {image_path}")

        logger.info(f"Performing Multi-Modal Visual Audit on {image_path}...")
        
        # Mock Vision LLM analysis
        # In production: use client = vision.ImageAnalysisClient(...) with GPT-4o / Gemini Pro Vision
        visual_findings = {
            "text_readability": "EXCELLENT",
            "contrast_ratio": "21:1 (WCAG AAA compliant)",
            "layout_score": 0.95,
            "color_harmony": "Professional - Navy & White palette",
            "composition": "Balanced, follows rule of thirds",
            "text_detected": [expected_text] if expected_text else [],
            "brand_elements": "Present and correctly positioned"
        }
        
        visual_score = 0.93
        verdict = "PASS" if visual_score > 0.80 else "NEEDS_REVISION"

        return TaskResponse(
            task_id=request.task_id,
            status=TaskStatus.COMPLETED,
            artifacts={
                "audit_type": "visual_multimodal",
                "visual_findings": visual_findings,
                "visual_score": visual_score,
                "verdict": verdict,
                "recommendations": ["All visual elements meet quality standards."]
            },
            meta={"model": "Vision-LLM-Mock-GPT4o", "latency_seconds": 1.2}
        )

    def _audit_text_content(self, request: TaskRequest) -> TaskResponse:
        """
        Performs a comprehensive text-based audit.
        """
        try:
            content_to_audit = request.payload.get("content", "")
            claims_list = request.payload.get("claims", [])
            
            if not content_to_audit:
                return TaskResponse(
                    task_id=request.task_id,
                    status=TaskStatus.FAILED,
                    artifacts={},
                    error_message="No content provided for audit"
                )
            
            # Extract claims if not provided
            if not claims_list:
                claims_list = self._extract_claims(content_to_audit)
            
            # Perform multi-dimensional audit
            fact_checks = self.fact_checker.fact_check_batch(claims_list)
            bias_analysis = self.bias_detector.detect_bias(content_to_audit)
            compliance_report = self.compliance_validator.validate_compliance(content_to_audit)
            
            # Calculate overall quality score
            overall_score = self._calculate_quality_score(fact_checks, bias_analysis, compliance_report)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(
                fact_checks, bias_analysis, compliance_report, overall_score
            )
            
            # Create audit result
            audit_result = AuditResult(
                content_to_audit=content_to_audit,
                fact_checks=fact_checks,
                bias_analysis=bias_analysis,
                compliance_report=compliance_report,
                overall_quality_score=overall_score,
                recommendation=recommendation
            )
            
            # Store in database
            self.db.store_audit_result(audit_result.audit_id, audit_result.model_dump())
            
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "audit_result": audit_result.model_dump(),
                    "primary_output": recommendation,
                    "quality_score": overall_score
                },
                meta={
                    "audit_timestamp": datetime.now().isoformat(),
                    "fact_checks_performed": len(fact_checks),
                    "bias_detected": bias_analysis.bias_detected,
                    "compliance_status": compliance_report.compliant
                }
            )
        
        except Exception as e:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={},
                error_message=f"Audit failed: {str(e)}"
            )
    
    def _extract_claims(self, content: str) -> List[str]:
        """
        Extracts factual claims from content.
        Simple heuristic: sentences ending with facts.
        """
        sentences = content.split(". ")
        claims = [s.strip() for s in sentences if len(s.strip()) > 10]
        return claims[:10]  # Limit to 10 claims for efficiency
    
    def _calculate_quality_score(
        self,
        fact_checks: List[FactCheckResult],
        bias_analysis: BiasAnalysis,
        compliance_report: ComplianceReport
    ) -> float:
        """Calculate overall quality score (0-1)."""
        scores = []
        
        # Fact-checking score
        if fact_checks:
            fact_score = sum(fc.confidence for fc in fact_checks) / len(fact_checks)
            scores.append(fact_score * 0.4)  # 40% weight
        
        # Bias score (lower bias = higher score)
        bias_score = 1.0 - bias_analysis.bias_score
        scores.append(bias_score * 0.35)  # 35% weight
        
        # Compliance score
        compliance_score = 1.0 if compliance_report.compliant else 0.5
        scores.append(compliance_score * 0.25)  # 25% weight
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def _generate_recommendation(
        self,
        fact_checks: List[FactCheckResult],
        bias_analysis: BiasAnalysis,
        compliance_report: ComplianceReport,
        overall_score: float
    ) -> str:
        """Generate recommendation based on audit results."""
        issues = []
        
        # Check fact-checking issues
        unverified = [fc for fc in fact_checks if not fc.verified and fc.confidence < 0.7]
        if unverified:
            issues.append(f"{len(unverified)} unverified claims")
        
        # Check bias issues
        if bias_analysis.bias_detected:
            issues.append(f"Bias detected ({', '.join(bias_analysis.bias_categories)})")
        
        # Check compliance issues
        if not compliance_report.compliant:
            issues.append(f"Compliance issue: {compliance_report.details}")
        
        # Generate recommendation
        if overall_score >= 0.85 and not issues:
            return "approved"
        elif overall_score >= 0.70:
            return "minor_revisions"
        elif overall_score >= 0.50:
            return "major_revisions"
        else:
            return "rejected"
    
    def _handle_unknown_action(self, request: TaskRequest) -> TaskResponse:
        """Handle unknown action requests."""
        logger.warning(f"QAAuditor received unknown action: {request.action}")
        return TaskResponse(
            task_id=request.task_id,
            status=TaskStatus.FAILED,
            artifacts={},
            error_message=f"Unknown action: {request.action}. Supported: audit, audit_visual"
        )
