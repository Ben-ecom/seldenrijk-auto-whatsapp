"""
API Structure Validation Script

This script validates that all API files are correctly structured
and can be imported without errors.
"""

import sys
from pathlib import Path

def validate_imports():
    """Validate that all API modules can be imported."""
    print("🔍 Validating API structure...\n")

    errors = []

    # Test 1: Import main API module
    print("1️⃣  Testing main API module...")
    try:
        from api import main
        print("   ✅ api.main imported successfully")
    except Exception as e:
        print(f"   ❌ Failed to import api.main: {e}")
        errors.append(f"api.main: {e}")

    # Test 2: Import middleware
    print("\n2️⃣  Testing middleware...")
    try:
        from api.middleware import RateLimitMiddleware
        print("   ✅ RateLimitMiddleware imported successfully")
    except Exception as e:
        print(f"   ❌ Failed to import middleware: {e}")
        errors.append(f"middleware: {e}")

    # Test 3: Import routes
    print("\n3️⃣  Testing routes...")
    try:
        from api.routes import webhook, leads, messages, auth
        print("   ✅ All routes imported successfully")
    except Exception as e:
        print(f"   ❌ Failed to import routes: {e}")
        errors.append(f"routes: {e}")

    # Test 4: Import agents
    print("\n4️⃣  Testing agent modules...")
    try:
        from agent import Agent1PydanticAI, Agent2ClaudeSDK, ConversationMessage
        print("   ✅ Agent modules imported successfully")
    except Exception as e:
        print(f"   ❌ Failed to import agents: {e}")
        errors.append(f"agents: {e}")

    # Test 5: Check environment variables
    print("\n5️⃣  Checking environment setup...")
    import os
    env_file = Path(".env")
    if env_file.exists():
        print("   ✅ .env file exists")
    else:
        print("   ⚠️  .env file not found (expected for development)")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("✅ All validation checks passed!")
        print("\n🚀 API is ready to run:")
        print("   python -m api.main")
        return True

if __name__ == "__main__":
    success = validate_imports()
    sys.exit(0 if success else 1)
