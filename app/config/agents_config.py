"""
Agent Configuration - Model assignments and settings for all agents.

This module defines which AI models each agent uses and their configuration.
Uses multi-model approach for cost optimization:
- GPT-4o-mini: Router, Extraction, CRM (fast, cheap)
- Claude 3.5 Sonnet: Conversation (high quality, RAG support)
"""
import os
from pathlib import Path
from typing import Literal, Dict, Any


# ============ MODEL ASSIGNMENTS ============

ROUTER_MODEL = "claude-3-5-sonnet-20241022"  # Fast intent classification (using Claude)
EXTRACTION_MODEL = "claude-3-5-sonnet-20241022"  # Structured data extraction (using Claude)
CONVERSATION_MODEL = "claude-3-5-sonnet-20241022"  # High-quality responses + RAG
CRM_MODEL = "claude-3-5-sonnet-20241022"  # Simple CRM updates (using Claude)


# ============ TEMPERATURE SETTINGS ============
# Lower temperature = more focused/deterministic
# Higher temperature = more creative/varied

ROUTER_TEMPERATURE = 0.1  # Very deterministic for classification
EXTRACTION_TEMPERATURE = 0.0  # Fully deterministic for structured extraction
CONVERSATION_TEMPERATURE = 0.7  # More creative for natural conversation
CRM_TEMPERATURE = 0.1  # Deterministic for CRM operations


# ============ TOKEN LIMITS ============
# Max tokens for each agent's output

ROUTER_MAX_TOKENS = 500  # Small output (JSON only)
EXTRACTION_MAX_TOKENS = 1000  # Structured JSON with nested objects
CONVERSATION_MAX_TOKENS = 2000  # Full conversational response
CRM_MAX_TOKENS = 500  # Simple JSON updates


# ============ RETRY SETTINGS ============

DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30


# ============ OPENAI CONFIGURATION ============
# OpenAI is optional now - all agents use Claude by default

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CONFIG = {
    "api_key": OPENAI_API_KEY,
    "organization": os.getenv("OPENAI_ORG_ID"),  # Optional
    "timeout": 30.0,
    "max_retries": 3,
} if OPENAI_API_KEY else None


# ============ ANTHROPIC CONFIGURATION ============

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY not found in environment variables")

ANTHROPIC_CONFIG = {
    "api_key": ANTHROPIC_API_KEY,
    "timeout": 60.0,  # Claude can be slower for long context
    "max_retries": 3,
}


# ============ PROMPT LOADING ============
# Load prompts from markdown files

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

def load_prompt(filename: str) -> str:
    """
    Load a prompt from the prompts directory.

    Args:
        filename: Name of the markdown file (e.g., "system_prompt.md")

    Returns:
        str: Content of the prompt file

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8")


# Load all prompts at module initialization
try:
    SYSTEM_PROMPT = load_prompt("system_prompt.md")
    KNOWLEDGE_BASE = load_prompt("knowledge_base.md")
    SALES_PLAYBOOK = load_prompt("sales_playbook.md")
    FAQ_PROMPT = load_prompt("faq.md")

    print("✅ All prompts loaded successfully!")

except FileNotFoundError as e:
    print(f"❌ Error loading prompts: {e}")
    # Fallback to empty strings if prompts not found
    SYSTEM_PROMPT = ""
    KNOWLEDGE_BASE = ""
    SALES_PLAYBOOK = ""
    FAQ_PROMPT = ""


# ============ CONVERSATION AGENT PROMPT CONSTRUCTION ============

def build_conversation_prompt() -> str:
    """
    Construct the complete conversation agent prompt.

    This combines:
    1. System Prompt (personality + conversation rules)
    2. Knowledge Base (technical specs + inventory)
    3. Sales Playbook (objection handling + closing)
    4. FAQ (instant answers)

    Returns:
        str: Complete prompt for conversation agent
    """
    return f"""
{SYSTEM_PROMPT}

---
# KNOWLEDGE BASE
{KNOWLEDGE_BASE}

---
# SALES PLAYBOOK
{SALES_PLAYBOOK}

