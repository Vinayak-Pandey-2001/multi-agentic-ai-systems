"""
Hybrid RAG Search Module
-------------------------
Provides hybrid search combining dense (semantic) and sparse (BM25) retrieval
for Qdrant vector database.

Usage:
    from hybrid_search import HybridSearcher
    
    searcher = HybridSearcher(client, collection_name)
    results = searcher.search("your query", limit=5)
"""

from qdrant_client import QdrantClient, models
from collections import Counter
import re
import math
from typing import List, Dict, Optional, Tuple
import voyageai
import os

# RFQ Domain-Specific Synonyms for Query Expansion
RFQ_DOMAIN_SYNONYMS = {
    "turnover": ["revenue", "annual sales", "financial performance"],
    "eligibility": ["qualification", "pre-qualification", "bidder requirements"],
    "experience": ["track record", "past performance", "project history"],
    "technical": ["specification", "technical requirement", "design standard"],
    "certification": ["accreditation", "approval", "license"],
    "capacity": ["capability", "output", "production capacity"],
    "compliance": ["conformance", "adherence", "regulatory compliance"],
    "manufacturer": ["supplier", "vendor", "OEM", "producer"],
    "installation": ["erection", "commissioning", "setup"],
    "maintenance": ["upkeep", "servicing", "preventive maintenance"],
}

