#!/usr/bin/env python3
"""
Generate secure secrets for webhook authentication.
Run this before deployment to generate all required secrets.
"""
import secrets

def generate_secret(length: int = 32) -> str:
    """Generate URL-safe secret."""
    return secrets.token_urlsafe(length)

def main():
    print("🔐 Generating Secure Secrets for WhatsApp Recruitment Platform\n")
    print("=" * 70)

    secrets_dict = {
        "CHATWOOT_WEBHOOK_SECRET": generate_secret(),
        "DIALOG360_WEBHOOK_SECRET": generate_secret(),
        "WHATSAPP_VERIFY_TOKEN": generate_secret(24),
    }

    print("\n📋 Add these to your .env file:\n")
    print("-" * 70)

    for key, value in secrets_dict.items():
        print(f"{key}={value}")

    print("-" * 70)
    print("\n✅ Secrets generated successfully!")
    print("\n⚠️  SECURITY WARNING:")
    print("   - Never commit these secrets to Git")
    print("   - Store them in Railway/Render environment variables")
    print("   - Keep a backup in a secure password manager\n")

if __name__ == "__main__":
    main()
