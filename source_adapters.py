"""
source_adapters.py - Source-Specific Adapters
Implements standardized interfaces for different types of knowledge sources.
Each adapter translates queries and formats responses consistently.
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from source_api_gateway import SourceAPIClient, SourceType, APICredentials
from utils.logger import logger
import requests


@dataclass
class SourceResult:
    """Standardized result from any source adapter."""
    source_type: SourceType
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    execution_time: float
    timestamp: str
    metadata: Dict[str, Any]


class SourceAdapter(ABC):
    """Base class for all source adapters."""
    
    def __init__(self, gateway: SourceAPIClient, source_type: SourceType):
        self.gateway = gateway
        self.source_type = source_type
    
    @abstractmethod
    def search(self, query: str, limit: int = 5, **kwargs) -> SourceResult:
        """Executes a search against this source."""
        pass
    
    @abstractmethod
    def parse_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Converts raw API response to standardized format."""
        pass
    
    def _standardize_result(
        self,
        raw_results: List[Dict],
        query: str,
        execution_time: float,
        metadata: Dict[str, Any] = None
    ) -> SourceResult:
        """Helper to create standardized SourceResult."""
        parsed_results = [self.parse_result(r) for r in raw_results]
        
        return SourceResult(
            source_type=self.source_type,
            query=query,
            results=parsed_results,
            total_count=len(parsed_results),
            execution_time=execution_time,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )


class WebSearchAdapter(SourceAdapter):
    """Adapter for general web search (Tavily, Google Custom Search, etc.)"""
    
    def __init__(self, gateway: SourceAPIClient):
        super().__init__(gateway, SourceType.WEB_SEARCH)
    
    def search(self, query: str, limit: int = 5, depth: str = "advanced", **kwargs) -> SourceResult:
        """Searches the web for general information."""
        import time
        start_time = time.time()
        
        try:
            # Fallback to direct Tavily if gateway doesn't have it registered
            if SourceType.WEB_SEARCH not in self.gateway.sources:
                return self._fallback_tavily_search(query, limit, depth)
            
            params = {
                "query": query,
                "search_depth": depth,
                "max_results": limit,
                "include_answer": True
            }
            
            raw_results = self.gateway.request(
                self.source_type,
                "/search",
                params
            )
            
            execution_time = time.time() - start_time
            
            results_list = raw_results.get("results", [])
            
            return self._standardize_result(
                results_list,
                query,
                execution_time,
                metadata={"depth": depth, "authority_score": 0.6}
            )
        
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return self._fallback_tavily_search(query, limit, depth)
    
    def _fallback_tavily_search(self, query: str, limit: int, depth: str) -> SourceResult:
        """Fallback to direct Tavily API call."""
        import time
        start_time = time.time()
        
        try:
            from config import config
            if not config.TAVILY_API_KEY or config.TAVILY_API_KEY == "your_tavily_api_key_here":
                logger.warning("No Tavily API key configured. Using mock results.")
                return self._mock_results(query, limit)
            
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": config.TAVILY_API_KEY,
                    "query": query,
                    "search_depth": depth,
                    "max_results": limit,
                    "include_answer": True
                },
                timeout=30
            )
            response.raise_for_status()
            raw_results = response.json().get("results", [])
            
            execution_time = time.time() - start_time
            
            return self._standardize_result(
                raw_results,
                query,
                execution_time,
                metadata={"depth": depth, "authority_score": 0.6, "source": "tavily"}
            )
        
        except Exception as e:
            logger.error(f"Tavily fallback failed: {e}")
            return self._mock_results(query, limit)
    
    def _mock_results(self, query: str, limit: int) -> SourceResult:
        """Returns mock results for testing."""
        import time
        start_time = time.time()
        
        mock_data = [
            {
                "url": f"https://example.com/article-{i}",
                "title": f"Web article about {query} - Part {i+1}",
                "content": f"Comprehensive information about {query} from web sources.",
                "snippet": f"Key finding: {query} has multiple aspects to consider."
            }
            for i in range(limit)
        ]
        
        execution_time = time.time() - start_time
        return self._standardize_result(
            mock_data,
            query,
            execution_time,
            metadata={"authority_score": 0.6, "is_mock": True}
        )
    
    def parse_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizes web search result format."""
        return {
            "title": raw_result.get("title", "N/A"),
            "url": raw_result.get("url", "N/A"),
            "content": raw_result.get("content", raw_result.get("snippet", "N/A")),
            "authority_score": 0.6,
            "source_type": "web"
        }


class AcademicDatabaseAdapter(SourceAdapter):
    """Adapter for peer-reviewed academic literature (PubMed, arXiv, etc.)"""
    
    def __init__(self, gateway: SourceAPIClient):
        super().__init__(gateway, SourceType.ACADEMIC)
    
    def search(self, query: str, limit: int = 5, field: str = "all", **kwargs) -> SourceResult:
        """Searches academic databases for peer-reviewed research."""
        import time
        start_time = time.time()
        
        try:
            if SourceType.ACADEMIC not in self.gateway.sources:
                logger.info("Academic database not configured. Using mock results.")
                return self._mock_results(query, limit)
            
            params = {
                "query": query,
                "max_results": limit,
                "field": field,
                "sort": "relevance"
            }
            
            raw_results = self.gateway.request(
                self.source_type,
                "/search",
                params
            )
            
            execution_time = time.time() - start_time
            results_list = raw_results.get("results", [])
            
            return self._standardize_result(
                results_list,
                query,
                execution_time,
                metadata={"field": field, "authority_score": 0.95, "peer_reviewed": True}
            )
        
        except Exception as e:
            logger.error(f"Academic search failed: {e}")
            return self._mock_results(query, limit)
    
    def _mock_results(self, query: str, limit: int) -> SourceResult:
        """Returns mock academic results for testing."""
        import time
        start_time = time.time()
        
        mock_data = [
            {
                "title": f"Peer-reviewed study on {query} (2024) - Paper {i+1}",
                "authors": ["Dr. Smith", "Dr. Johnson"],
                "abstract": f"This study investigates {query} through empirical research methods.",
                "journal": "Nature / Science / Medical Journal",
                "doi": f"10.1234/example.{i+1}",
                "year": 2024
            }
            for i in range(limit)
        ]
        
        execution_time = time.time() - start_time
        return self._standardize_result(
            mock_data,
            query,
            execution_time,
            metadata={"authority_score": 0.95, "peer_reviewed": True, "is_mock": True}
        )
    
    def parse_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizes academic database result format."""
        return {
            "title": raw_result.get("title", "N/A"),
            "authors": raw_result.get("authors", []),
            "abstract": raw_result.get("abstract", "N/A"),
            "journal": raw_result.get("journal", "N/A"),
            "doi": raw_result.get("doi", "N/A"),
            "year": raw_result.get("year", "N/A"),
            "authority_score": 0.95,
            "peer_reviewed": True,
            "source_type": "academic"
        }


