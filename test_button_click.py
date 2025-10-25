"""
Test script to verify clicking 'Toon resultaten' button loads all vehicles.
"""
import asyncio
from playwright.async_api import async_playwright


async def test_button_click():
    """Test clicking the button and counting vehicles."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("📄 Navigating to Seldenrijk occasions page...")
        await page.goto("https://seldenrijk.nl/aanbod-occasions", wait_until="networkidle", timeout=30000)

        print("⏳ Waiting for initial Livewire load...")
        await page.wait_for_selector("text=/voertuigen gevonden/i", timeout=20000)

        # Count initial vehicles
        initial_count = len(await page.query_selector_all('[wire\\:key]'))
        print(f"✅ Initial load: {initial_count} vehicles")

        # Find and click the button
        print("\n🔘 Looking for 'Toon resultaten' button...")
        show_all_button = await page.query_selector('button:has-text("Toon")')

        if show_all_button:
            button_text = await show_all_button.inner_text()
            print(f"✅ Found button: '{button_text.strip()}'")

            # Click the button
            await show_all_button.click()
            print("🔘 Clicked button!")

            # Wait for vehicles to load
            print("⏳ Waiting 20 seconds for ALL vehicles to load...")
            await page.wait_for_timeout(20000)

            # Count vehicles after clicking
            final_count = len(await page.query_selector_all('[wire\\:key]'))
            print(f"\n✅ After clicking: {final_count} vehicles")
            print(f"📊 Difference: +{final_count - initial_count} vehicles")

            if final_count >= 400:
                print("\n🎉 SUCCESS! All ~450 vehicles loaded!")
            else:
                print(f"\n⚠️ Only {final_count} vehicles loaded (expected ~450)")

        else:
            print("❌ Button not found!")

        # Keep browser open to verify
        print("\n👀 Keeping browser open for 10 seconds...")
        await page.wait_for_timeout(10000)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_button_click())
