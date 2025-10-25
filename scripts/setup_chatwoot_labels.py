"""
Setup Chatwoot Labels - Create required labels for lead tagging.

This script creates all labels needed by the Enhanced CRM Agent.
Uses centralized tag_registry.py for single source of truth.
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import centralized tag registry
from config.tag_registry import ALL_LABELS


def get_chatwoot_config():
    """Get Chatwoot configuration from environment."""
    return {
        "base_url": os.getenv("CHATWOOT_BASE_URL", "http://localhost:3001"),
        "api_token": os.getenv("CHATWOOT_API_TOKEN"),
        "account_id": os.getenv("CHATWOOT_ACCOUNT_ID", "2")
    }


def list_labels(config):
    """List all existing labels."""
    url = f"{config['base_url']}/api/v1/accounts/{config['account_id']}/labels"
    headers = {
        "api_access_token": config["api_token"],
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get("payload", [])
    except Exception as e:
        print(f"❌ Error listing labels: {e}")
        return []


def create_label(config, title, description="", color="#1f93ff", show_on_sidebar=False):
    """Create a new label."""
    url = f"{config['base_url']}/api/v1/accounts/{config['account_id']}/labels"
    headers = {
        "api_access_token": config["api_token"],
        "Content-Type": "application/json"
    }

    data = {
        "title": title,
        "description": description,
        "color": color,
        "show_on_sidebar": show_on_sidebar
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Error creating label '{title}': {e}")
        return False


def main():
    """Setup all required Chatwoot labels."""
    print("=" * 60)
    print("🏷️  CHATWOOT LABELS SETUP")
    print("=" * 60)

    config = get_chatwoot_config()

    if not config["api_token"]:
        print("\n❌ CHATWOOT_API_TOKEN not set in .env")
        return False

    print(f"\n📋 Chatwoot URL: {config['base_url']}")
    print(f"📋 Account ID: {config['account_id']}")

    # Get required labels from centralized registry
    required_labels = [
        {
            "title": label["title"],
            "description": label["description"],
            "color": label["color"],
            "show_on_sidebar": label.get("show_on_sidebar", False)
        }
        for label in ALL_LABELS.values()
    ]

    print(f"\n🏷️  Need to check/create {len(required_labels)} labels...")
    print(f"📌 Using centralized tag_registry.py (single source of truth)")

    # Get existing labels
    print("\n📋 Checking existing labels...")
    existing_labels = list_labels(config)
    existing_titles = {label.get("title", "").lower() for label in existing_labels}

    print(f"✅ Found {len(existing_labels)} existing labels")

    # Create missing labels
    created_count = 0
    skipped_count = 0
    failed_count = 0

    print("\n🔨 Creating missing labels...")
    for label in required_labels:
        title = label["title"]

        if title.lower() in existing_titles:
            print(f"⏭️  {title:<40} (already exists)")
            skipped_count += 1
            continue

        if create_label(
            config,
            title,
            label["description"],
            label["color"],
            label.get("show_on_sidebar", False)
        ):
            sidebar_indicator = "📌" if label.get("show_on_sidebar") else "  "
            print(f"✅ {sidebar_indicator} {title:<40} (created)")
            created_count += 1
        else:
            print(f"❌    {title:<40} (failed)")
            failed_count += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Created: {created_count}")
    print(f"⏭️  Skipped: {skipped_count}")
    print(f"❌ Failed: {failed_count}")

    if failed_count == 0:
        print("\n🎉 All labels are ready!")
        return True
    else:
        print(f"\n⚠️  {failed_count} labels failed to create")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
