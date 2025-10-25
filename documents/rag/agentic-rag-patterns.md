# Agentic RAG Patterns

Guide to implementing Retrieval-Augmented Generation (RAG) with agentic workflows.

## Overview

**RAG (Retrieval-Augmented Generation):**
- Retrieve relevant documents from knowledge base
- Augment LLM prompts with retrieved context
- Generate responses grounded in retrieved knowledge

**Agentic RAG:**
- AI agents decide WHEN and WHAT to retrieve
- Multi-step reasoning with retrieval
- Dynamic query reformulation
- Tool use combined with retrieval

## Basic RAG Architecture

### Simple RAG Flow

```
User Query
    ↓
Query → Vector Search → Top-K Documents
    ↓
Retrieved Docs + Query → LLM → Response
```

### Implementation

```python
async def simple_rag(query: str) -> str:
    """Basic RAG implementation."""

    # 1. Embed query
    query_embedding = await embed_text(query)

    # 2. Vector search
    documents = await vector_search(
        embedding=query_embedding,
        top_k=5
    )

    # 3. Build context
    context = "\n\n".join([doc["content"] for doc in documents])

    # 4. Generate response
    response = await llm.generate(
        prompt=f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:",
        max_tokens=1024
    )

    return response
```

## Agentic RAG Patterns

### Pattern 1: Conditional Retrieval

Agent decides IF retrieval is needed:

```python
async def agentic_rag(query: str, conversation_history: list) -> str:
    """Agent decides if RAG is needed."""

    # 1. Route: Does this need RAG?
    routing = await router_agent(query)

    if routing["needs_rag"]:
        # 2. Retrieve documents
        documents = await retrieve_documents(routing["rag_query"])

        # 3. Generate with context
        response = await generate_with_context(query, documents)
    else:
        # Direct generation (no retrieval)
        response = await generate_without_rag(query)

    return response
```

### Pattern 2: Query Reformulation

Agent reformulates query for better retrieval:

```python
async def reformulation_rag(query: str) -> str:
    """Reformulate query for better retrieval."""

    # 1. Analyze query
    analysis = await llm.generate(
        prompt=f"""Analyze this query and create 3 search queries:
        User query: {query}

        Output JSON:
        {{
            "search_queries": ["query1", "query2", "query3"]
        }}"""
    )

    search_queries = json.loads(analysis)["search_queries"]

    # 2. Multi-query retrieval
    all_documents = []
    for sq in search_queries:
        docs = await retrieve_documents(sq)
        all_documents.extend(docs)

    # 3. Deduplicate and rank
    unique_docs = deduplicate_documents(all_documents)

    # 4. Generate response
    response = await generate_with_context(query, unique_docs)

    return response
```

### Pattern 3: Multi-Step RAG

Agent performs multiple retrieval steps:

```python
async def multistep_rag(query: str) -> str:
    """Multi-step retrieval with reasoning."""

    # 1. Initial retrieval
    docs_1 = await retrieve_documents(query)

    # 2. Reasoning step 1
    reasoning_1 = await llm.generate(
        prompt=f"Context: {docs_1}\nQuestion: {query}\nWhat else do we need to know?"
    )

    # 3. Follow-up retrieval
    if reasoning_1["needs_more_info"]:
        docs_2 = await retrieve_documents(reasoning_1["follow_up_query"])
        all_docs = docs_1 + docs_2
    else:
        all_docs = docs_1

    # 4. Final generation
    response = await generate_with_context(query, all_docs)

    return response
```

### Pattern 4: Self-RAG (Self-Reflective)

Agent evaluates retrieval quality and retries:

```python
async def self_rag(query: str, max_iterations: int = 3) -> str:
    """Self-reflective RAG with quality checks."""

    for iteration in range(max_iterations):
        # 1. Retrieve
        documents = await retrieve_documents(query)

        # 2. Self-evaluate retrieval quality
        evaluation = await llm.generate(
            prompt=f"""Evaluate if these documents answer the query:
            Query: {query}
            Documents: {documents}

            Output JSON:
            {{
                "quality": "good" | "poor",
                "reasoning": "...",
                "improved_query": "..." if poor
            }}"""
        )

        eval_result = json.loads(evaluation)

        if eval_result["quality"] == "good":
            break  # Good retrieval

        # 3. Reformulate query
        query = eval_result["improved_query"]

    # 4. Generate response
    response = await generate_with_context(query, documents)

    return response
```

