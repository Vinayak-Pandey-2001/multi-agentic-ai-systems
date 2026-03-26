from pathlib import Path
from dotenv import load_dotenv
from docling.document_converter import DocumentConverter
from qdrant_client import QdrantClient, models
import os
from google import genai
from qdrant_client.http.models import PointStruct
from docling.chunking import HybridChunker
import voyageai
from pathlib import Path
import uuid
from collections import Counter
import math

load_dotenv(dotenv_path="/Users/vinayak/Downloads/venwiz/google-adk-clientPQR-agent/.env")
vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
client_gemini = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
GEMINI_MODEL = "gemini-2.5-flash"
client = QdrantClient("http://localhost:6333")
COLLECTION_NAME = "rfq_documents"

# Global vocabulary for BM25 sparse vectors
VOCABULARY = {}
DOCUMENT_STATS = {
    "total_docs": 0,
    "avg_doc_length": 0,
    "term_doc_freq": Counter()  # How many docs contain each term
}

def extract_to_markdown(source_path: str, output_dir: str = "output"):
    converter = DocumentConverter()
    print(f"Processing: {source_path}...")
    result = converter.convert(source_path)
    markdown_content = result.document.export_to_markdown()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    file_stem = Path(source_path).stem
    save_file = output_path / f"{file_stem}.md"
    with open(save_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"Successfully saved to: {save_file}")
    return markdown_content

def setup_collection():
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            }
        )

        # ✅ Create text index for filtering
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="text",
            field_schema=models.TextIndexParams(type="text")
        )
        
        print(f"✅ Collection '{COLLECTION_NAME}' created with hybrid search support")
    else:
        # Optional safety: ensure index exists even if collection already existed
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="text",
                field_schema=models.TextIndexParams(type="text")
            )
        except Exception:
            # Index already exists → safe to ignore
            pass

def tokenize(text: str) -> list[str]:
    """Simple tokenizer for BM25"""
    # Convert to lowercase, split on whitespace and common punctuation
    import re
    text = text.lower()
    tokens = re.findall(r'\b\w+\b', text)
    return [t for t in tokens if len(t) > 2]  # Filter out very short tokens

def build_vocabulary(all_texts: list[str]) -> dict:
    """Build vocabulary from all texts"""
    all_tokens = set()
    for text in all_texts:
        tokens = tokenize(text)
        all_tokens.update(tokens)
    
    vocab = {token: idx for idx, token in enumerate(sorted(all_tokens))}
    print(f"📚 Built vocabulary with {len(vocab)} unique tokens")
    return vocab

def calculate_idf(all_texts: list[str]) -> dict:
    """Calculate IDF (Inverse Document Frequency) for all terms"""
    global DOCUMENT_STATS
    
    total_docs = len(all_texts)
    term_doc_freq = Counter()
    
    # Count how many documents contain each term
    for text in all_texts:
        unique_tokens = set(tokenize(text))
        for token in unique_tokens:
            term_doc_freq[token] += 1
    
    # Calculate IDF: log(total_docs / doc_freq)
    idf_scores = {}
    for term, doc_freq in term_doc_freq.items():
        idf_scores[term] = math.log((total_docs + 1) / (doc_freq + 1)) + 1
    
    DOCUMENT_STATS["total_docs"] = total_docs
    DOCUMENT_STATS["term_doc_freq"] = term_doc_freq
    
    return idf_scores

def text_to_sparse_bm25(text: str, vocab: dict, idf_scores: dict, k1: float = 1.5, b: float = 0.75) -> tuple[list[int], list[float]]:
    """
    Generate BM25 sparse vector from text
    
    Args:
        text: Input text
        vocab: Token to index mapping
        idf_scores: IDF scores for each term
        k1: BM25 parameter (term frequency saturation)
        b: BM25 parameter (length normalization)
    
    Returns:
        Tuple of (indices, values) for sparse vector
    """
    tokens = tokenize(text)
    token_counts = Counter(tokens)
    
    doc_len = len(tokens)
    avg_doc_len = DOCUMENT_STATS.get("avg_doc_length", 100)
    
    indices = []
    values = []
    
    for token, count in token_counts.items():
        if token in vocab:
            idx = vocab[token]
            idf = idf_scores.get(token, 1.0)
            
            # BM25 formula
            numerator = count * (k1 + 1)
            denominator = count + k1 * (1 - b + b * (doc_len / avg_doc_len))
            bm25_score = idf * (numerator / denominator)
            
            indices.append(idx)
            values.append(float(bm25_score))
    
    return indices, values

