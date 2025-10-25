"""
Inspect the 'Toon resultaten' button to understand why it's not clickable.
"""
import asyncio
from playwright.async_api import async_playwright


async def inspect_button():
    """Inspect button properties."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("📄 Navigating...")
        await page.goto("https://seldenrijk.nl/aanbod-occasions", wait_until="networkidle", timeout=30000)
        await page.wait_for_selector("text=/voertuigen gevonden/i", timeout=20000)
        await page.wait_for_timeout(3000)

        # Find button
        buttons = await page.query_selector_all('button:has-text("Toon")')
        print(f"\n✅ Found {len(buttons)} buttons with 'Toon' text\n")

        for i, button in enumerate(buttons):
            print(f"Button {i+1}:")
            text = await button.inner_text()
            print(f"  Text: '{text.strip()}'")

            # Check visibility
            is_visible = await button.is_visible()
            print(f"  Visible: {is_visible}")

            # Check if hidden
            is_hidden = await button.is_hidden()
            print(f"  Hidden: {is_hidden}")

            # Get bounding box (position)
            box = await button.bounding_box()
            if box:
                print(f"  Position: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
            else:
                print(f"  Position: No bounding box (not in viewport)")

            # Get classes
            classes = await button.get_attribute("class")
            print(f"  Classes: {classes}")

            # Try to scroll into view
            if not is_visible:
                print("  🔄 Trying to scroll into view...")
                await button.scroll_into_view_if_needed()
                await page.wait_for_timeout(1000)

                is_visible_after_scroll = await button.is_visible()
                print(f"  Visible after scroll: {is_visible_after_scroll}")

                if is_visible_after_scroll:
                    print("  ✅ Button is now visible - trying click with force...")
                    try:
                        await button.click(force=True)
                        print("  ✅ Click succeeded!")

                        await page.wait_for_timeout(20000)
                        vehicle_count = len(await page.query_selector_all('[wire\\:key]'))
                        print(f"\n🎉 Vehicles after click: {vehicle_count}")
                    except Exception as e:
                        print(f"  ❌ Click failed: {e}")

            print()

        # Keep browser open
        print("\n👀 Keeping browser open for 30 seconds...")
        await page.wait_for_timeout(30000)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_button())
