"""
Test script for Priority 1 RAG improvements
Tests: Reranking, Query Expansion, Adaptive Prefetch
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="/Users/vinayak/Downloads/venwiz/auto-client-pqr/personal_assistant/.env")

# Add client_pqr_agent to path
sys.path.insert(0, str(Path(__file__).parent / "client_pqr_agent"))

from tools.query_vector_db import create_hybrid_searcher

def test_adaptive_prefetch():
    """Test that short queries get higher prefetch multiplier"""
    print("\n" + "="*80)
    print("TEST 1: Adaptive Prefetch Multiplier")
    print("="*80)
    
    searcher = create_hybrid_searcher()
    
    test_cases = [
        ("turnover", 4, "Short query"),
        ("minimum turnover requirement", 3, "Medium query"),
        ("What is the minimum annual turnover requirement for vendors?", 2, "Long query")
    ]
    
    for query, expected_mult, description in test_cases:
        actual_mult = searcher._estimate_query_complexity(query)
        status = "✅" if actual_mult == expected_mult else "❌"
        print(f"{status} {description}: '{query}'")
        print(f"   Expected multiplier: {expected_mult}, Got: {actual_mult}")
    
    print("\n✅ Adaptive prefetch test complete!\n")

def test_query_expansion():
    """Test domain synonym expansion"""
    print("\n" + "="*80)
    print("TEST 2: Query Expansion with Domain Synonyms")
    print("="*80)
    
    searcher = create_hybrid_searcher()
    
    test_cases = [
        "minimum turnover requirement",
        "vendor eligibility criteria",
        "technical certification needed"
    ]
    
    for query in test_cases:
        expansions = searcher._expand_query(query)
        print(f"\n🔍 Original: '{query}'")
        print(f"   Expansions ({len(expansions)} total):")
        for i, exp in enumerate(expansions, 1):
            print(f"   {i}. {exp}")
    
    print("\n✅ Query expansion test complete!\n")

def test_reranking():
    """Test reranking with a sample query"""
    print("\n" + "="*80)
    print("TEST 3: Voyage Rerank 2.0 Integration")
    print("="*80)
    
    searcher = create_hybrid_searcher()
    query = "What is the minimum annual turnover requirement?"
    
    print(f"\n🔍 Query: '{query}'\n")
    
    # Test basic hybrid search
    print("📊 Standard Hybrid Search (RRF):")
    try:
        basic_results = searcher.search(query, limit=3)
        for i, res in enumerate(basic_results, 1):
            print(f"  {i}. Score: {res['score']:.4f} | {res['text'][:80]}...")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "-"*80)
    
    # Test with reranking
    print("🎯 Enhanced Search with Reranking:")
    try:
        reranked_results = searcher.search_with_reranking(query, limit=3, prefetch_limit=15)
        for i, res in enumerate(reranked_results, 1):
            rerank_score = res.get('rerank_score', 'N/A')
            print(f"  {i}. Rerank Score: {rerank_score:.4f} | {res['text'][:80]}...")
        print("\n✅ Reranking working!")
    except Exception as e:
        print(f"  ⚠️  Reranking failed (expected if no data): {e}")
    
    print("\n✅ Reranking test complete!\n")

def test_full_pipeline():
    """Test the updated query_vector_db function"""
    print("\n" + "="*80)
    print("TEST 4: Full Pipeline (query_vector_db with all improvements)")
    print("="*80)
    
    from tools.query_vector_db import query_vector_db
    
    query = "minimum turnover requirement"
    print(f"\n🔍 Testing query_vector_db: '{query}'\n")
    
    try:
        result = query_vector_db(query, limit=3)
        print(result)
        print("\n✅ Full pipeline test complete!")
    except Exception as e:
        print(f"⚠️  Error (expected if database empty): {e}")

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 RAG IMPROVEMENTS TEST SUITE")
    print("="*80)
    
    try:
        # Test 1: Adaptive Prefetch
        test_adaptive_prefetch()
        
        # Test 2: Query Expansion
        test_query_expansion()
        
        # Test 3: Reranking (may fail if DB empty)
        test_reranking()
        
        # Test 4: Full Pipeline
        test_full_pipeline()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        import traceback
        traceback.print_exc()