def get_dense_embeddings(text: str) -> list[float]:
    response = vo.embed(
        texts=[text],
        model="voyage-4-large",
        input_type="document",
        truncation=True
    )
    return response.embeddings[0]

def generate_text(prompt: str) -> str:
    response = client_gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return response.text.strip()

def ingest_document(file_path: str, vocab: dict, idf_scores: dict):
    """
    Ingest a document with both dense and sparse vectors
    """
    # 1. Convert to Markdown using Docling
    converter = DocumentConverter()
    all_chunks = []    
    
    # Convert the document
    result = converter.convert(file_path)
    full_text = result.document.export_to_markdown()
    
    # 2. Use HybridChunker
    chunker = HybridChunker(
        tokenizer="sentence-transformers/all-mpnet-base-v2",
        merge_peers=True
    )
    
    doc_chunks = list(chunker.chunk(result.document))
    
    for i, chunk in enumerate(doc_chunks):
        print(chunk.text if i == 3 else "")
        all_chunks.append({
            "text": chunk.text,
            "metadata": {
                "source": file_path,
                "heading": " > ".join([h for h in chunk.meta.headings]) if chunk.meta.headings else "General"
            }
        })

    points = []
    for i, chunk in enumerate(all_chunks):
        # 3. Generate Situating Context
        prompt = f"""
You are analyzing an RFP/RFQ document.

Given the following section text, briefly describe:
1. What part of an RFP/RFQ this belongs to
2. Whether it looks like eligibility, financial, experience, or technical requirement

Section:
{chunk['text']}

Respond in 2 concise sentences.
"""
        context_summary = generate_text(prompt)
        contextual_chunk = f"{context_summary}\n\n{chunk['text']}"
        
        # 4. Generate Dense Embeddings
        dense_vector = get_dense_embeddings(contextual_chunk)
        
        # 5. Generate Sparse Vector (BM25)
        sparse_indices, sparse_values = text_to_sparse_bm25(
            chunk['text'], 
            vocab, 
            idf_scores
        )
        
        raw_id = f"{file_path}_{i}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, raw_id))
        
        points.append(PointStruct(
            id=point_id,
            vector={
                "dense": dense_vector,
                "sparse": models.SparseVector(
                    indices=sparse_indices,
                    values=sparse_values
                )
            },
            payload={
                "text": chunk['text'], 
                "context": context_summary, 
                "source": file_path,
                "heading": chunk['metadata']['heading']
            }
        ))
    
    if not points:
        print(f"⚠️ No text chunks found in {file_path}. Skipping ingestion.")
        return
    
    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"✅ Ingested {len(points)} chunks from {Path(file_path).name}")

def is_file_already_ingested(file_path: str) -> bool:
    if not client.collection_exists(COLLECTION_NAME):
        return False

    scroll, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=file_path)
                )
            ]
        ),
        limit=1
    )
    return len(scroll) > 0

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".png", ".jpg", ".jpeg"}

def ingest_folder(folder_path: str):
    """
    Ingest all documents in a folder with hybrid search support
    """
    global VOCABULARY, DOCUMENT_STATS
    
    folder = Path(folder_path)

    if not folder.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")

    files = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    print(f"📁 Found {len(files)} files in {folder_path}")
    
    # STEP 1: First pass - collect all texts to build vocabulary
    print("\n🔍 Step 1: Building vocabulary and calculating IDF scores...")
    all_texts = []
    file_chunks_map = {}
    
    converter = DocumentConverter()
    
    for file_path in files:
        file_path_str = str(file_path.resolve())
        
        if is_file_already_ingested(file_path_str):
            print(f"⏭️  Skipping already ingested file: {file_path.name}")
            continue
        
        print(f"  Analyzing: {file_path.name}")
        result = converter.convert(file_path_str)
        
        chunker = HybridChunker(
            tokenizer="sentence-transformers/all-mpnet-base-v2",
            merge_peers=True
        )
        
        doc_chunks = list(chunker.chunk(result.document))
        file_chunks_map[file_path_str] = doc_chunks
        
        for chunk in doc_chunks:
            all_texts.append(chunk.text)
    
    if not all_texts:
        print("⚠️ No new documents to ingest")
        return
    
    # Build vocabulary and calculate IDF
    VOCABULARY = build_vocabulary(all_texts)
    idf_scores = calculate_idf(all_texts)
    
    # Calculate average document length
    total_tokens = sum(len(tokenize(text)) for text in all_texts)
    DOCUMENT_STATS["avg_doc_length"] = total_tokens / len(all_texts)
    print(f"📊 Average document length: {DOCUMENT_STATS['avg_doc_length']:.1f} tokens")
    
    # STEP 2: Second pass - ingest with both dense and sparse vectors
    print("\n📥 Step 2: Ingesting documents with hybrid vectors...")
    for file_path_str, doc_chunks in file_chunks_map.items():
        print(f"  Processing: {Path(file_path_str).name}")
        ingest_document(file_path_str, VOCABULARY, idf_scores)

