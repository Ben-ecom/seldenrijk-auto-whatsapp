"""
Test Chatwoot API connection and configuration.

This script verifies:
1. Chatwoot is reachable
2. API token is valid
3. Account ID is correct
4. Can retrieve account details
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


def test_chatwoot_connection():
    """Test Chatwoot API connection."""
    print("=" * 60)
    print("🔍 CHATWOOT CONNECTION TEST")
    print("=" * 60)

    # Get configuration from .env
    base_url = os.getenv("CHATWOOT_BASE_URL")
    api_token = os.getenv("CHATWOOT_API_TOKEN")
    account_id = os.getenv("CHATWOOT_ACCOUNT_ID")

    print("\n📋 Configuration:")
    print(f"   Base URL: {base_url}")
    print(f"   API Token: {'✅ Set' if api_token else '❌ Missing'}")
    print(f"   Account ID: {account_id}")

    if not all([base_url, api_token, account_id]):
        print("\n❌ Missing configuration!")
        print("\nRequired .env variables:")
        print("   - CHATWOOT_BASE_URL")
        print("   - CHATWOOT_API_TOKEN")
        print("   - CHATWOOT_ACCOUNT_ID")
        return False

    # Test 1: Ping Chatwoot
    print("\n" + "=" * 60)
    print("TEST 1: Ping Chatwoot server")
    print("=" * 60)

    try:
        response = requests.get(base_url, timeout=5)
        print(f"✅ Chatwoot is reachable (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot reach Chatwoot server")
        print(f"   URL: {base_url}")
        print("\n💡 Tips:")
        print("   - Is Chatwoot running? (docker compose ps)")
        print("   - Check if port 3001 is accessible")
        print("   - Try: curl http://localhost:3001")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test 2: Validate API token
    print("\n" + "=" * 60)
    print("TEST 2: Validate API token")
    print("=" * 60)

    headers = {
        "api_access_token": api_token,
        "Content-Type": "application/json"
    }

    try:
        url = f"{base_url}/api/v1/accounts/{account_id}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            print("✅ API token is valid")
            data = response.json()
            print(f"\n📊 Account Details:")
            print(f"   Name: {data.get('name', 'N/A')}")
            print(f"   ID: {data.get('id', 'N/A')}")
            print(f"   Status: {data.get('status', 'N/A')}")
        elif response.status_code == 401:
            print("❌ API token is invalid (401 Unauthorized)")
            print("\n💡 Tips:")
            print("   - Generate new token in Chatwoot:")
            print("     Settings → Profile → Access Token")
            print("   - Update CHATWOOT_API_TOKEN in .env")
            return False
        elif response.status_code == 404:
            print(f"❌ Account ID {account_id} not found (404)")
            print("\n💡 Tips:")
            print("   - Check account ID in Chatwoot URL")
            print("   - Update CHATWOOT_ACCOUNT_ID in .env")
            return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test 3: List inboxes
    print("\n" + "=" * 60)
    print("TEST 3: List inboxes")
    print("=" * 60)

    try:
        url = f"{base_url}/api/v1/accounts/{account_id}/inboxes"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            inboxes = response.json().get("payload", [])
            print(f"✅ Found {len(inboxes)} inbox(es)")

            for inbox in inboxes:
                print(f"\n   📥 {inbox.get('name', 'N/A')}")
                print(f"      ID: {inbox.get('id', 'N/A')}")
                print(f"      Channel: {inbox.get('channel_type', 'N/A')}")
        else:
            print(f"❌ Failed to list inboxes: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test 4: List agents
    print("\n" + "=" * 60)
    print("TEST 4: List agents")
    print("=" * 60)

    try:
        url = f"{base_url}/api/v1/accounts/{account_id}/agents"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            agents = response.json()
            print(f"✅ Found {len(agents)} agent(s)")

            for agent in agents:
                print(f"\n   👤 {agent.get('name', 'N/A')}")
                print(f"      ID: {agent.get('id', 'N/A')}")
                print(f"      Email: {agent.get('email', 'N/A')}")
                print(f"      Role: {agent.get('role', 'N/A')}")
        else:
            print(f"❌ Failed to list agents: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # All tests passed
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\n🎉 Chatwoot connection is working correctly!")
    print("\nNext steps:")
    print("   - Ensure WhatsApp inbox is configured")
    print("   - Test sending messages via API")
    print("   - Test webhook integration")

    return True


if __name__ == "__main__":
    try:
        success = test_chatwoot_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
