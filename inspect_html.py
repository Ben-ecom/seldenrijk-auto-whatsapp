"""
Inspect Seldenrijk HTML to find correct selectors for vehicle cards.
"""
import asyncio
from playwright.async_api import async_playwright


async def inspect_html():
    """Inspect the HTML structure."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("📄 Navigating to Seldenrijk occasions page...")
        await page.goto("https://seldenrijk.nl/aanbod-occasions", wait_until="networkidle", timeout=30000)

        print("⏳ Waiting for Livewire initial load...")
        await page.wait_for_selector("text=/voertuigen gevonden/i", timeout=20000)

        print("⏳ Waiting 15 seconds for vehicles to load...")
        await page.wait_for_timeout(15000)

        print("📜 Scrolling to load all content...")
        for _ in range(10):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await page.wait_for_timeout(500)

        # Get the HTML content
        html_content = await page.content()

        print(f"\n{'='*80}")
        print(f"HTML LENGTH: {len(html_content)} characters")
        print(f"'occasion' present: {'occasion' in html_content.lower()}")
        print(f"{'='*80}\n")

        # Test various selectors
        print("TESTING SELECTORS:")
        print("-" * 80)

        selectors = [
            'a[href*="/occasion/"]',
            'a[href^="/occasion"]',
            '.card',
            '.occasion-card',
            '[wire\\:key]',  # Livewire wire:key attribute
            '[x-data]',       # Alpine.js x-data attribute
            'div[class*="col"] a',  # Any div with col class containing links
            'a img',          # Links containing images (vehicle cards usually have images)
        ]

        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                print(f"\n{selector}")
                print(f"  Found: {len(elements)} elements")

                if elements and len(elements) > 0:
                    # Get first 3 sample URLs or content
                    for i, elem in enumerate(elements[:3]):
                        try:
                            tag_name = await elem.evaluate("el => el.tagName.toLowerCase()")

                            if tag_name == "a":
                                url = await elem.get_attribute("href")
                                text = await elem.inner_text()
                                text = text.strip()[:50]  # First 50 chars
                                print(f"    Sample {i+1}: {tag_name} - {url} - '{text}...'")
                            else:
                                outer_html = await elem.evaluate("el => el.outerHTML")
                                outer_html = outer_html[:100]  # First 100 chars
                                print(f"    Sample {i+1}: {tag_name} - {outer_html}...")
                        except Exception as e:
                            print(f"    Sample {i+1}: Error - {e}")
            except Exception as e:
                print(f"\n{selector}")
                print(f"  Error: {e}")

        print(f"\n{'='*80}")
        print("SEARCHING HTML FOR SPECIFIC PATTERNS:")
        print("-" * 80)

        # Search for specific patterns in HTML
        patterns = [
            ('href="/occasion/', 'Occasion links'),
            ('wire:key', 'Livewire keys'),
            ('x-data', 'Alpine.js data'),
            ('class="card', 'Card classes'),
        ]

        for pattern, description in patterns:
            count = html_content.count(pattern)
            print(f"{description}: {count} occurrences")

            if count > 0:
                # Find first occurrence and show context
                idx = html_content.find(pattern)
                context = html_content[max(0, idx-100):min(len(html_content), idx+200)]
                print(f"  First occurrence context: ...{context}...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_html())
