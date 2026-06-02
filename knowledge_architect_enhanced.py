"""
knowledge_architect.py - The Researcher Agent (PHASE 1 ENHANCED)
Performs web research, document analysis, and creates structured knowledge maps.
Phase 1 Enhancement: Multi-source retrieval with credibility scoring.
"""

import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from database import DBManager
from schemas import TaskRequest, TaskResponse, TaskStatus
from utils.resilience import retry_with_backoff
from tool_registry import registry as tool_registry
from source_api_gateway import SourceAPIClient, SourceType, APICredentials
from source_adapters import (
    WebSearchAdapter,
    AcademicDatabaseAdapter,
    InternalKnowledgeBaseAdapter,
    NewsAggregatorAdapter,
    SourceResult
)
from query_decomposer import QueryDecomposer, DecomposedQuery
from utils.logger import logger


class ResearchEngine:
    """Manages multi-source web search and document retrieval with Phase 1 enhancements."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.search_url = "https://api.tavily.com/search"
        
        # Initialize Phase 1 components
        self.source_gateway = SourceAPIClient()
        self._initialize_source_adapters()
        self.query_decomposer = QueryDecomposer()
        self.source_results_cache: Dict[str, List[SourceResult]] = {}
        logger.info("ResearchEngine initialized with Phase 1 components")
    
    def _initialize_source_adapters(self):
        """Initializes all source adapters."""
        try:
            # Register web search source
            web_credentials = APICredentials(
                api_key=self.api_key or "demo_key",
                base_url="https://api.tavily.com",
                timeout=30,
                rate_limit_requests=100,
                rate_limit_window=60
            )
            self.source_gateway.register_source(SourceType.WEB_SEARCH, web_credentials)
            logger.info("Web search source registered")
        except Exception as e:
            logger.warning(f"Could not register web search source: {e}")
        
        # Initialize all adapters
        self.web_search_adapter = WebSearchAdapter(self.source_gateway)
        self.academic_adapter = AcademicDatabaseAdapter(self.source_gateway)
        self.internal_adapter = InternalKnowledgeBaseAdapter(self.source_gateway)
        self.news_adapter = NewsAggregatorAdapter(self.source_gateway)
        
        logger.info("All source adapters initialized")

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
    
    def perform_multi_source_search(self, query: str, max_results_per_source: int = 3) -> Dict[str, SourceResult]:
        """
        Phase 1: Performs searches across multiple sources for comprehensive coverage.
        Returns results grouped by source type with credibility metadata.
        """
        logger.info(f"Starting multi-source search for: {query}")
        
        # 1. Decompose query
        decomposed = self.query_decomposer.decompose_query(query)
        self.query_decomposer.print_decomposition(decomposed)
        
        # 2. Execute searches on appropriate sources
        all_results = {}
        
        # Execute each sub-query against its target sources
        for sub_query in decomposed.sub_queries:
            logger.info(f"Executing sub-query [{sub_query.query_type.value}]: {sub_query.sub_query_text}")
            
            for source_name in sub_query.target_sources:
                source_key = f"{source_name}_{sub_query.query_id}"
                
                try:
                    if source_name == "web_search":
                        result = self.web_search_adapter.search(sub_query.sub_query_text, max_results_per_source)
                    elif source_name == "academic":
                        result = self.academic_adapter.search(sub_query.sub_query_text, max_results_per_source)
                    elif source_name == "internal":
                        result = self.internal_adapter.search(sub_query.sub_query_text, max_results_per_source)
                    elif source_name == "news":
                        result = self.news_adapter.search(sub_query.sub_query_text, max_results_per_source)
                    else:
                        logger.warning(f"Unknown source: {source_name}")
                        continue
                    
                    all_results[source_key] = result
                    logger.info(f"✓ {source_name}: {result.total_count} results in {result.execution_time:.2f}s")
                
                except Exception as e:
                    logger.error(f"Search failed for {source_name}: {e}")
        
        return all_results
    
    def consolidate_results(self, multi_source_results: Dict[str, SourceResult]) -> Dict[str, Any]:
        """
        Phase 1: Consolidates results from multiple sources with credibility scoring.
        """
        consolidated = {
            "by_source": {},
            "by_authority": [],
            "consensus_facts": [],
            "conflicting_claims": [],
            "metadata": {
                "total_sources": len(multi_source_results),
                "total_results": sum(r.total_count for r in multi_source_results.values())
            }
        }
        
        # Group by source type
        for key, source_result in multi_source_results.items():
            source_type = source_result.source_type.value
            if source_type not in consolidated["by_source"]:
                consolidated["by_source"][source_type] = []
            
            consolidated["by_source"][source_type].extend(source_result.results)
        
        # Sort by authority score
        all_results = []
        for source_type, results in consolidated["by_source"].items():
            for result in results:
                all_results.append(result)
        
        all_results.sort(key=lambda x: x.get("authority_score", 0.5), reverse=True)
        consolidated["by_authority"] = all_results
        
        logger.info(f"Consolidated {len(all_results)} results from {len(multi_source_results)} source queries")
        
        return consolidated


class KnowledgeArchitect:
    """The Researcher Agent - Phase 1 Enhanced with Multi-Source Retrieval."""

    def __init__(self, db_manager: DBManager, search_api_key: str = None, llm_client=None):
        self.db = db_manager
        self.engine = ResearchEngine(search_api_key)
        self.llm = llm_client
        logger.info("Knowledge Architect initialized with Phase 1 enhancements")

    def execute(self, request: TaskRequest) -> TaskResponse:
        """
        Processes a research request and returns a structured Knowledge Map.
        Phase 1: Now supports multi-source retrieval with credibility scoring.
        """
        query = request.payload.get("instruction") or request.payload.get("user_input")
        use_multi_source = request.payload.get("use_multi_source", True)  # Phase 1 default: enabled
        
        print(f"📚 Knowledge Architect: Processing request '{query}'...")
        logger.info(f"Multi-source mode: {use_multi_source}")

        try:
            # 1. Dynamic Tool Planning
            tool_call = self._plan_tool_use(query)
            
            if tool_call:
                tool_name, args = tool_call
                logger.info(f"Tool Use Detected: {tool_name} with args {args}")
                tool_result, success = tool_registry.execute_tool(tool_name, args)
                
                if success:
                    query = f"Original Request: {query}\n\nTool Result from {tool_name}: {tool_result}"
                else:
                    logger.warning(f"Tool execution failed: {tool_result}")

            # 2. Perform Research - Phase 1: Multi-Source or Legacy
            if use_multi_source:
                logger.info("Phase 1: Executing multi-source research")
                multi_source_results = self.engine.perform_multi_source_search(query)
                consolidated_data = self.engine.consolidate_results(multi_source_results)
                
                # Prepare facts from all sources with credibility metadata
                facts = self._format_consolidated_facts(consolidated_data)
                sources_metadata = self._extract_sources_metadata(multi_source_results)
            else:
                # Fallback to legacy single-source pipeline
                logger.info("Legacy: Using single-source research")
                raw_results = self.engine.perform_search(query)
                facts = self.engine.extract_key_facts(raw_results)
                sources_metadata = {"sources_count": len(raw_results)}

            # 3. Generate the Knowledge Map
            knowledge_map = self._generate_map(query, facts)

            # 4. Construct the formal TaskResponse with Phase 1 metadata
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.COMPLETED,
                artifacts={
                    "primary_output": knowledge_map,
                    "supporting_data": facts,
                    "diagram_type": "mermaid_mindmap",
                    "sources_breakdown": sources_metadata,
                    "phase": "phase_1_multi_source" if use_multi_source else "legacy"
                },
                meta={
                    "confidence": 0.85,
                    "multi_source_enabled": use_multi_source,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Research execution failed: {e}")
            return TaskResponse(
                task_id=request.task_id,
                status=TaskStatus.FAILED,
                artifacts={"error": str(e)},
                meta={"confidence": 0.0},
                error_message=f"Research failed: {str(e)}"
            )
    
    def _format_consolidated_facts(self, consolidated_data: Dict[str, Any]) -> str:
        """
        Formats consolidated results from multiple sources with credibility indicators.
        """
        facts = []
        
        # Add header showing sources
        source_types = list(consolidated_data["by_source"].keys())
        facts.append(f"[MULTI-SOURCE RESEARCH]\nSources: {', '.join(source_types)}\n")
        
        # Add results sorted by authority
        for i, result in enumerate(consolidated_data["by_authority"][:10], 1):  # Top 10 results
            authority = result.get("authority_score", 0.5)
            authority_indicator = "🟢" if authority >= 0.8 else "🟡" if authority >= 0.6 else "🟠"
            
            source_type = result.get("source_type", "unknown")
            title = result.get("title", "N/A")
            content = result.get("content", result.get("abstract", "N/A"))
            
            fact = f"[Source {i}] {authority_indicator} {source_type.upper()}\nTitle: {title}\nContent: {content[:200]}...\n"
            facts.append(fact)
        
        return "\n---\n".join(facts)
    
    def _extract_sources_metadata(self, multi_source_results: Dict[str, SourceResult]) -> Dict[str, Any]:
        """
        Extracts metadata about the sources used.
        """
        metadata = {}
        
        for key, result in multi_source_results.items():
            source_name = result.source_type.value
            if source_name not in metadata:
                metadata[source_name] = {
                    "results_count": 0,
                    "total_execution_time": 0.0,
                    "authority_score": result.metadata.get("authority_score", 0.5)
                }
            
            metadata[source_name]["results_count"] += result.total_count
            metadata[source_name]["total_execution_time"] += result.execution_time
        
        return metadata

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
