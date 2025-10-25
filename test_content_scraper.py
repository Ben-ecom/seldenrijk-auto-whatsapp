"""
Test script for content scraper.
"""
import asyncio
import json
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.scrapers.content_scraper import ContentScraper


async def test_content_scraper():
    """Test content scraper."""
    print("🚀 Testing Seldenrijk Content Scraper\n")
    print("="*80)

    scraper = ContentScraper()

    # Scrape all content
    content = await scraper.scrape_all_content()

    print("\n" + "="*80)
    print("📊 SCRAPING RESULTS")
    print("="*80)

    # Company Info
    print("\n🏢 COMPANY INFO:")
    print(f"  Name: {content['company_info'].get('name')}")
    print(f"  Highlights: {len(content['company_info'].get('highlights', []))}")
    for highlight in content['company_info'].get('highlights', [])[:5]:
        print(f"    - {highlight}")

    # Team Members
    print(f"\n👥 TEAM MEMBERS: {len(content['team_members'])}")
    for member in content['team_members'][:5]:
        print(f"  - {member.get('name')} ({member.get('role')})")
        if member.get('image'):
            print(f"    Image: {member.get('image')[:50]}...")

    # Financing
    print(f"\n💰 FINANCING:")
    print(f"  Available: {content['financing'].get('available')}")
    print(f"  Options: {len(content['financing'].get('options', []))}")
    for option in content['financing'].get('options', [])[:3]:
        print(f"    - {option}")

    if content['financing'].get('partners'):
        print(f"  Partners: {', '.join(content['financing']['partners'][:3])}")

    # Contact
    print(f"\n📞 CONTACT INFO:")
    address = content['contact'].get('address', {})
    print(f"  Address: {address.get('street')}, {address.get('postal_code')} {address.get('city')}")
    print(f"  Phone: {content['contact'].get('phone')}")
    print(f"  Email: {content['contact'].get('email')}")
    print(f"  WhatsApp: {content['contact'].get('whatsapp')}")

    print(f"\n🕒 OPENING HOURS:")
    for day, hours in content['contact'].get('opening_hours', {}).items():
        print(f"  {day.capitalize()}: {hours}")

    # Save to file
    print(f"\n💾 Saving to content_data.json...")
    with open('content_data.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, indent=2, ensure_ascii=False)

    print("\n" + "="*80)
    print("✅ Content scraping test complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_content_scraper())
