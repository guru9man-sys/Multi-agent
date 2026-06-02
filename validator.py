"""
validator.py - The Guardrail Layer
Validates and repairs LLM outputs to ensure schema compliance.
"""

import json
import re
from typing import Tuple, Optional
from pydantic import ValidationError
from schemas import TaskResponse, RoutingDecision


class ResponseValidator:
    """
    Validates LLM outputs to ensure they adhere to the expected schemas.
    Prevents invalid data from entering the orchestrator loop.
    """

    @staticmethod
    def clean_llm_json(raw_text: str) -> str:
        """
        Removes Markdown code blocks and leading/trailing whitespace
        which Local LLMs often include.
        """
        text = raw_text.strip()

        # Remove Markdown code fence
        if text.startswith("```"):
            # Remove starting fence (e.g., ```json)
            text = text.split("\n", 1)[-1] if "\n" in text else text
            # Remove ending fence (```)
            if "```" in text:
                text = text.rsplit("```", 1)[0]

        return text.strip()

    @staticmethod
    def extract_json_from_text(text: str) -> Optional[str]:
        """
        Attempts to find a JSON object in freeform text.
        """
        # Try to find a JSON object pattern
        pattern = r'\{[^{}]*\}'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[-1]  # Return the last (most complete) match
        return None

    def validate_routing_decision(self, raw_output: str) -> Tuple[bool, Optional[RoutingDecision], Optional[str]]:
        """
        Validates a routing decision from the Local Router.
        Returns: (Is_Valid, Parsed_Object, Error_Message)
        """
        cleaned_text = self.clean_llm_json(raw_output)

        try:
            # Step 1: Basic JSON parsing
            data = json.loads(cleaned_text)

            # Step 2: Pydantic validation
            decision_obj = RoutingDecision(**data)
            return True, decision_obj, None

        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON format: {str(e)}"
        except ValidationError as e:
            return False, None, f"Schema mismatch: {e.json()}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"

    def validate_task_response(self, raw_output: str) -> Tuple[bool, Optional[TaskResponse], Optional[str]]:
        """
        Validates a task response from a specialist agent.
        """
        cleaned_text = self.clean_llm_json(raw_output)

        try:
            data = json.loads(cleaned_text)
            response_obj = TaskResponse(**data)
            return True, response_obj, None

        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON format: {str(e)}"
        except ValidationError as e:
            return False, None, f"Schema mismatch: {e.json()}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"

    def validate_generic_json(self, raw_output: str, expected_keys: list = None) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Generic JSON validator for flexible outputs.
        """
        cleaned_text = self.clean_llm_json(raw_output)

        try:
            data = json.loads(cleaned_text)

            if expected_keys:
                missing_keys = [k for k in expected_keys if k not in data]
                if missing_keys:
                    return False, None, f"Missing keys: {missing_keys}"

            return True, data, None

        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
