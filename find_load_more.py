"""
Find the 'Load More' button or infinite scroll trigger.
"""
import asyncio
from playwright.async_api import async_playwright


async def find_load_more():
    """Find load more mechanism."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("📄 Navigating...")
        await page.goto("https://seldenrijk.nl/aanbod-occasions", wait_until="networkidle")
        await page.wait_for_selector("text=/voertuigen gevonden/i", timeout=20000)
        await page.wait_for_timeout(5000)

        # Look for "Load More" or "Toon meer" buttons
        print("\n🔍 Searching for 'Load More' buttons...")

        load_more_selectors = [
            'button:has-text("meer")',
            'button:has-text("Meer")',
            'button:has-text("Load")',
            'button:has-text("Laad")',
            'button:has-text("Toon")',
            '[wire\\:click*="load"]',
            '[wire\\:click*="more"]',
            '[x-on\\:click*="load"]',
            'button[class*="load"]',
            'button[class*="more"]'
        ]

        for selector in load_more_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                print(f"✅ Found {len(elements)} elements with selector: {selector}")
                for i, elem in enumerate(elements):
                    text = await elem.inner_text()
                    print(f"   Button {i+1}: '{text}'")

        # Check for Livewire wire:model or wire:click attributes
        print("\n🔍 Checking for Livewire scroll triggers...")
        html = await page.content()

        if 'wire:init' in html:
            print("✅ Found wire:init")
        if 'x-intersect' in html:
            print("✅ Found x-intersect (infinite scroll trigger)")
        if '@scroll' in html:
            print("✅ Found @scroll event")

        # Scroll down and check for new vehicles loading
        print("\n🔄 Testing scroll behavior...")
        initial_count = len(await page.query_selector_all('[wire\\:key]'))
        print(f"Initial: {initial_count} vehicles")

        # Scroll to bottom and wait
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        print("Scrolled to bottom, waiting 5 seconds...")
        await page.wait_for_timeout(5000)

        after_scroll = len(await page.query_selector_all('[wire\\:key]'))
        print(f"After scroll: {after_scroll} vehicles")

        if after_scroll > initial_count:
            print("✅ Infinite scroll IS working!")
        else:
            print("❌ Infinite scroll NOT triggered automatically")

        # Keep browser open
        print("\n👀 Keeping browser open for inspection (30 seconds)...")
        await page.wait_for_timeout(30000)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(find_load_more())
