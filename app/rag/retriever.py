"""
RAG Document Retrieval Module.

Handles vector similarity search for retrieving relevant documentation.
Uses simple deterministic embeddings (no external API needed).
"""
import os
import re
import math
import hashlib
from typing import List, Dict, Any, Optional
from supabase import create_client
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)

# Configuration
EMBEDDING_DIMENSIONS = 1536
DEFAULT_SIMILARITY_THRESHOLD = 0.7
DEFAULT_MAX_RESULTS = 5


def create_simple_embedding(text: str) -> List[float]:
    """
    Create a simple deterministic embedding from text.
    Same algorithm as index_documentation_claude.py.

    Args:
        text: Text to embed

    Returns:
        1536-dimensional embedding vector
    """
    # Normalize text
    text = text.lower()
    words = re.findall(r'\w+', text)

    # Initialize embedding vector
    embedding = [0.0] * EMBEDDING_DIMENSIONS

    # 1. Word frequency component (first 768 dimensions)
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1

    for word, freq in word_freq.items():
        word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = word_hash % 768
        embedding[idx] += math.log(1 + freq)

    # 2. Position component (middle 384 dimensions)
    for i, word in enumerate(words[:384]):
        word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
        idx = 768 + (word_hash % 384)
        position_weight = 1.0 / (1 + i * 0.01)
        embedding[idx] += position_weight

    # 3. Character n-gram component (last 384 dimensions)
    char_ngrams = [text[i:i+3] for i in range(len(text)-2)]
    ngram_freq = {}
    for ngram in char_ngrams:
        ngram_freq[ngram] = ngram_freq.get(ngram, 0) + 1

    for ngram, freq in list(ngram_freq.items())[:384]:
        ngram_hash = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
        idx = 1152 + (ngram_hash % 384)
        embedding[idx] += math.log(1 + freq)

    # 4. Normalize to unit length
    magnitude = math.sqrt(sum(x * x for x in embedding))
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]

    return embedding


class DocumentRetriever:
    """Retrieve relevant documents using vector similarity search."""

    def __init__(self):
        """Initialize document retriever with Supabase client."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        if not self.supabase_url or not self.supabase_key:
            logger.warning("⚠️ Supabase credentials not set - RAG disabled")
            self.enabled = False
            return

        self.supabase = create_client(self.supabase_url, self.supabase_key)
        self.enabled = True

        logger.info("✅ DocumentRetriever initialized (no OpenAI needed)")

    async def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            category: Optional category filter (e.g., "chatwoot", "waha")
            max_results: Maximum number of results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of document dicts with content, metadata, and similarity score
        """
        if not self.enabled:
            logger.warning("RAG retrieval disabled - returning empty results")
            return []

        try:
            # 1. Embed query
            query_embedding = await self._embed_query(query)

            # 2. Vector search
            results = await self._vector_search(
                embedding=query_embedding,
                category=category,
                max_results=max_results,
                threshold=threshold
            )

            logger.info(
                f"✅ Retrieved {len(results)} documents",
                extra={
                    "query": query[:100],
                    "category": category,
                    "num_results": len(results)
                }
            )

            return results

        except Exception as e:
            logger.error(
                f"❌ Document retrieval failed: {e}",
                extra={"query": query, "error": str(e)},
                exc_info=True
            )
            return []

    async def _embed_query(self, query: str) -> List[float]:
        """
        Embed query text using simple deterministic approach.

        Args:
            query: Query text

        Returns:
            Embedding vector (1536 dimensions)
        """
        try:
            embedding = create_simple_embedding(query)
            logger.debug(f"Embedded query: {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Query embedding failed: {e}", exc_info=True)
            raise

    async def _vector_search(
        self,
        embedding: List[float],
        category: Optional[str],
        max_results: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Execute vector similarity search in Supabase.

        Args:
            embedding: Query embedding vector
            category: Optional category filter
            max_results: Maximum results
            threshold: Similarity threshold

        Returns:
            List of matching documents
        """
        try:
            # Call Supabase RPC function
            response = self.supabase.rpc(
                "match_documents",
                {
                    "query_embedding": embedding,
                    "match_threshold": threshold,
                    "match_count": max_results,
                    "filter_category": category
                }
            ).execute()

            documents = response.data

            logger.debug(
                f"Vector search returned {len(documents)} results",
                extra={"threshold": threshold, "category": category}
            )

            return documents

        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            raise


def format_retrieved_context(documents: List[Dict[str, Any]]) -> str:
    """
    Format retrieved documents into context string for LLM.

    Args:
        documents: List of retrieved document dicts

    Returns:
        Formatted context string
    """
    if not documents:
        return ""

    context_parts = ["**Retrieved Documentation:**\n"]

    for i, doc in enumerate(documents, 1):
        metadata = doc.get("metadata", {})
        source = metadata.get("source", "Unknown")
        section = metadata.get("section", "")
        similarity = doc.get("similarity", 0)

        context_parts.append(
            f"\n**[{i}] {source}** (similarity: {similarity:.2f})"
        )

        if section:
            context_parts.append(f"Section: {section}")

        context_parts.append(f"\n{doc['content']}\n")
        context_parts.append("---")

    return "\n".join(context_parts)


# Singleton instance
_retriever_instance = None


def get_retriever() -> DocumentRetriever:
    """
    Get singleton DocumentRetriever instance.

    Returns:
        DocumentRetriever instance
    """
    global _retriever_instance

    if _retriever_instance is None:
        _retriever_instance = DocumentRetriever()

    return _retriever_instance