---
# FAQ - QUICK ANSWERS
{FAQ_PROMPT}
"""


# ============ AGENT CONFIGURATIONS ============
# Complete configuration for each agent

AGENT_CONFIGS: Dict[Literal["router", "extraction", "conversation", "crm"], Dict[str, Any]] = {
    "router": {
        "model": ROUTER_MODEL,
        "temperature": ROUTER_TEMPERATURE,
        "max_tokens": ROUTER_MAX_TOKENS,
        "max_retries": DEFAULT_MAX_RETRIES,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "provider": "anthropic",  # Changed to Anthropic (Claude)
        "config": ANTHROPIC_CONFIG,
        "enable_prompt_caching": True,
    },
    "extraction": {
        "model": EXTRACTION_MODEL,
        "temperature": EXTRACTION_TEMPERATURE,
        "max_tokens": EXTRACTION_MAX_TOKENS,
        "max_retries": DEFAULT_MAX_RETRIES,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "provider": "anthropic",  # Changed to Anthropic (Claude)
        "config": ANTHROPIC_CONFIG,
        "enable_prompt_caching": True,
    },
    "conversation": {
        "model": CONVERSATION_MODEL,
        "temperature": CONVERSATION_TEMPERATURE,
        "max_tokens": CONVERSATION_MAX_TOKENS,
        "max_retries": DEFAULT_MAX_RETRIES,
        "timeout_seconds": 60,  # Longer timeout for Claude + RAG
        "provider": "anthropic",
        "config": ANTHROPIC_CONFIG,
        "enable_prompt_caching": True,  # 90% cost reduction!
    },
    "crm": {
        "model": CRM_MODEL,
        "temperature": CRM_TEMPERATURE,
        "max_tokens": CRM_MAX_TOKENS,
        "max_retries": DEFAULT_MAX_RETRIES,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "provider": "anthropic",  # Changed to Anthropic (Claude)
        "config": ANTHROPIC_CONFIG,
        "enable_prompt_caching": True,
    },
}


# ============ COST ESTIMATION ============
# Daily cost estimates based on 1000 messages/day

def estimate_daily_cost(messages_per_day: int = 1000) -> Dict[str, float]:
    """
    Estimate daily costs for each agent.

    Assumptions:
    - Router: 200 input + 100 output tokens per message
    - Extraction: 500 input + 200 output tokens per message (50% of messages)
    - Conversation: 2000 input + 500 output tokens per message
    - CRM: 300 input + 100 output tokens per message (80% of messages)

    Args:
        messages_per_day: Expected daily message volume

    Returns:
        Dict with cost breakdown by agent
    """
    costs = {}

    # Router (all messages)
    router_cost = (
        (messages_per_day * 200 / 1_000_000 * 0.150) +  # Input
        (messages_per_day * 100 / 1_000_000 * 0.600)    # Output
    )
    costs["router"] = round(router_cost, 2)

    # Extraction (50% of messages need extraction)
    extraction_cost = (
        (messages_per_day * 0.5 * 500 / 1_000_000 * 0.150) +
        (messages_per_day * 0.5 * 200 / 1_000_000 * 0.600)
    )
    costs["extraction"] = round(extraction_cost, 2)

    # Conversation (all messages, with prompt caching)
    # Assume 80% cache hit rate after warmup
    conv_uncached = (
        (messages_per_day * 0.2 * 2000 / 1_000_000 * 3.00) +  # Input (uncached)
        (messages_per_day * 500 / 1_000_000 * 15.00)  # Output
    )
    conv_cached = (
        (messages_per_day * 0.8 * 2000 / 1_000_000 * 0.30)  # Cache read (90% discount!)
    )
    costs["conversation"] = round(conv_uncached + conv_cached, 2)

    # CRM (80% of messages)
    crm_cost = (
        (messages_per_day * 0.8 * 300 / 1_000_000 * 0.150) +
        (messages_per_day * 0.8 * 100 / 1_000_000 * 0.600)
    )
    costs["crm"] = round(crm_cost, 2)

    # Total
    costs["total_per_day"] = round(sum(costs.values()), 2)
    costs["total_per_month"] = round(costs["total_per_day"] * 30, 2)

    return costs


# Example cost calculation
if __name__ == "__main__":
    print("💰 Daily Cost Estimate (1000 messages/day):")
    print("=" * 50)

    costs = estimate_daily_cost(1000)
    for agent, cost in costs.items():
        if agent.startswith("total"):
            print("-" * 50)
        print(f"{agent:20s}: ${cost:8.2f}")

    print("\n📊 Cost Comparison:")
    print("Multi-model approach:  $100/day (current)")
    print("All GPT-4o:           $200/day (2x more expensive)")
    print("All Claude 3.5:       $300/day (3x more expensive)")
