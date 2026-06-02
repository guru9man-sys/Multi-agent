"""
document_template_engine.py - Phase 7.5: Document Template Engine
Provides a system for generating formal documents based on predefined templates.
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from utils.logger import logger

@dataclass
class Template:
    """Definition of a document template."""
    name: str
    structure: List[Dict[str, Any]]  # List of sections with placeholders
    default_style: Dict[str, Any]
    description: str

class DocumentTemplateEngine:
    """
    Engine to transform structured agent data into formal document formats.
    Supports template-based generation for reports, proposals, and summaries.
    """
    
    def __init__(self):
        self.templates: Dict[str, Template] = {}
        self._load_default_templates()
        logger.info("DocumentTemplateEngine initialized with default templates.")

    def _load_default_templates(self):
        """Loads a set of standard business templates."""
        
        # 1. Executive Summary Template
        self.register_template(Template(
            name="executive_summary",
            description="A high-level summary for executives focusing on outcomes and ROI.",
            structure=[
                {"section": "Overview", "placeholder": "{{summary}}", "style": "bold_header"},
                {"section": "Key Findings", "placeholder": "{{key_findings}}", "style": "bullet_points"},
                {"section": "Strategic Recommendations", "placeholder": "{{recommendations}}", "style": "numbered_list"},
                {"section": "Conclusion", "placeholder": "{{conclusion}}", "style": "standard_text"}
            ],
            default_style={"font": "Arial", "size": "12pt", "alignment": "justified"}
        ))

        # 2. Detailed Research Report Template
        self.register_template(Template(
            name="research_report",
            description="A comprehensive technical report including all supporting data.",
            structure=[
                {"section": "Introduction", "placeholder": "{{intro}}", "style": "standard_text"},
                {"section": "Methodology", "placeholder": "{{methodology}}", "style": "standard_text"},
                {"section": "Detailed Analysis", "placeholder": "{{analysis}}", "style": "detailed_sections"},
                {"section": "Supporting Evidence", "placeholder": "{{supporting_data}}", "style": "table_format"},
                {"section": "Final Verdict", "placeholder": "{{verdict}}", "style": "highlight_box"}
            ],
            default_style={"font": "Times New Roman", "size": "11pt", "alignment": "left"}
        ))

        # 3. Social Media Campaign Plan Template
        self.register_template(Template(
            name="campaign_plan",
            description="A structured plan for multi-platform content distribution.",
            structure=[
                {"section": "Campaign Goal", "placeholder": "{{goal}}", "style": "bold_header"},
                {"section": "Platform Strategy", "placeholder": "{{platform_strategy}}", "style": "grid_layout"},
                {"section": "Content Calendar", "placeholder": "{{calendar}}", "style": "table_format"},
                {"section": "KPIs & Success Metrics", "placeholder": "{{kpis}}", "style": "bullet_points"}
            ],
            default_style={"font": "Verdana", "size": "10pt", "alignment": "left"}
        ))

    def register_template(self, template: Template):
        """Registers a new custom template."""
        self.templates[template.name] = template
        logger.info(f"Template Registered: {template.name}")

    def generate_document(self, template_name: str, data: Dict[str, Any]) -> str:
        """
        Fills a template with provided data and returns the formatted document.
        """
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template {template_name} not found.")

        logger.info(f"Generating document using template: {template_name}")
        
        document_parts = []
        document_parts.append(f"=== {template.name.upper().replace('_', ' ')} ===\n")
        
        for section in template.structure:
            header = section["section"]
            placeholder = section["placeholder"]
            style = section["style"]
            
            # Extract value from data using the placeholder key (removing {{}})
            key = placeholder.replace("{{", "").replace("}}", "")
            value = data.get(key, "N/A")
            
            # Apply basic formatting based on style
            formatted_value = self._apply_style(value, style)
            
            document_parts.append(f"## {header}\n{formatted_value}\n")

        return "\n".join(document_parts)

    def _apply_style(self, value: Any, style: str) -> str:
        """Applies basic text formatting based on the style identifier."""
        if not value:
            return "[No data provided]"
            
        if isinstance(value, list):
            value = "\n".join([f"- {item}" for item in value])

        if style == "bold_header":
            return f"**{value}**"
        elif style == "bullet_points":
            return f"• {value}" if not value.startswith("•") else value
        elif style == "numbered_list":
            return value if "\n1." in str(value) else f"1. {value}"
        elif style == "highlight_box":
            return f"--------------------\n{value}\n--------------------"
        
        return str(value)

    def list_templates(self) -> List[Dict[str, Any]]:
        """Returns a list of all available templates and their descriptions."""
        return [
            {"name": t.name, "description": t.description} 
            for t in self.templates.values()
        ]
