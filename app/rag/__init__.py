"""
RAG (Retrieval-Augmented Generation) Module.

Provides document retrieval for augmenting LLM responses with relevant context.
"""
from app.rag.retriever import DocumentRetriever, get_retriever, format_retrieved_context

__all__ = [
    "DocumentRetriever",
    "get_retriever",
    "format_retrieved_context"
]