## Vector Database Operations

### Embedding Text

```python
from anthropic import Anthropic

async def embed_text(text: str) -> list[float]:
    """Generate embedding for text."""
    # Using OpenAI embeddings (example)
    import openai

    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    return response.data[0].embedding
```

### Vector Search (Supabase/pgvector)

```python
async def vector_search(
    embedding: list[float],
    top_k: int = 5,
    threshold: float = 0.7
) -> list[dict]:
    """Search documents by vector similarity."""

    # SQL query with pgvector
    query = """
    SELECT
        id,
        content,
        metadata,
        1 - (embedding <=> $1::vector) AS similarity
    FROM documents
    WHERE 1 - (embedding <=> $1::vector) > $2
    ORDER BY embedding <=> $1::vector
    LIMIT $3
    """

    results = await supabase.rpc(
        "vector_search",
        {
            "query_embedding": embedding,
            "match_threshold": threshold,
            "match_count": top_k
        }
    ).execute()

    return results.data
```

### Hybrid Search (Vector + Keyword)

```python
async def hybrid_search(
    query: str,
    embedding: list[float],
    top_k: int = 10
) -> list[dict]:
    """Combine vector and keyword search."""

    # 1. Vector search
    vector_results = await vector_search(embedding, top_k)

    # 2. Keyword search (PostgreSQL full-text)
    keyword_results = await supabase.from_("documents").select("*").text_search(
        "content",
        query,
        config="english"
    ).limit(top_k).execute()

    # 3. Merge and re-rank (RRF - Reciprocal Rank Fusion)
    merged = merge_and_rerank(vector_results, keyword_results.data)

    return merged[:top_k]
```

## Document Processing

### Chunking Strategies

```python
def chunk_document(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> list[str]:
    """Split document into overlapping chunks."""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap  # Overlap

    return chunks
```

### Semantic Chunking

```python
async def semantic_chunk(text: str) -> list[str]:
    """Split by semantic meaning (paragraphs/sections)."""
    # Split by double newline (paragraphs)
    paragraphs = text.split("\n\n")

    # Group small paragraphs
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < 1000:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
```

### Metadata Enrichment

```python
async def enrich_chunk(chunk: str, document_metadata: dict) -> dict:
    """Add metadata to chunk for better retrieval."""
    return {
        "content": chunk,
        "metadata": {
            **document_metadata,
            "chunk_length": len(chunk),
            "source": document_metadata.get("source"),
            "created_at": datetime.now().isoformat()
        }
    }
```

## Retrieval Optimization

### Reranking

```python
async def rerank_documents(
    query: str,
    documents: list[dict],
    top_k: int = 5
) -> list[dict]:
    """Rerank documents using LLM."""

    # Score each document
    scored_docs = []
    for doc in documents:
        score_prompt = f"""Rate relevance (0-10):
        Query: {query}
        Document: {doc['content'][:500]}

        Score:"""

        score = await llm.generate(score_prompt, max_tokens=5)
        scored_docs.append({**doc, "llm_score": float(score)})

    # Sort by LLM score
    reranked = sorted(scored_docs, key=lambda x: x["llm_score"], reverse=True)

    return reranked[:top_k]
```

### Query Expansion

```python
async def expand_query(query: str) -> list[str]:
    """Generate multiple query variations."""
    expansion_prompt = f"""Generate 3 alternative phrasings:
    Original: {query}

    1.
    2.
    3."""

    expanded = await llm.generate(expansion_prompt)

    return [query] + parse_expanded_queries(expanded)
```

## Agent Integration

### RAG in LangGraph Workflow

