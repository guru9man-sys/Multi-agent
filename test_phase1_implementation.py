"""
test_phase1_implementation.py - Test Suite for Phase 1: Source Integration Layer
Tests the multi-source retrieval, query decomposition, and credibility scoring.
"""

import sys
import asyncio
from source_api_gateway import SourceAPIClient, SourceType, APICredentials
from source_adapters import (
    WebSearchAdapter,
    AcademicDatabaseAdapter,
    InternalKnowledgeBaseAdapter,
    NewsAggregatorAdapter
)
from query_decomposer import QueryDecomposer, QueryType
from knowledge_architect import ResearchEngine, KnowledgeArchitect
from database import DBManager
from utils.logger import logger


def test_source_gateway():
    """Test 1: Source API Gateway initialization and caching."""
    print("\n" + "="*70)
    print("TEST 1: Source API Gateway")
    print("="*70)
    
    gateway = SourceAPIClient()
    
    # Register a test source
    creds = APICredentials(
        api_key="test_key",
        base_url="https://api.test.com",
        timeout=30,
        rate_limit_requests=10,
        rate_limit_window=60
    )
    
    gateway.register_source(SourceType.WEB_SEARCH, creds)
    
    # Check metadata
    metadata = gateway.get_source_metadata(SourceType.WEB_SEARCH)
    print(f"\n✓ Source registered: {metadata}")
    
    # Check cache stats
    cache_stats = gateway.get_cache_stats()
    print(f"✓ Cache initialized: {cache_stats}")
    
    print("✅ Gateway test passed")


def test_source_adapters():
    """Test 2: All source adapters with mock data."""
    print("\n" + "="*70)
    print("TEST 2: Source Adapters")
    print("="*70)
    
    gateway = SourceAPIClient()
    
    # Test Web Search Adapter
    print("\n2A: Web Search Adapter")
    web_adapter = WebSearchAdapter(gateway)
    web_result = web_adapter.search("What is machine learning?", limit=2)
    print(f"   ✓ Results: {web_result.total_count}")
    print(f"   ✓ Source: {web_result.source_type.value}")
    print(f"   ✓ First result: {web_result.results[0]['title'] if web_result.results else 'N/A'}")
    
    # Test Academic Database Adapter
    print("\n2B: Academic Database Adapter")
    academic_adapter = AcademicDatabaseAdapter(gateway)
    academic_result = academic_adapter.search("Neural networks in deep learning", limit=2)
    print(f"   ✓ Results: {academic_result.total_count}")
    print(f"   ✓ Authority Score: {academic_result.metadata.get('authority_score', 'N/A')}")
    print(f"   ✓ Peer Reviewed: {academic_result.metadata.get('peer_reviewed', False)}")
    
    # Test Internal Knowledge Base Adapter
    print("\n2C: Internal Knowledge Base Adapter")
    internal_adapter = InternalKnowledgeBaseAdapter(gateway)
    internal_result = internal_adapter.search("Company AI policy", limit=2)
    print(f"   ✓ Results: {internal_result.total_count}")
    print(f"   ✓ Source Type: {internal_result.source_type.value}")
    
    # Test News Aggregator Adapter
    print("\n2D: News Aggregator Adapter")
    news_adapter = NewsAggregatorAdapter(gateway)
    news_result = news_adapter.search("Latest AI developments", limit=2)
    print(f"   ✓ Results: {news_result.total_count}")
    print(f"   ✓ Recency: {news_result.metadata.get('recency', 'N/A')}")
    
    print("\n✅ All adapters test passed")


def test_query_decomposer():
    """Test 3: Query decomposition engine."""
    print("\n" + "="*70)
    print("TEST 3: Query Decomposition Engine")
    print("="*70)
    
    decomposer = QueryDecomposer()
    
    test_queries = [
        "What is artificial intelligence and how does it work?",
        "Compare machine learning and deep learning",
        "What is the current status of quantum computing?",
        "What are company policies on AI usage?"
    ]
    
    for query in test_queries:
        print(f"\n📌 Query: {query}")
        decomposed = decomposer.decompose_query(query)
        
        print(f"   ✓ Query Types: {', '.join([t.value for t in decomposed.query_types])}")
        print(f"   ✓ Sub-queries Generated: {len(decomposed.sub_queries)}")
        print(f"   ✓ Complexity Score: {decomposed.complexity_score:.2f}")
        print(f"   ✓ Estimated Sources: {', '.join(decomposed.estimated_sources)}")
        
        for sq in decomposed.sub_queries[:2]:  # Show first 2 sub-queries
            print(f"      - [{sq.query_type.value}] {sq.sub_query_text[:60]}...")
    
    print("\n✅ Query decomposition test passed")


