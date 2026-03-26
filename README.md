Multi-Agent RAG Systems: The RFQ to PQR Workflow
Welcome! If you are a new graduate or beginner diving into the world of AI, Large Language Models (LLMs), and Agentic Systems, you are in the right place.

This guide will walk you step-by-step through a real-world enterprise application: extracting Pre-Qualifying Requirements (PQR) from highly complex Request for Quotation (RFQ) documents using a Multi-Agent Retrieval-Augmented Generation (RAG) system.

1. The Core Concepts (Jargon Buster)
Before we look at the code, let's understand the terms:

RFQ (Request for Quotation): A complex document a company sends out to vendors when they want to buy equipment, services, or construction work. It contains hundreds of pages of technical specs, financial rules, and legal terms.
PQR (Pre-Qualifying Requirements): A strict checklist hidden inside the RFQ. Vendors must meet these criteria (e.g., "Must have $5M annual revenue", "Must use ISO-certified steel") just to be allowed to bid.
RAG (Retrieval-Augmented Generation): A technique where an AI searches through your private documents (using a database) to find facts before answering a question. It prevents the AI from "hallucinating" or making things up.
Agent: An AI model given a specific persona, a set of instructions, and tools (like the ability to search a database or write files) to autonomously achieve a goal.
The Goal: We want AI agents to read massive RFQ PDFs and automatically output a neat PQR checklist in JSON format.

2. The 4-Step Workflow Architecture
This system isn't just one giant AI prompt. It's carefully split into a pipeline. Here is how the data flows from a raw PDF to a final structured output.

Step 1: Document Ingestion & Indexing (
ingestion.py
)
How do we teach the AI to "read" a 200-page PDF?

LLMs can't read PDFs directly efficiently. We have to break the PDF down into bite-sized pieces (chunks) and turn them into numbers (vectors) so the AI can search through them.

Parsing with Docling: The system uses a tool called Docling to read PDFs, Word docs, etc., and convert them into clean Markdown text, preserving tables and formatting.
Hybrid Chunking: The text is chopped into "chunks" (paragraphs/sections). We don't just chop blindly; we respect sentence boundaries to keep the meaning intact.
Context Injection (The Secret Sauce): Before saving a chunk, we ask a lightweight LLM (Gemini 2.5 Flash) to read it and write a 2-sentence summary (e.g., "This is an eligibility requirement about vendor financials."). This summary is glued to the chunk so the search engine always knows why the text matters.
Embedding & Vectorizing:
Dense Vectors (Voyage AI): Captures the "vibe" or semantic meaning of the text. (e.g., knows that "revenue" and "turnover" mean the same thing).
Sparse Vectors (BM25): Acts like a traditional keyword search. (e.g., looks for the exact number "ISO-9001:2015").
Qdrant Database: Both the dense and sparse vectors are saved into Qdrant, our Vector Database.
Step 2: The Orchestrator (
run_async.py
 & 
agent.py
)
Who is the boss of this operation?

We use a "Coordinator Agent." Think of this agent as the Project Manager.

It doesn't do the heavy lifting itself.
It receives the user's initial command: "Extract PQR from these RFQs."
It creates a shared memory space (session state) so all agents can share notes.
It delegates work to the Extractor Agent, waits for it to finish, and then passes the results to the Formulator Agent.
Step 3: The Extractor Agent (Deep Dive RAG)
How do we find the needles in the haystack?

Standard RAG just searches a database once. That's not good enough for massive RFQs. Our rfq_extractor_agent uses a rigorous loop called ReAct (Reasoning and Acting).

The ReAct Loop in Action:

Thought: "I need to figure out what type of RFQ this is."
Action: Agent uses its tool: 
query_vector_db("What is being procured?")
Observation: The database returns: "This is an RFQ for 300 TR Water Chillers."
Reflection: "Okay, it's equipment. Now I need to search for technical capacity specs."
The Extractor will repeat this loop 15 to 25 times, aggressively interrogating the Qdrant database until it is satisfied it has found all technical, financial, and eligibility rules.

Advanced Search Features Used Here:

Query Expansion: If the agent searches for "turnover", the system automatically also searches for "revenue" and "annual sales".
Adaptive Prefetching: If the agent asks a very short, vague question, the system automatically pulls more documents from the database to ensure nothing is missed.
Voyage Rerank 2.0: The database initially pulls dozens of potential matches. A specialized AI model (the Reranker) instantly grade-scores and re-sorts these documents so the Extractor Agent only ever reads the absolute most relevant paragraphs.
Step 4: The Formulator Agent (Data Structuring)
How do we make the data usable for software and humans?

The Extractor Agent has now found all the rules, but they are just raw text notes. The Coordinator passes these notes to the Formulator Agent (pqr_formulator_agent).

Its Job: Take raw text and turn it into strict, predictable formatting (JSON).
Document Classification: For every rule (e.g., "Vendor must be ISO certified"), the Formulator uses its logic to tag it with the exact verification document required (e.g., iso_certificate).
Finally, the Coordinator Agent takes this perfect JSON array and saves it directly to a file (pqr_outputs/pqr_results.json) for the user!

3. Summary of Why This System is "Advanced"
If you are building your own RAG systems, here is what takes this workflow from "Beginner" to "Enterprise-Grade":

Agentic Routing: Breaking the problem into two distinct brains (Extractor for searching, Formulator for structuring) rather than asking one LLM to do everything at once.
Hybrid Search + Reranking: Combining keyword search (BM25), semantic search (Dense Vectors), and a distinct Reranking model ensures almost 100% recall. No spec is left behind.
Iterative Looping (ReAct): Giving the agent permission to query the database as many times as it needs to, rather than just forcing a single "one-shot" query.
Next Steps for You:
To experiment with this codebase yourself:

Put a sample PDF into the client_pqr_agent/RFQDocs folder.
Run python ingestion.py to index it.
Run python run_async.py and watch the terminal to see the Agents "thinking" and "acting" in real time!
