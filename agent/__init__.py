"""
Agent Module: 2-Agent Architecture (Pydantic AI + Claude SDK)

This module implements the enterprise-validated 2-agent system:
- Agent 1 (Pydantic AI): Structured extraction + qualification scoring
- Agent 2 (Claude SDK): Conversational flow + RAG + tool use

Architecture:
    - Agent 1: GPT-4o-mini (€0.003/conv) - Type-safe extraction
    - Agent 2: Claude 3.5 Sonnet (€0.15/conv) - Natural conversation
    - RAG: OpenAI embeddings + PGVector semantic search
    - Tools: 4 tools (search_jobs, search_docs, calendar, escalate)
"""

from .models import (
    LeadQualification,
    ConversationMessage,
    ExtractionInput,
    ExtractionResponse
)

from .agent_1_pydantic import (
    Agent1PydanticAI,
    extract_lead_qualification,
    get_sample_conversation
)

from .agent_2_claude import (
    Agent2ClaudeSDK,
    send_conversational_message
)

from .tools import (
    search_job_postings_impl,
    search_company_docs_impl,
    check_calendar_availability_impl,
    escalate_to_human_impl,
    TOOLS_DEFINITION
)

from .embeddings import (
    generate_job_posting_embeddings,
    generate_company_doc_embeddings,
    process_all_jobs,
    process_all_docs,
    seed_sample_data
)

__all__ = [
    # Models
    "LeadQualification",
    "ConversationMessage",
    "ExtractionInput",
    "ExtractionResponse",

    # Agent 1 (Pydantic AI)
    "Agent1PydanticAI",
    "extract_lead_qualification",
    "get_sample_conversation",

    # Agent 2 (Claude SDK)
    "Agent2ClaudeSDK",
    "send_conversational_message",

    # Tools
    "search_job_postings_impl",
    "search_company_docs_impl",
    "check_calendar_availability_impl",
    "escalate_to_human_impl",
    "TOOLS_DEFINITION",

    # Embeddings/RAG
    "generate_job_posting_embeddings",
    "generate_company_doc_embeddings",
    "process_all_jobs",
    "process_all_docs",
    "seed_sample_data",
]
