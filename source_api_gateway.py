"""
source_api_gateway.py - Source API Gateway
Centralized management for authentication, rate limiting, and request formatting
across multiple knowledge source APIs.
"""

import requests
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import json
from utils.logger import logger
from utils.resilience import retry_with_backoff


class SourceType(Enum):
    """Enumeration of supported knowledge sources."""
    WEB_SEARCH = "web_search"
    ACADEMIC = "academic"
    INTERNAL = "internal"
    NEWS = "news"
    CUSTOM = "custom"


@dataclass
class APICredentials:
    """Stores API credentials for a source."""
    api_key: str
    base_url: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class RateLimitTracker:
    """Tracks API rate limiting."""
    requests_made: int = 0
    window_start: datetime = field(default_factory=datetime.now)
    
    def should_wait(self, rate_limit_requests: int, rate_limit_window: int) -> Tuple[bool, float]:
        """
        Determines if we should wait before making the next request.
        Returns (should_wait, wait_seconds)
        """
        elapsed = (datetime.now() - self.window_start).total_seconds()
        
        # Reset window if it has expired
        if elapsed > rate_limit_window:
            self.requests_made = 0
            self.window_start = datetime.now()
            return False, 0.0
        
        # Check if we've hit the limit
        if self.requests_made >= rate_limit_requests:
            wait_seconds = rate_limit_window - elapsed
            return True, max(0.1, wait_seconds)
        
        return False, 0.0
    
    def record_request(self):
        """Records that a request was made."""
        self.requests_made += 1


class SourceAPIClient:
    """
    Central gateway for managing multiple source APIs.
    Handles authentication, rate limiting, and standardized request formatting.
    """
    
    def __init__(self):
        self.sources: Dict[SourceType, APICredentials] = {}
        self.rate_limiters: Dict[SourceType, RateLimitTracker] = {}
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = 3600  # 1 hour
        logger.info("SourceAPIClient initialized")
    
    def register_source(self, source_type: SourceType, credentials: APICredentials):
        """
        Registers a new source with its credentials.
        """
        self.sources[source_type] = credentials
        self.rate_limiters[source_type] = RateLimitTracker()
        logger.info(f"Registered source: {source_type.value}")
    
    def _check_rate_limit(self, source_type: SourceType) -> bool:
        """
        Checks and enforces rate limiting.
        Returns True if request can proceed, False if we need to wait.
        """
        if source_type not in self.rate_limiters:
            return True
        
        credentials = self.sources.get(source_type)
        if not credentials:
            return True
        
        tracker = self.rate_limiters[source_type]
        should_wait, wait_seconds = tracker.should_wait(
            credentials.rate_limit_requests,
            credentials.rate_limit_window
        )
        
        if should_wait:
            logger.warning(f"Rate limit reached for {source_type.value}. Waiting {wait_seconds:.1f}s")
            time.sleep(wait_seconds)
            tracker.window_start = datetime.now()
            tracker.requests_made = 0
        
        tracker.record_request()
        return True
    
    def _get_cache_key(self, source_type: SourceType, endpoint: str, params: Dict) -> str:
        """Generates a cache key for a request."""
        param_str = json.dumps(params, sort_keys=True)
        return f"{source_type.value}:{endpoint}:{param_str}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieves data from cache if available and not expired."""
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                logger.info(f"Cache hit: {cache_key}")
                return data
            else:
                del self.cache[cache_key]
        return None
    
    def _store_in_cache(self, cache_key: str, data: Any):
        """Stores data in cache."""
        self.cache[cache_key] = (data, datetime.now())
    
    @retry_with_backoff(retries=3, backoff_factor=2.0)
    def request(
        self,
        source_type: SourceType,
        endpoint: str,
        params: Dict[str, Any],
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Makes a standardized request to a source API.
        Handles authentication, rate limiting, and caching.
        """
        if source_type not in self.sources:
            raise ValueError(f"Source {source_type.value} not registered")
        
        # Check cache
        cache_key = self._get_cache_key(source_type, endpoint, params)
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Check rate limit
        self._check_rate_limit(source_type)
        
        credentials = self.sources[source_type]
        url = f"{credentials.base_url}{endpoint}"
        
        headers = credentials.headers.copy()
        headers["Authorization"] = f"Bearer {credentials.api_key}"
        
        try:
            logger.info(f"Requesting {source_type.value}: {endpoint}")
            
            if method == "GET":
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=credentials.timeout
                )
            elif method == "POST":
                response = requests.post(
                    url,
                    json=params,
                    headers=headers,
                    timeout=credentials.timeout
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            # Store in cache
            self._store_in_cache(cache_key, result)
            
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {source_type.value}: {e}")
            raise
    
    def batch_request(
        self,
        requests_list: List[Tuple[SourceType, str, Dict[str, Any], str]]
    ) -> Dict[str, Any]:
        """
        Makes multiple requests and aggregates results.
        Useful for query decomposition with multiple sub-queries.
        """
        results = {}
        
        for i, (source_type, endpoint, params, method) in enumerate(requests_list):
            try:
                results[f"request_{i}"] = self.request(source_type, endpoint, params, method)
            except Exception as e:
                logger.error(f"Batch request {i} failed: {e}")
                results[f"request_{i}"] = {"error": str(e)}
        
        return results
    
    def get_source_metadata(self, source_type: SourceType) -> Dict[str, Any]:
        """Returns metadata about a source."""
        if source_type not in self.sources:
            return {}
        
        credentials = self.sources[source_type]
        tracker = self.rate_limiters[source_type]
        
        return {
            "type": source_type.value,
            "base_url": credentials.base_url,
            "rate_limit": f"{credentials.rate_limit_requests}/{credentials.rate_limit_window}s",
            "timeout": credentials.timeout,
            "requests_in_current_window": tracker.requests_made,
            "cache_size": len(self.cache)
        }
    
    def clear_cache(self):
        """Clears the entire cache."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Returns statistics about the cache."""
        return {
            "total_cached_items": len(self.cache),
            "cache_ttl": self.cache_ttl,
            "estimated_size_mb": len(json.dumps(self.cache)) / 1024 / 1024
        }
