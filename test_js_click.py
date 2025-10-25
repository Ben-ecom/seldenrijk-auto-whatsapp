"""
Test clicking button using JavaScript evaluate (bypass visibility check).
"""
import asyncio
from playwright.async_api import async_playwright


async def test_js_click():
    """Test JS click."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("📄 Navigating...")
        await page.goto("https://seldenrijk.nl/aanbod-occasions", wait_until="networkidle", timeout=30000)
        await page.wait_for_selector("text=/voertuigen gevonden/i", timeout=20000)
        await page.wait_for_timeout(3000)

        # Count initial vehicles
        initial_count = len(await page.query_selector_all('[wire\\:key]'))
        print(f"✅ Initial: {initial_count} vehicles")

        # Find button with JavaScript
        print("\n🔘 Finding button with JavaScript...")
        button_exists = await page.evaluate("""() => {
            const button = document.querySelector('button.btn-primary:not([style*="display: none"])');
            if (button && button.textContent.includes('Toon')) {
                return {
                    exists: true,
                    text: button.textContent.trim(),
                    visible: button.offsetParent !== null
                };
            }
            return { exists: false };
        }""")

        print(f"Button status: {button_exists}")

        if button_exists.get('exists'):
            print(f"✅ Found: '{button_exists['text']}'")
            print(f"Visible: {button_exists['visible']}")

            # Click with JavaScript (bypasses visibility check)
            print("\n🔘 Clicking with JavaScript...")
            await page.evaluate("""() => {
                const buttons = document.querySelectorAll('button');
                for (const button of buttons) {
                    if (button.textContent.includes('Toon') && button.textContent.includes('resultaten')) {
                        button.click();
                        return true;
                    }
                }
                return false;
            }""")

            print("⏳ Waiting 20 seconds for Livewire to load all vehicles...")
            await page.wait_for_timeout(20000)

            # Count after click
            final_count = len(await page.query_selector_all('[wire\\:key]'))
            print(f"\n✅ After JS click: {final_count} vehicles")
            print(f"📊 Difference: +{final_count - initial_count}")

            if final_count >= 400:
                print("\n🎉 SUCCESS! All ~450 vehicles loaded!")
            else:
                print(f"\n⚠️ Only {final_count} vehicles (expected ~450)")

        else:
            print("❌ Button not found with JavaScript either")

        print("\n👀 Keeping browser open for 10 seconds...")
        await page.wait_for_timeout(10000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_js_click())
