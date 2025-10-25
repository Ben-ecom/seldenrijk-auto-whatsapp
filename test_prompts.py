#!/usr/bin/env python3
"""
Quick test script to verify APEX prompts are loaded correctly.
Run this to ensure the new prompt system works before testing with live WhatsApp.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env
load_dotenv(project_root / ".env")

from app.config.agents_config import (
    SYSTEM_PROMPT,
    KNOWLEDGE_BASE,
    SALES_PLAYBOOK,
    FAQ_PROMPT,
    build_conversation_prompt
)

def test_prompt_loading():
    """Test that all prompts loaded correctly."""
    print("=" * 80)
    print("🧪 TESTING APEX PROMPT SYSTEM")
    print("=" * 80)
    print()

    # Test individual prompts
    prompts = {
        "System Prompt": SYSTEM_PROMPT,
        "Knowledge Base": KNOWLEDGE_BASE,
        "Sales Playbook": SALES_PLAYBOOK,
        "FAQ": FAQ_PROMPT
    }

    all_loaded = True
    for name, content in prompts.items():
        status = "✅" if content and len(content) > 100 else "❌"
        length = len(content) if content else 0
        print(f"{status} {name:20s}: {length:,} characters")

        if not content or len(content) < 100:
            all_loaded = False
            print(f"   ⚠️  WARNING: {name} failed to load!")

    print()

    # Test combined prompt
    combined = build_conversation_prompt()
    print(f"{'✅' if combined else '❌'} Combined Prompt:       {len(combined):,} characters")

    print()
    print("=" * 80)

    if not all_loaded:
        print("❌ FAILED: Some prompts did not load correctly")
        print()
        print("Possible causes:")
        print("- prompts/ directory missing")
        print("- .md files not created yet")
        print("- File permissions issue")
        return False

    if len(combined) < 1000:
        print("❌ FAILED: Combined prompt suspiciously short")
        return False

    print("✅ SUCCESS: All prompts loaded correctly!")
    print()
    print("📊 Prompt Structure:")
    print(f"   • System Prompt:   {len(SYSTEM_PROMPT):>6,} chars (Lisa's personality)")
    print(f"   • Knowledge Base:  {len(KNOWLEDGE_BASE):>6,} chars (Tech specs + inventory)")
    print(f"   • Sales Playbook:  {len(SALES_PLAYBOOK):>6,} chars (Objections + closing)")
    print(f"   • FAQ:             {len(FAQ_PROMPT):>6,} chars (Quick answers)")
    print(f"   • TOTAL:           {len(combined):>6,} chars")
    print()

    return True


def preview_prompt_snippet():
    """Show a snippet of the combined prompt."""
    print("=" * 80)
    print("📄 PREVIEW: First 500 characters of combined prompt")
    print("=" * 80)
    print()

    combined = build_conversation_prompt()
    preview = combined[:500] + "..." if len(combined) > 500 else combined

    print(preview)
    print()
    print("=" * 80)
    print()


def test_conversation_agent_import():
    """Test that conversation agent can import the prompts."""
    print("=" * 80)
    print("🔧 TESTING CONVERSATION AGENT INTEGRATION")
    print("=" * 80)
    print()

    try:
        from app.agents.conversation_agent import CONVERSATION_SYSTEM_PROMPT

        if not CONVERSATION_SYSTEM_PROMPT:
            print("❌ FAILED: Conversation agent has empty prompt")
            return False

        print(f"✅ Conversation agent loaded prompt: {len(CONVERSATION_SYSTEM_PROMPT):,} chars")
        print()

        # Check if it's the new APEX prompt or fallback
        if "LISA - AUTOMOTIVE SALES AGENT" in CONVERSATION_SYSTEM_PROMPT:
            print("✅ Using APEX prompts (NEW)")
        else:
            print("⚠️  Using fallback prompt (OLD)")
            print("   This means APEX prompts failed to load in conversation agent")

        print()
        return True

    except Exception as e:
        print(f"❌ FAILED: Could not import conversation agent")
        print(f"   Error: {e}")
        return False


if __name__ == "__main__":
    print()
    success = True

    # Test 1: Prompt loading
    if not test_prompt_loading():
        success = False

    # Test 2: Preview
    preview_prompt_snippet()

    # Test 3: Agent integration
    if not test_conversation_agent_import():
        success = False

    # Final result
    print("=" * 80)
    if success:
        print("✅ ALL TESTS PASSED! WhatsApp agent is ready to use APEX prompts.")
        print()
        print("Next steps:")
        print("1. Test with real WhatsApp conversation")
        print("2. Validate AI responses match APEX standards")
        print("3. Iterate on prompts if needed")
    else:
        print("❌ SOME TESTS FAILED! Fix issues before proceeding.")
        print()
        print("Check:")
        print("- prompts/ directory exists")
        print("- All .md files are present")
        print("- File permissions are correct")

    print("=" * 80)
    print()

    sys.exit(0 if success else 1)
