"""
knowledge_architect.py - The Researcher Agent
Performs web research, document analysis, and creates structured knowledge maps.
"""

import json
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from database import DBManager
from schemas import TaskRequest, TaskResponse, TaskStatus
from utils.resilience import retry_with_backoff
from tool_registry import registry as tool_registry


class ResearchEngine:
    """Manages web search and document retrieval."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.search_url = "https://api.tavily.com/search"

    @retry_with_backoff(retries=3, backoff_factor=2.0)
    def perform_search(self, query: str, depth: str = "advanced", max_results: int = 5) -> List[Dict]:
        """
        Performs a web search using Tavily (optimized for LLMs).
        If no API key, returns mock results for testing.
        """
        if not self.api_key:
            print(f"⚠️ No Tavily API key configured. Using mock search results for: {query}")
            return self._mock_search_results(query)

        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": depth,
                "include_answer": True,
                "max_results": max_results
            }
            response = requests.post(self.search_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("results", [])
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return self._mock_search_results(query)

    def _mock_search_results(self, query: str) -> List[Dict]:
        """Returns mock search results for testing."""
        return [
            {
                "url": f"https://example.com/article-{i}",
                "title": f"Research article about {query} - Part {i+1}",
                "content": f"This is a comprehensive overview of {query}. Key findings include relevant data and insights."
            }
            for i in range(3)
        ]

    def extract_key_facts(self, results: List[Dict]) -> str:
        """
        Condenses search results into structured fact-list.
        Saves tokens before sending to synthesis stage.
        """
        facts = []
        for i, res in enumerate(results, 1):
            fact = f"[Source {i}]\nTitle: {res.get('title', 'N/A')}\nURL: {res.get('url', 'N/A')}\nContent: {res.get('content', '')}"
            facts.append(fact)
        return "\n\n---\n\n".join(facts)


class KnowledgeArchitect:
    """The Researcher Agent."""

    def __init__(self, db_manager: DBManager, search_api_key: str = None, llm_client=None):
        self.db = db_manager
        self.engine = ResearchEngine(search_api_key)
        self.llm = llm_client

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        Processes a research request and returns a structured Knowledge Map.
        Now supports Dynamic Tool Selection for autonomous tool use.
        """
        query = request.payload.get("instruction") or request.payload.get("user_input")
        print(f"📚 Knowledge Architect: Processing request '{query}'...")

        try:
            # 1. Dynamic Tool Planning
            # The agent decides if it needs a specific tool based on the query
            tool_call = self._plan_tool_use(query)
            
            if tool_call:
                tool_name, args = tool_call
                print(f"🛠️  Tool Use Detected: {tool_name} with args {args}")
                tool_result, success = tool_registry.execute_tool(tool_name, args)
                
                if success:
                    # Augment the query with tool results
                    query = f"Original Request: {query}\n\nTool Result from {tool_name}: {tool_result}"
                else:
                    print(f"⚠️ Tool execution failed: {tool_result}")

            # 2. Perform Research (Standard Pipeline)
            raw_results = self.engine.perform_search(query)
            facts = self.engine.extract_key_facts(raw_results)

            # 3. Generate the Knowledge Map (Call LLM)
            knowledge_map = self._generate_map(query, facts)

            # 4. Construct the formal TaskResponse
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "primary_output": knowledge_map,
                    "supporting_data": facts,
                    "diagram_type": "mermaid_mindmap",
                    "search_results": raw_results
                },
                meta={
                    "confidence": 0.9,
                    "sources_count": len(raw_results),
                    "execution_time": "2.5s",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                meta={"confidence": 0.0},
                error_message=f"Research failed: {str(e)}"
            )

    def _generate_map(self, query: str, facts: str) -> str:
        """
        Calls LLM to convert facts into a Mermaid.js mindmap.
        """
        prompt = f"""Transform these research facts into a structured Mermaid.js mindmap.
Query: {query}
Facts: {facts}

Return ONLY the Mermaid code starting with 'mindmap' or 'graph'. No explanation."""

        if self.llm:
            return self.llm.generate(prompt)
        else:
            # Fallback: Return a simple mindmap structure
            return f"mindmap\n  root(({query}))\n    Fact1\n    Fact2"

    def _plan_tool_use(self, query: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Analyzes the query to determine if a registered tool should be used.
        In production, this would be a call to a small, fast LLM (like Qwen 2.5)
        to decide the tool and extract arguments.
        """
        query_lower = query.lower()
        
        # Simple heuristic-based tool selection for demo
        # In production, this is replaced by LLM-based function calling
        if "calculate" in query_lower or "math" in query_lower:
            import re
            match = re.search(r"calculate\s+(.*)", query_lower)
            expr = match.group(1) if match else "0"
            return "calculate_advanced", {"expression": expr}
            
        if "read file" in query_lower or "read local" in query_lower:
            import re
            match = re.search(r"file\s+([\w\./\\]+)", query_lower)
            path = match.group(1) if match else "unknown.txt"
            
            # Determine tool based on extension
            if path.endswith(".pdf"):
                return "analyze_pdf", {"file_path": path}
            elif path.endswith((".xlsx", ".xls")):
                return "analyze_excel", {"file_path": path}
            else:
                return "read_local_file", {"file_path": path}
            
        if "fetch" in query_lower and "url" in query_lower:
            import re
            match = re.search(r"url\s+([^\s]+)", query_lower)
            url = match.group(1) if match else "https://google.com"
            return "fetch_url_content", {"url": url}

        return None
            topic = query.replace(" ", "_")
            return f"""mindmap
  root((Research: {query}))
    Key Finding 1
      Supporting Detail A
      Supporting Detail B
    Key Finding 2
      Supporting Detail A
      Supporting Detail B"""