```python
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    query: str
    needs_rag: bool
    rag_query: str
    retrieved_docs: list[dict]
    response: str

# Create graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("router", router_agent)
workflow.add_node("retriever", retrieval_agent)
workflow.add_node("generator", generation_agent)

# Conditional routing
def should_retrieve(state: AgentState) -> str:
    if state["needs_rag"]:
        return "retriever"
    return "generator"

workflow.add_conditional_edges(
    "router",
    should_retrieve,
    {
        "retriever": "retriever",
        "generator": "generator"
    }
)

workflow.add_edge("retriever", "generator")
```

### Retrieval Agent Implementation

```python
async def retrieval_agent(state: AgentState) -> dict:
    """Retrieve relevant documents."""

    query = state["rag_query"]

    # 1. Embed query
    embedding = await embed_text(query)

    # 2. Vector search
    documents = await vector_search(embedding, top_k=5)

    # 3. Rerank
    reranked = await rerank_documents(query, documents, top_k=3)

    return {"retrieved_docs": reranked}
```

## Best Practices

### 1. Chunk Size Optimization

```python
# ✅ Good - semantic chunks with overlap
chunks = chunk_document(
    text=document,
    chunk_size=1000,  # ~250 words
    chunk_overlap=200  # 20% overlap
)
```

### 2. Metadata for Filtering

```python
# ✅ Good - rich metadata
document = {
    "content": "...",
    "metadata": {
        "source": "chatwoot_docs",
        "category": "api",
        "language": "en",
        "created_at": "2025-01-15",
        "tags": ["contacts", "conversations"]
    }
}

# Filter during search
results = await vector_search_with_filter(
    embedding=embedding,
    filters={"category": "api", "language": "nl"}
)
```

### 3. Caching Retrieved Documents

```python
# ✅ Good - cache for repeated queries
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_retrieve(query: str) -> list[dict]:
    """Cache retrieval results."""
    embedding = await embed_text(query)
    return await vector_search(embedding)
```

### 4. Graceful Degradation

```python
# ✅ Good - fallback if no documents found
documents = await vector_search(embedding)

if not documents:
    # Generate without RAG
    response = await llm.generate(
        f"Answer this without additional context: {query}"
    )
else:
    # Generate with RAG
    response = await generate_with_context(query, documents)
```

### 5. Source Attribution

```python
# ✅ Good - cite sources
response = f"""{generated_answer}

Sources:
{chr(10).join([f"- {doc['metadata']['source']}" for doc in documents])}
"""
```

## Common Patterns

### RAG + Tool Use

```python
async def rag_with_tools(query: str) -> str:
    """Combine RAG with function calling."""

    # 1. Retrieve documents
    documents = await retrieve_documents(query)

    # 2. Generate with tools
    response = await llm.generate(
        system=f"Context: {documents}",
        messages=[{"role": "user", "content": query}],
        tools=[search_cars_tool, book_appointment_tool]
    )

    # 3. Execute tool if needed
    if response.tool_calls:
        tool_result = await execute_tool(response.tool_calls[0])
        return tool_result

    return response.content
```

### Conversational RAG

```python
async def conversational_rag(
    query: str,
    conversation_history: list[dict]
) -> str:
    """RAG with conversation context."""

    # 1. Reformulate query with history
    reformulated = await llm.generate(
        f"Conversation:\n{conversation_history}\n\nLatest: {query}\n\nStandalone query:"
    )

    # 2. Retrieve with reformulated query
    documents = await retrieve_documents(reformulated)

    # 3. Generate with full context
    response = await llm.generate(
        system=f"Context: {documents}",
        messages=conversation_history + [{"role": "user", "content": query}]
    )

    return response
```

## Performance Tips

1. **Use caching** for repeated queries
2. **Batch embed** multiple texts together
3. **Index optimization** - pgvector HNSW for speed
4. **Top-K tuning** - fewer docs = faster, more focused
5. **Async operations** - parallel retrieval + generation

## Source

Documentation compiled from:
- https://python.langchain.com/docs/use_cases/question_answering/
- RAG research papers
- Production RAG implementations
- Agentic RAG patterns from LangChain