class HybridSearcher:
    """
    Hybrid search combining dense and sparse vectors
    """
    
    def __init__(
        self, 
        client: QdrantClient, 
        collection_name: str,
        voyage_api_key: Optional[str] = None,
        vocabulary: Optional[Dict[str, int]] = None
    ):
        """
        Initialize hybrid searcher
        
        Args:
            client: Qdrant client instance
            collection_name: Name of the collection to search
            voyage_api_key: Voyage AI API key for dense embeddings
            vocabulary: Pre-built vocabulary (if None, will build from collection)
        """
        self.client = client
        self.collection_name = collection_name
        
        # Initialize Voyage client for dense embeddings
        api_key = voyage_api_key or os.getenv("VOYAGE_API_KEY")
        self.vo = voyageai.Client(api_key=api_key)
        
        # Build or load vocabulary
        if vocabulary is None:
            self.vocabulary, self.idf_scores = self._build_vocabulary_from_collection()
        else:
            self.vocabulary = vocabulary
            self.idf_scores = {}
        
        self.avg_doc_length = 100  # Will be updated when building vocabulary
    
    def _estimate_query_complexity(self, query: str) -> int:
        """
        Estimate query complexity to determine prefetch multiplier
        
        Returns:
            Multiplier for prefetch limit (2-4)
        """
        word_count = len(query.split())
        
        if word_count < 5:
            return 4  # Short/broad query needs more diversity
        elif word_count < 10:
            return 3  # Medium query
        else:
            return 2  # Long/specific query, top results likely good
    
    def _expand_query(self, query: str) -> List[str]:
        """
        Generate query variations using domain synonyms
        
        Returns:
            List of query variations (original + expanded)
        """
        expansions = [query]  # Always include original
        query_lower = query.lower()
        
        for term, synonyms in RFQ_DOMAIN_SYNONYMS.items():
            if term in query_lower:
                # Add top 2 synonym variations
                for synonym in synonyms[:2]:
                    expanded = query_lower.replace(term, synonym)
                    expansions.append(expanded)
        
        return expansions
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25"""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return [t for t in tokens if len(t) > 2]
    
    def _build_vocabulary_from_collection(self) -> Tuple[Dict[str, int], Dict[str, float]]:
        """
        Build vocabulary and IDF scores from existing collection
        """
        print("📚 Building vocabulary from collection...")
        
        all_texts = []
        offset = None
        
        # Fetch all points from collection
        while True:
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            points, offset = result
            
            for point in points:
                text = point.payload.get("text", "")
                if text:
                    all_texts.append(text)
            
            if offset is None:
                break
        
        if not all_texts:
            print("⚠️  Warning: No texts found in collection")
            return {}, {}
        
        # Build vocabulary
        all_tokens = set()
        for text in all_texts:
            tokens = self._tokenize(text)
            all_tokens.update(tokens)
        
        vocab = {token: idx for idx, token in enumerate(sorted(all_tokens))}
        
        # Calculate IDF
        total_docs = len(all_texts)
        term_doc_freq = Counter()
        total_tokens = 0
        
        for text in all_texts:
            tokens = self._tokenize(text)
            total_tokens += len(tokens)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                term_doc_freq[token] += 1
        
        idf_scores = {}
        for term, doc_freq in term_doc_freq.items():
            idf_scores[term] = math.log((total_docs + 1) / (doc_freq + 1)) + 1
        
        self.avg_doc_length = total_tokens / total_docs if total_docs > 0 else 100
        
        print(f"✅ Vocabulary built: {len(vocab)} unique tokens")
        print(f"📊 Average document length: {self.avg_doc_length:.1f} tokens")
        
        return vocab, idf_scores
    
    def _text_to_sparse_bm25(
        self, 
        text: str, 
        k1: float = 1.5, 
        b: float = 0.75
    ) -> models.SparseVector:
        """
        Generate BM25 sparse vector from text
        """
        tokens = self._tokenize(text)
        token_counts = Counter(tokens)
        
        doc_len = len(tokens)
        
        indices = []
        values = []
        
        for token, count in token_counts.items():
            if token in self.vocabulary:
                idx = self.vocabulary[token]
                idf = self.idf_scores.get(token, 1.0)
                
                # BM25 formula
                numerator = count * (k1 + 1)
                denominator = count + k1 * (1 - b + b * (doc_len / self.avg_doc_length))
                bm25_score = idf * (numerator / denominator)
                
                indices.append(idx)
                values.append(float(bm25_score))
        
        return models.SparseVector(indices=indices, values=values)
    
    def _get_dense_embedding(self, text: str) -> List[float]:
        """Generate dense embedding using Voyage AI"""
        response = self.vo.embed(
            texts=[text],
            model="voyage-4-large",
            input_type="query",  # Use "query" for search queries
            truncation=True
        )
        return response.embeddings[0]
    
    def search(
        self,
        query: str,
        limit: int = 5,
        fusion_method: str = "rrf",  # "rrf" or "weighted"
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        filter_conditions: Optional[models.Filter] = None,
        score_threshold: Optional[float] = None,
        use_adaptive_prefetch: bool = True  # NEW: Enable adaptive prefetch
    ) -> List[Dict]:
        """
        Perform hybrid search with adaptive prefetch multiplier
        
        Args:
            query: Search query string
            limit: Number of results to return
            fusion_method: "rrf" (Reciprocal Rank Fusion) or "weighted"
            dense_weight: Weight for dense search (only for weighted fusion)
            sparse_weight: Weight for sparse search (only for weighted fusion)
            filter_conditions: Optional Qdrant filter to apply
            score_threshold: Minimum score threshold for results
            use_adaptive_prefetch: Use query complexity to adjust prefetch limit
        
        Returns:
            List of search results with scores and payloads
        """
        # Generate query vectors
        dense_query = self._get_dense_embedding(query)
        sparse_query = self._text_to_sparse_bm25(query)
        
        # Adaptive prefetch multiplier based on query complexity
        if use_adaptive_prefetch:
            prefetch_multiplier = self._estimate_query_complexity(query)
        else:
            prefetch_multiplier = 2  # Original behavior
        
        prefetch_limit = limit * prefetch_multiplier
        
        # Build prefetch operations
        prefetch_operations = [
            models.Prefetch(
                query=dense_query,
                using="dense",
                limit=prefetch_limit
            ),
            models.Prefetch(
                query=sparse_query,
                using="sparse",
                limit=prefetch_limit
            )
        ]
        
        # Choose fusion strategy
        if fusion_method.lower() == "rrf":
            fusion_query = models.FusionQuery(fusion=models.Fusion.RRF)
        else:
            fusion_query = models.FusionQuery(
                fusion=models.Fusion.WEIGHTED,
                weights=[dense_weight, sparse_weight]
            )
        
        # Perform search (filter applied here, not in prefetch)
        result = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=prefetch_operations,
            query=fusion_query,
            query_filter=filter_conditions,  # Filter applies to the final merged results
            limit=limit,
            with_payload=True,
            score_threshold=score_threshold
        )
        
        # Format results
        search_results = []
        for point in result.points:
            search_results.append({
                "id": point.id,
                "score": point.score,
                "payload": point.payload,
                "text": point.payload.get("text", ""),
                "context": point.payload.get("context", ""),
                "source": point.payload.get("source", ""),
                "heading": point.payload.get("heading", "")
            })
        
        return search_results
    
    def search_with_expansion(
        self,
        query: str,
        limit: int = 5,
        fusion_method: str = "rrf"
    ) -> List[Dict]:
        """
        Search with query expansion using domain synonyms
        
        Generates multiple query variations and merges results
        """
        # Get query variations
        query_variations = self._expand_query(query)
        
        all_results = {}
        for q in query_variations:
            results = self.search(q, limit=limit * 2, fusion_method=fusion_method)
            for r in results:
                doc_id = r['id']
                # Keep highest score for each unique document
                if doc_id not in all_results or r['score'] > all_results[doc_id]['score']:
                    all_results[doc_id] = r
        
        # Sort by score and return top K
        ranked = sorted(all_results.values(), key=lambda x: x['score'], reverse=True)
        return ranked[:limit]
    
    def search_with_reranking(
        self,
        query: str,
        limit: int = 5,
        prefetch_limit: int = 20,
        rerank_model: str = "rerank-2"
    ) -> List[Dict]:
        """
        Two-stage retrieval:
        1. Hybrid search (RRF) retrieves top candidates
        2. Voyage Rerank 2.0 reranks to final top K
        
        Args:
            query: Search query
            limit: Final number of results
            prefetch_limit: Candidates to fetch before reranking
            rerank_model: Voyage rerank model ("rerank-2" or "rerank-2-lite")
        
        Returns:
            Reranked search results
        """
        # Stage 1: Hybrid retrieval with adaptive prefetch
        candidates = self.search(query, limit=prefetch_limit)
        
        if not candidates:
            return []
        
        # Stage 2: Reranking
        docs_to_rerank = [c['text'] for c in candidates]
        
        try:
            # Call Voyage Rerank API
            rerank_response = self.vo.rerank(
                query=query,
                documents=docs_to_rerank,
                model=rerank_model,
                top_k=limit
            )
            
            # Map reranked results back to original candidates
            reranked_results = []
            for result in rerank_response.results:
                idx = result.index
                reranked_results.append({
                    **candidates[idx],
                    "rerank_score": result.relevance_score,
                    "original_score": candidates[idx]["score"],
                    "score": result.relevance_score  # Use rerank score as primary
                })
            
            return reranked_results
            
        except Exception as e:
            print(f"⚠️  Reranking failed: {e}. Falling back to original results.")
            return candidates[:limit]
    
    def search_dense_only(
        self,
        query: str,
        limit: int = 5,
        filter_conditions: Optional[models.Filter] = None
    ) -> List[Dict]:
        """Semantic search using only dense vectors"""
        dense_query = self._get_dense_embedding(query)
        
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=dense_query,
            using="dense",
            limit=limit,
            query_filter=filter_conditions,
            with_payload=True
        )
        
        return [
            {
                "id": point.id,
                "score": point.score,
                "payload": point.payload,
                "text": point.payload.get("text", ""),
            }
            for point in result.points
        ]
    
    def search_sparse_only(
        self,
        query: str,
        limit: int = 5,
        filter_conditions: Optional[models.Filter] = None
    ) -> List[Dict]:
        """Keyword search using only sparse vectors (BM25)"""
        sparse_query = self._text_to_sparse_bm25(query)
        
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=sparse_query,
            using="sparse",
            limit=limit,
            query_filter=filter_conditions,
            with_payload=True
        )
        
        return [
            {
                "id": point.id,
                "score": point.score,
                "payload": point.payload,
                "text": point.payload.get("text", ""),
            }
            for point in result.points
        ]
    
    def compare_search_methods(self, query: str, limit: int = 5):
        """
        Compare all three search methods side-by-side
        
        Returns:
            Dictionary with dense, sparse, and hybrid results
        """
        print(f"\n🔍 Query: '{query}'")
        print("=" * 80)
        
        # Dense only
        print("\n📊 DENSE (Semantic) Search:")
        print("-" * 80)
        dense_results = self.search_dense_only(query, limit)
        for i, res in enumerate(dense_results, 1):
            print(f"{i}. [{res['score']:.4f}] {res['text'][:150]}...")
        
        # Sparse only
        print("\n📊 SPARSE (BM25 Keyword) Search:")
        print("-" * 80)
        sparse_results = self.search_sparse_only(query, limit)
        for i, res in enumerate(sparse_results, 1):
            print(f"{i}. [{res['score']:.4f}] {res['text'][:150]}...")
        
        # Hybrid
        print("\n📊 HYBRID (RRF Fusion) Search:")
        print("-" * 80)
        hybrid_results = self.search(query, limit, fusion_method="rrf")
        for i, res in enumerate(hybrid_results, 1):
            print(f"{i}. [{res['score']:.4f}] {res['text'][:150]}...")
        
        return {
            "dense": dense_results,
            "sparse": sparse_results,
            "hybrid": hybrid_results
        }


# Convenience function for quick usage
def create_hybrid_searcher(
    qdrant_url: str = "http://localhost:6333",
    collection_name: str = "rfq_documents",
    voyage_api_key: Optional[str] = None
) -> HybridSearcher:
    """
    Quick factory function to create a hybrid searcher
    
    Args:
        qdrant_url: URL of Qdrant instance
        collection_name: Collection to search
        voyage_api_key: Voyage AI API key
    
    Returns:
        Configured HybridSearcher instance
    """
    client = QdrantClient(url=qdrant_url)
    return HybridSearcher(client, collection_name, voyage_api_key)

# Global cached instance to avoid rebuilding vocabulary on every query
_CACHED_SEARCHER: Optional[HybridSearcher] = None

def get_cached_searcher() -> HybridSearcher:
    """
    Get or create a cached HybridSearcher instance.
    
    This prevents rebuilding the vocabulary on every query call,
    which can take 5-10 seconds for large collections.
    """
    global _CACHED_SEARCHER
    
    if _CACHED_SEARCHER is None:
        print("🔧 Initializing cached searcher (vocabulary build - one time only)...")
        _CACHED_SEARCHER = create_hybrid_searcher(
            collection_name="rfq_documents",
            voyage_api_key=os.getenv("VOYAGE_API_KEY")
        )
    
    return _CACHED_SEARCHER

def query_vector_db(query: str, limit: int = 5) -> str:
    """
    Searches the RFQ vector database for relevant requirements using enhanced hybrid search.
    
    This tool performs:
    1. Hybrid search (semantic + keyword) with adaptive prefetch
    2. Voyage Rerank 2.0 for precision refinement
    
    Use this to extract specific information about requirements, criteria, thresholds,
    specifications, and other details from RFQ documents.
    
    Args:
        query: The search query. Be specific and targeted. Examples:
               - "What are the eligibility criteria for vendors?"
               - "Financial turnover requirements"
               - "ISO certifications required"
               - "Experience requirements in years"
               - "Technical specifications for products"
        limit: Number of results to return (default: 5). Use higher values for broad queries.
        
    Returns:
        A formatted string containing relevant text chunks with:
        - Reranked relevance score (higher = more relevant)
        - Source document name
        - Contextual description of the chunk
        - Actual content from the RFQ
        
    Example Usage:
        # Ask targeted questions to extract specific criteria
        result = query_vector_db("minimum annual turnover requirement", limit=3)
        
        # Based on results, refine your next question
        result = query_vector_db("turnover calculation method and proof documents", limit=3)
    """
    
    # Log the question being asked (for transparency during extraction)
    print(f"\n🔍 Question: {query}")
    print(f"   (Using enhanced search: adaptive prefetch + reranking, top {limit} results...)")
    
    # Get cached searcher instance (vocabulary already built)
    searcher = get_cached_searcher()
    
    # Perform search with reranking (Priority 1 improvement)
    try:
        results = searcher.search_with_reranking(
            query=query,
            limit=limit,
            prefetch_limit=min(20, limit * 4)  # Fetch more candidates for reranking
        )
    except Exception as e:
        # Fallback to basic hybrid search if reranking fails
        print(f"⚠️  Reranking unavailable, using standard hybrid search: {e}")
        results = searcher.search(query, limit=limit)
    
    # Format output for the Agent
    output = []
    for i, res in enumerate(results, 1):
        source = res.get('source', 'Unknown')
        text = res.get('text', '').strip()
        score = res.get('score', 0.0)
        rerank_score = res.get('rerank_score')
        context = res.get('context', '').strip()
        heading = res.get('heading', 'General')
        
        # Show both scores if reranking was used
        score_str = f"Rerank: {rerank_score:.4f}" if rerank_score else f"Score: {score:.4f}"
        
        output.append(
            f"Result {i} ({score_str}, Source: {source}, Section: {heading}):\n"
            f"Context: {context}\n"
            f"Content: {text}\n"
        )
        
    return "\n---\n".join(output) if output else "No relevant documents found."



# Wrap as ADK FunctionTool
from google.adk.tools import FunctionTool
query_vector_db_tool = FunctionTool(query_vector_db)

# Aliases to handle LLM hallucinations of the tool name
# (same pattern as memorize_vendor_data aliases in working reference)
def query_Vectordb(query: str, limit: int = 5) -> str:
    """Alias for query_vector_db (handles capitalization)."""
    return query_vector_db(query, limit)

def query_vectordb(query: str, limit: int = 5) -> str:
    """Alias for query_vector_db (handles missing underscore)."""
    return query_vector_db(query, limit)

def queryVectorDb(query: str, limit: int = 5) -> str:
    """Alias for query_vector_db (handles camelCase)."""
    return query_vector_db(query, limit)

def query_vector_Db(query: str, limit: int = 5) -> str:
    """Alias for query_vector_db (handles mixed case)."""
    return query_vector_db(query, limit)

# Export alias tools
query_Vectordb_tool = FunctionTool(query_Vectordb)
query_vectordb_tool = FunctionTool(query_vectordb)
queryVectorDb_tool = FunctionTool(queryVectorDb)
query_vector_Db_tool = FunctionTool(query_vector_Db)
def query_vactor_db(query: str, limit: int = 5) -> str:
    """Alias for query_vector_db (handles common typo: vactor instead of vector)."""
    return query_vector_db(query, limit)

query_vactor_db_tool = FunctionTool(query_vactor_db)