class InternalKnowledgeBaseAdapter(SourceAdapter):
    """Adapter for internal organizational knowledge bases (Confluence, Vector DB, etc.)"""
    
    def __init__(self, gateway: SourceAPIClient):
        super().__init__(gateway, SourceType.INTERNAL)
    
    def search(self, query: str, limit: int = 5, **kwargs) -> SourceResult:
        """Searches internal knowledge bases."""
        import time
        start_time = time.time()
        
        try:
            if SourceType.INTERNAL not in self.gateway.sources:
                logger.info("Internal knowledge base not configured.")
                return self._mock_results(query, limit)
            
            params = {
                "query": query,
                "max_results": limit,
                "match_threshold": 0.7
            }
            
            raw_results = self.gateway.request(
                self.source_type,
                "/search",
                params
            )
            
            execution_time = time.time() - start_time
            results_list = raw_results.get("results", [])
            
            return self._standardize_result(
                results_list,
                query,
                execution_time,
                metadata={"authority_score": 0.8, "internal": True}
            )
        
        except Exception as e:
            logger.error(f"Internal KB search failed: {e}")
            return self._mock_results(query, limit)
    
    def _mock_results(self, query: str, limit: int) -> SourceResult:
        """Returns mock internal knowledge base results."""
        import time
        start_time = time.time()
        
        mock_data = [
            {
                "title": f"Internal Policy on {query}",
                "content": f"Company guidelines and best practices regarding {query}",
                "author": "Knowledge Management Team",
                "last_updated": "2026-04-15",
                "category": "Policies"
            }
            for i in range(limit)
        ]
        
        execution_time = time.time() - start_time
        return self._standardize_result(
            mock_data,
            query,
            execution_time,
            metadata={"authority_score": 0.8, "internal": True, "is_mock": True}
        )
    
    def parse_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizes internal knowledge base result format."""
        return {
            "title": raw_result.get("title", "N/A"),
            "content": raw_result.get("content", "N/A"),
            "author": raw_result.get("author", "N/A"),
            "last_updated": raw_result.get("last_updated", "N/A"),
            "category": raw_result.get("category", "N/A"),
            "authority_score": 0.8,
            "source_type": "internal"
        }


class NewsAggregatorAdapter(SourceAdapter):
    """Adapter for news aggregators (NewsAPI, etc.) - For current events"""
    
    def __init__(self, gateway: SourceAPIClient):
        super().__init__(gateway, SourceType.NEWS)
    
    def search(self, query: str, limit: int = 5, country: str = "us", **kwargs) -> SourceResult:
        """Searches news aggregators for current event information."""
        import time
        start_time = time.time()
        
        try:
            if SourceType.NEWS not in self.gateway.sources:
                logger.info("News aggregator not configured. Using mock results.")
                return self._mock_results(query, limit)
            
            params = {
                "query": query,
                "max_results": limit,
                "country": country,
                "sort_by": "publishedAt"
            }
            
            raw_results = self.gateway.request(
                self.source_type,
                "/top-headlines",
                params
            )
            
            execution_time = time.time() - start_time
            results_list = raw_results.get("results", [])
            
            return self._standardize_result(
                results_list,
                query,
                execution_time,
                metadata={"country": country, "authority_score": 0.7, "recency": "high"}
            )
        
        except Exception as e:
            logger.error(f"News search failed: {e}")
            return self._mock_results(query, limit)
    
    def _mock_results(self, query: str, limit: int) -> SourceResult:
        """Returns mock news results."""
        import time
        start_time = time.time()
        
        mock_data = [
            {
                "source": "NewsOrg",
                "author": "News Reporter",
                "title": f"Breaking News on {query} - Update {i+1}",
                "description": f"Latest developments regarding {query}",
                "url": f"https://news.example.com/article-{i}",
                "publishedAt": datetime.now().isoformat()
            }
            for i in range(limit)
        ]
        
        execution_time = time.time() - start_time
        return self._standardize_result(
            mock_data,
            query,
            execution_time,
            metadata={"authority_score": 0.7, "recency": "high", "is_mock": True}
        )
    
    def parse_result(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizes news article result format."""
        return {
            "source": raw_result.get("source", "N/A"),
            "author": raw_result.get("author", "N/A"),
            "title": raw_result.get("title", "N/A"),
            "description": raw_result.get("description", raw_result.get("content", "N/A")),
            "url": raw_result.get("url", "N/A"),
            "published_at": raw_result.get("publishedAt", datetime.now().isoformat()),
            "authority_score": 0.7,
            "recency": "high",
            "source_type": "news"
        }