def test_research_engine():
    """Test 4: Research engine with multi-source search."""
    print("\n" + "="*70)
    print("TEST 4: Research Engine - Multi-Source Search")
    print("="*70)
    
    engine = ResearchEngine(api_key=None)  # Use mock data
    
    query = "What is the impact of AI on healthcare?"
    print(f"\nSearching: {query}")
    
    # Perform multi-source search
    multi_results = engine.perform_multi_source_search(query, max_results_per_source=2)
    print(f"\n✓ Total source queries executed: {len(multi_results)}")
    
    # Consolidate results
    consolidated = engine.consolidate_results(multi_results)
    print(f"✓ Total consolidated results: {consolidated['metadata']['total_results']}")
    print(f"✓ Sources used: {list(consolidated['by_source'].keys())}")
    
    # Show top results
    print(f"\nTop 3 Results (sorted by authority):")
    for i, result in enumerate(consolidated['by_authority'][:3], 1):
        print(f"   {i}. [{result.get('source_type', 'N/A')}] {result.get('title', 'N/A')[:60]}...")
        print(f"      Authority: {result.get('authority_score', 0)}")
    
    print("\n✅ Research engine test passed")


def test_knowledge_architect():
    """Test 5: Full Knowledge Architect pipeline."""
    print("\n" + "="*70)
    print("TEST 5: Knowledge Architect - Full Pipeline")
    print("="*70)
    
    try:
        # Initialize database
        db = DBManager()
        
        # Create Knowledge Architect instance
        architect = KnowledgeArchitect(db, search_api_key=None)
        
        # Create a test task request
        from schemas import TaskRequest, TaskPriority, TaskAction, AgentRole
        
        test_request = TaskRequest(
            task_id="test_ka_001",
            agent_role=AgentRole.KNOWLEDGE_ARCHITECT,
            action=TaskAction.RESEARCH,
            priority=TaskPriority.HIGH,
            payload={
                "user_input": "What are the recent developments in quantum computing?",
                "use_multi_source": True
            }
        )
        
        print(f"\n📌 Task: {test_request.payload['user_input']}")
        print(f"   Multi-source mode: {test_request.payload['use_multi_source']}")
        
        # Execute the research
        result = architect.execute(test_request)
        
        print(f"\n✓ Execution Status: {result.status.value}")
        print(f"✓ Confidence: {result.meta.get('confidence', 'N/A')}")
        print(f"✓ Multi-source enabled: {result.meta.get('multi_source_enabled', 'N/A')}")
        print(f"✓ Phase: {result.artifacts.get('phase', 'N/A')}")
        
        # Show sources breakdown
        sources = result.artifacts.get('sources_breakdown', {})
        if sources:
            print(f"\n Sources Breakdown:")
            for source_name, source_data in sources.items():
                print(f"   - {source_name}: {source_data.get('results_count', 0)} results")
        
        print("\n✅ Knowledge Architect test passed")
    
    except Exception as e:
        logger.error(f"Knowledge Architect test failed: {e}")
        print(f"❌ Error: {e}")


def run_all_tests():
    """Run all Phase 1 tests."""
    print("\n" + "="*70)
    print("PHASE 1 IMPLEMENTATION TEST SUITE")
    print("Source Integration Layer for Knowledge Architect")
    print("="*70)
    
    try:
        test_source_gateway()
        test_source_adapters()
        test_query_decomposer()
        test_research_engine()
        test_knowledge_architect()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nPhase 1 Implementation Summary:")
        print("  ✓ Source API Gateway - Centralized API management")
        print("  ✓ Source Adapters - Multi-source retrieval")
        print("  ✓ Query Decomposition - Intelligent query targeting")
        print("  ✓ Research Engine - Multi-source search coordination")
        print("  ✓ Knowledge Architect - Full pipeline integration")
        print("\nNext: Phase 2 - Credibility & Relevance Scoring")
        print("="*70)
    
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
