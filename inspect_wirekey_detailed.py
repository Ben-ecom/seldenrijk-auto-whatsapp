"""
Detailed inspection of wire:key elements to find the correct scraping structure.
"""
import asyncio
from playwright.async_api import async_playwright


async def inspect_wirekey():
    """Inspect wire:key elements in detail."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("📄 Navigating to Seldenrijk occasions page...")
        await page.goto("https://seldenrijk.nl/aanbod-occasions", wait_until="networkidle", timeout=30000)

        print("⏳ Waiting for Livewire...")
        await page.wait_for_selector("text=/voertuigen gevonden/i", timeout=20000)
        await page.wait_for_timeout(15000)

        # Find all wire:key elements
        elements = await page.query_selector_all('[wire\\:key]')
        print(f"\n✅ Found {len(elements)} wire:key elements\n")

        # Inspect first 3 vehicle cards in detail
        for i, elem in enumerate(elements[:3]):
            print(f"{'='*80}")
            print(f"VEHICLE CARD {i+1}")
            print(f"{'='*80}")

            # Get outer HTML (first 500 chars)
            outer_html = await elem.evaluate("el => el.outerHTML")
            print(f"Outer HTML (first 500 chars):\n{outer_html[:500]}...\n")

            # Get wire:key attribute
            wire_key = await elem.get_attribute("wire:key")
            print(f"wire:key = {wire_key}\n")

            # Find all links inside this element
            links = await elem.query_selector_all("a")
            print(f"Found {len(links)} links inside:")
            for j, link in enumerate(links[:3]):
                href = await link.get_attribute("href")
                text = await link.inner_text()
                text = text.strip()[:50]
                print(f"  Link {j+1}: {href} - '{text}...'")

            # Find all images inside this element
            images = await elem.query_selector_all("img")
            print(f"\nFound {len(images)} images:")
            for j, img in enumerate(images[:2]):
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                print(f"  Image {j+1}: alt='{alt}', src={src[:80]}...")

            # Find all text content
            text_content = await elem.inner_text()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            print(f"\nText content (first 10 lines):")
            for line in lines[:10]:
                print(f"  - {line}")

            # Check for specific classes
            classes = await elem.get_attribute("class")
            print(f"\nClasses: {classes}")

            print()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_wirekey())
