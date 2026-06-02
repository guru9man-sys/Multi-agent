"""
query_decomposer.py - Query Decomposition Engine
Breaks down complex queries into specialized sub-queries
for optimal targeting of different knowledge sources.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import re
from utils.logger import logger
from utils.llm_clients import LocalLLMClientFactory
from config import config


class QueryType(Enum):
    """Types of queries that require different source strategies."""
    DEFINITION = "definition"           # "What is X?"
    MECHANISM = "mechanism"             # "How does X work?"
    CURRENT_STATUS = "current_status"   # "What's happening with X now?"
    TECHNICAL = "technical"             # "Details about X technology"
    BUSINESS_POLICY = "business_policy" # "Company policy on X"
    OPINION = "opinion"                 # "What do people think about X?"
    COMPARISON = "comparison"           # "X vs Y comparison"
    HISTORICAL = "historical"           # "History of X"


@dataclass
class SubQuery:
    """Represents a decomposed sub-query for a specific source."""
    query_id: str
    original_query: str
    sub_query_text: str
    query_type: QueryType
    target_sources: List[str]  # e.g., ["academic", "web_search"]
    priority: int              # 1=highest, 3=lowest
    description: str           # Human-readable explanation
    dependency_on: List[str] = None  # Which sub-queries this depends on
    
    def __post_init__(self):
        if self.dependency_on is None:
            self.dependency_on = []


@dataclass
class DecomposedQuery:
    """Result of query decomposition."""
    decomposition_id: str
    original_query: str
    query_types: List[QueryType]
    sub_queries: List[SubQuery]
    execution_order: List[str]  # Order to execute sub-queries
    estimated_sources: List[str]
    complexity_score: float  # 0.0-1.0, higher = more complex
    timestamp: str


class QueryDecomposer:
    """
    Analyzes complex queries and breaks them into targeted sub-queries
    optimized for specific knowledge sources.
    """
    
    def __init__(self):
        self.llm_client = None
        self._init_llm_client()
        logger.info("QueryDecomposer initialized")
    
    def _init_llm_client(self):
        """Initializes the LLM client for query understanding."""
        try:
            self.llm_client = LocalLLMClientFactory.create_from_config(config)
            if self.llm_client and self.llm_client.is_available():
                logger.info("LLM client ready for query decomposition")
        except Exception as e:
            logger.warning(f"Could not initialize LLM for decomposition: {e}")
    
    def decompose_query(self, query: str) -> DecomposedQuery:
        """
        Analyzes a query and decomposes it into specialized sub-queries.
        """
        import uuid
        decomposition_id = str(uuid.uuid4())
        
        logger.info(f"Decomposing query: {query}")
        
        # 1. Determine query types
        query_types = self._determine_query_types(query)
        
        # 2. Generate sub-queries based on types
        sub_queries = self._generate_sub_queries(query, query_types)
        
        # 3. Determine execution order (handle dependencies)
        execution_order = self._determine_execution_order(sub_queries)
        
        # 4. Estimate sources
        estimated_sources = self._estimate_sources(query_types)
        
        # 5. Calculate complexity
        complexity_score = self._calculate_complexity(sub_queries)
        
        result = DecomposedQuery(
            decomposition_id=decomposition_id,
            original_query=query,
            query_types=query_types,
            sub_queries=sub_queries,
            execution_order=execution_order,
            estimated_sources=estimated_sources,
            complexity_score=complexity_score,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Query decomposed into {len(sub_queries)} sub-queries with complexity {complexity_score:.2f}")
        return result
    
    def _determine_query_types(self, query: str) -> List[QueryType]:
        """Analyzes the query to determine its types."""
        types = []
        query_lower = query.lower()
        
        # Pattern matching for query types
        if any(x in query_lower for x in ["what is", "define", "meaning", "definition"]):
            types.append(QueryType.DEFINITION)
        
        if any(x in query_lower for x in ["how does", "how do", "how work", "mechanism", "process"]):
            types.append(QueryType.MECHANISM)
        
        if any(x in query_lower for x in ["now", "today", "current", "latest", "recent", "2024", "2025", "2026"]):
            types.append(QueryType.CURRENT_STATUS)
        
        if any(x in query_lower for x in ["policy", "guideline", "standard", "company", "organization"]):
            types.append(QueryType.BUSINESS_POLICY)
        
        if any(x in query_lower for x in ["vs", "versus", "compare", "comparison", "difference"]):
            types.append(QueryType.COMPARISON)
        
        if any(x in query_lower for x in ["history", "historical", "past", "evolution", "development"]):
            types.append(QueryType.HISTORICAL)
        
        if any(x in query_lower for x in ["technical", "technical details", "specification", "implementation"]):
            types.append(QueryType.TECHNICAL)
        
        if any(x in query_lower for x in ["opinion", "think", "believe", "argue"]):
            types.append(QueryType.OPINION)
        
        # Default to definition + mechanism if no specific type detected
        if not types:
            types = [QueryType.DEFINITION, QueryType.MECHANISM]
        
        return types
    
    def _generate_sub_queries(self, query: str, query_types: List[QueryType]) -> List[SubQuery]:
        """Generates specialized sub-queries for each identified type."""
        import uuid
        sub_queries = []
        priority_map = {QueryType.DEFINITION: 1, QueryType.MECHANISM: 1}
        
        for i, qtype in enumerate(query_types):
            sub_query_id = str(uuid.uuid4())[:8]
            priority = priority_map.get(qtype, 2)
            
            # Customize the sub-query based on type
            if qtype == QueryType.DEFINITION:
                sub_query_text = f"What is {query}? Provide a clear definition and key characteristics."
                target_sources = ["academic", "web_search"]
                description = "Understanding the fundamental definition and concept"
            
            elif qtype == QueryType.MECHANISM:
                sub_query_text = f"How does {query} work? Explain the underlying mechanisms and processes."
                target_sources = ["academic", "web_search", "internal"]
                description = "Understanding how the mechanism operates"
            
            elif qtype == QueryType.CURRENT_STATUS:
                sub_query_text = f"What is the current status and latest developments regarding {query}?"
                target_sources = ["news", "web_search"]
                description = "Finding the most recent information and updates"
            
            elif qtype == QueryType.BUSINESS_POLICY:
                sub_query_text = f"What are the organizational policies and guidelines related to {query}?"
                target_sources = ["internal", "web_search"]
                description = "Understanding company policies and standards"
            
            elif qtype == QueryType.COMPARISON:
                sub_query_text = f"Provide a detailed comparison and differences regarding {query}"
                target_sources = ["academic", "web_search"]
                description = "Comparing different aspects or entities"
            
            elif qtype == QueryType.HISTORICAL:
                sub_query_text = f"Provide the historical context and evolution of {query}"
                target_sources = ["academic", "web_search"]
                description = "Understanding historical development and background"
            
            elif qtype == QueryType.TECHNICAL:
                sub_query_text = f"Provide technical details and specifications about {query}"
                target_sources = ["academic", "web_search", "internal"]
                description = "Deep technical understanding and specifications"
            
            else:  # OPINION
                sub_query_text = f"What are the different perspectives and opinions about {query}?"
                target_sources = ["web_search", "news"]
                description = "Understanding various viewpoints and expert opinions"
            
            sub_query = SubQuery(
                query_id=sub_query_id,
                original_query=query,
                sub_query_text=sub_query_text,
                query_type=qtype,
                target_sources=target_sources,
                priority=priority,
                description=description
            )
            sub_queries.append(sub_query)
        
        # Sort by priority (simpler approach)
        sub_queries.sort(key=lambda x: x.priority)
        
        return sub_queries
    
    def _determine_execution_order(self, sub_queries: List[SubQuery]) -> List[str]:
        """
        Determines the optimal order to execute sub-queries.
        Respects dependencies and prioritizes high-priority queries.
        """
        # For now, execute by priority
        # In production, could use a topological sort for dependencies
        sorted_queries = sorted(sub_queries, key=lambda x: (x.priority, -sub_queries.index(x)))
        return [q.query_id for q in sorted_queries]
    
    def _estimate_sources(self, query_types: List[QueryType]) -> List[str]:
        """Estimates which sources are needed."""
        sources_set = set()
        
        for qtype in query_types:
            if qtype == QueryType.DEFINITION:
                sources_set.add("academic")
                sources_set.add("web_search")
            elif qtype == QueryType.MECHANISM:
                sources_set.add("academic")
                sources_set.add("web_search")
            elif qtype == QueryType.CURRENT_STATUS:
                sources_set.add("news")
                sources_set.add("web_search")
            elif qtype == QueryType.BUSINESS_POLICY:
                sources_set.add("internal")
            elif qtype == QueryType.TECHNICAL:
                sources_set.add("academic")
                sources_set.add("web_search")
            else:
                sources_set.add("web_search")
        
        return list(sources_set)
    
    def _calculate_complexity(self, sub_queries: List[SubQuery]) -> float:
        """
        Calculates query complexity based on number of sub-queries
        and types involved.
        """
        # Simple complexity calculation
        # More complex queries have more sub-queries and diverse types
        base_complexity = min(len(sub_queries) / 3.0, 1.0)
        return base_complexity
    
    def print_decomposition(self, decomposed: DecomposedQuery):
        """Prints a human-readable decomposition report."""
        print(f"\n{'='*70}")
        print(f"QUERY DECOMPOSITION REPORT")
        print(f"{'='*70}")
        print(f"Original Query: {decomposed.original_query}")
        print(f"Decomposition ID: {decomposed.decomposition_id}")
        print(f"Complexity Score: {decomposed.complexity_score:.2f}/1.0")
        print(f"Query Types: {', '.join([t.value for t in decomposed.query_types])}")
        print(f"Estimated Sources: {', '.join(decomposed.estimated_sources)}")
        print(f"\nSub-Queries ({len(decomposed.sub_queries)}):")
        print(f"{'-'*70}")
        
        for i, sq in enumerate(decomposed.sub_queries, 1):
            print(f"\n{i}. [{sq.query_type.value.upper()}] Priority {sq.priority}")
            print(f"   Query: {sq.sub_query_text}")
            print(f"   Target Sources: {', '.join(sq.target_sources)}")
            print(f"   {sq.description}")
        
        print(f"\n{'='*70}")