def reset_collection():
    if client.collection_exists(COLLECTION_NAME):
        print(f"🗑️ Deleting collection: {COLLECTION_NAME}")
        client.delete_collection(COLLECTION_NAME)

    print(f"✨ Recreating collection: {COLLECTION_NAME}")
    setup_collection()

# ============================================================
# HYBRID SEARCH FUNCTION
# ============================================================

def hybrid_search(
    query: str,
    limit: int = 5,
    dense_weight: float = 0.5,
    sparse_weight: float = 0.5,
    use_rrf: bool = True
) -> list[dict]:
    """
    Perform hybrid search combining dense (semantic) and sparse (keyword) retrieval
    
    Args:
        query: Search query
        limit: Number of results to return
        dense_weight: Weight for dense vector search (0-1)
        sparse_weight: Weight for sparse vector search (0-1)
        use_rrf: Use Reciprocal Rank Fusion (better than weighted average)
    
    Returns:
        List of search results with scores and payloads
    """
    # Generate dense query vector
    dense_query_vector = get_dense_embeddings(query)
    
    # Generate sparse query vector
    sparse_indices, sparse_values = text_to_sparse_bm25(
        query, 
        VOCABULARY, 
        calculate_idf([query])  # Simple IDF for query
    )
    sparse_query_vector = models.SparseVector(
        indices=sparse_indices,
        values=sparse_values
    )
    
    if use_rrf:
        # Use Reciprocal Rank Fusion (RRF) - recommended approach
        result = client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                # Prefetch 1: Dense vector search
                models.Prefetch(
                    query=dense_query_vector,
                    using="dense",
                    limit=limit * 2  # Fetch more for fusion
                ),
                # Prefetch 2: Sparse vector search
                models.Prefetch(
                    query=sparse_query_vector,
                    using="sparse",
                    limit=limit * 2
                )
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.RRF  # Reciprocal Rank Fusion
            ),
            limit=limit,
            with_payload=True
        )
    else:
        # Use weighted average fusion
        result = client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                models.Prefetch(
                    query=dense_query_vector,
                    using="dense",
                    limit=limit * 2,
                    score_threshold=0.0
                ),
                models.Prefetch(
                    query=sparse_query_vector,
                    using="sparse",
                    limit=limit * 2,
                    score_threshold=0.0
                )
            ],
            query=models.FusionQuery(
                fusion=models.Fusion.WEIGHTED,
                weights=[dense_weight, sparse_weight]
            ),
            limit=limit,
            with_payload=True
        )
    
    # Format results
    results = []
    for point in result.points:
        results.append({
            "id": point.id,
            "score": point.score,
            "text": point.payload.get("text", ""),
            "context": point.payload.get("context", ""),
            "source": point.payload.get("source", ""),
            "heading": point.payload.get("heading", "")
        })
    
    return results

def test_hybrid_search():
    """
    Test the hybrid search functionality
    """
    print("\n" + "="*60)
    print("TESTING HYBRID SEARCH")
    print("="*60)
    
    test_queries = [
        "What are the eligibility criteria?",
        "financial requirements",
        "technical specifications",
        "submission deadline"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 60)
        
        results = hybrid_search(query, limit=3, use_rrf=True)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result['score']:.4f}")
            print(f"   Source: {Path(result['source']).name}")
            print(f"   Heading: {result['heading']}")
            print(f"   Text: {result['text'][:200]}...")

if __name__ == "__main__":
    # Reset and ingest
    reset_collection()
    ingest_folder("/Users/vinayak/Downloads/venwiz/google-adk-clientPQR-agent/client_pqr_agent/RFQDocs")
    
    # Test hybrid search
    test_hybrid_search()