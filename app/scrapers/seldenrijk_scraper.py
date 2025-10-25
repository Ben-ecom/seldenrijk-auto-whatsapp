"""
Seldenrijk Inventory Scraper.

Scrapes vehicle inventory from https://seldenrijk.nl using Playwright.
Saves directly to Supabase with embeddings for semantic search.
"""
import os
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from app.services.vector_store import get_vector_store
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


class SeldenrijkScraper:
    """
    Scraper for Seldenrijk occasions inventory.

    Features:
    - Async Playwright for JavaScript-rendered content
    - Robust error handling and retries
    - Structured data extraction
    - Progress logging
    """

    def __init__(self):
        """Initialize scraper."""
        self.base_url = "https://seldenrijk.nl"
        self.occasions_url = f"{self.base_url}/aanbod-occasions"
        self.headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

    async def scrape_inventory(self) -> List[Dict[str, Any]]:
        """
        Scrape complete vehicle inventory from Seldenrijk website using pagination.

        Seldenrijk.nl uses URL-based pagination (?page=N) with accumulative loading:
        - Page 1: 15 vehicles
        - Page 2: 30 vehicles (15 + 15)
        - Page 3: 45 vehicles (30 + 15)
        - Page 30: ~450 vehicles (all vehicles on one page)

        Strategy: Navigate directly to last page (?page=30) to load all vehicles at once.

        Returns:
            List of vehicle dictionaries with structured data

        Raises:
            Exception: If scraping fails after retries
        """
        logger.info("🚀 Starting Seldenrijk inventory scrape (pagination strategy)")

        vehicles = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                # Navigate to LAST page to load all vehicles at once (accumulative pagination)
                # 438 vehicles ÷ 15 per page = 29.2 pages → use page 30 to ensure all are loaded
                last_page_url = f"{self.occasions_url}?page=30"
                logger.info(f"📄 Navigating to last page: {last_page_url}")
                await page.goto(last_page_url, wait_until="networkidle", timeout=60000)

                # Wait for Livewire to load vehicle count text
                logger.info("⏳ Waiting for page to load completely...")
                await page.wait_for_selector("text=/voertuigen gevonden/i", timeout=20000)

                # Wait an additional 3 seconds for all vehicles to render
                await page.wait_for_timeout(3000)

                # Check vehicle count
                vehicle_count = len(await page.query_selector_all('[wire\\:key]'))
                logger.info(f"✅ Page loaded with {vehicle_count} vehicle cards")

                # Extract vehicle data
                vehicles = await self._extract_vehicles(page)

                await browser.close()

            logger.info(f"✅ Successfully scraped {len(vehicles)} vehicles using pagination strategy")

            # Save to Supabase with embeddings
            await self._save_to_supabase(vehicles)

            return vehicles

        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}", exc_info=True)
            raise

    async def _save_to_supabase(self, vehicles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save scraped vehicles to Supabase with embeddings.

        Args:
            vehicles: List of scraped vehicle dicts

        Returns:
            Save statistics dict
        """
        logger.info(f"💾 Saving {len(vehicles)} vehicles to Supabase...")

        vector_store = get_vector_store()

        saved_count = 0
        failed_count = 0

        for idx, vehicle in enumerate(vehicles, 1):
            try:
                await vector_store.upsert_vehicle(
                    external_id=vehicle["id"],
                    brand=vehicle["brand"],
                    model=vehicle["model"],
                    title=vehicle["title"],
                    price=vehicle["price"],
                    build_year=vehicle.get("buildYear"),
                    mileage=vehicle.get("mileage"),
                    fuel=vehicle.get("fuel"),
                    transmission=vehicle.get("transmission"),
                    url=vehicle["url"],
                    image_url=vehicle.get("image"),
                    available=vehicle.get("available", True)
                )

                saved_count += 1

                # Log progress every 50 vehicles
                if idx % 50 == 0:
                    logger.info(
                        f"📊 Supabase save progress: {idx}/{len(vehicles)} "
                        f"({saved_count} saved, {failed_count} failed)"
                    )

            except Exception as e:
                logger.error(f"❌ Failed to save vehicle {idx}: {e}")
                failed_count += 1

        logger.info(
            f"✅ Supabase save complete: {saved_count}/{len(vehicles)} vehicles saved"
        )

        return {
            "total": len(vehicles),
            "saved": saved_count,
            "failed": failed_count
        }

    async def _scroll_to_bottom(self, page: Page) -> None:
        """
        Scroll EXTREMELY aggressively to trigger Livewire infinite scroll loading.

        Livewire loads vehicles sporadically with VERY long gaps between batches.
        Scrolls 300 times with faster intervals to load ALL 450 vehicles.

        Strategy:
        - 300 scroll iterations (enough for 450 vehicles at 15 vehicles per batch)
        - 600ms wait between scrolls (faster but still reliable)
        - Larger scroll distance (1500px) to trigger more batches

        Args:
            page: Playwright page object
        """
        try:
            logger.info("📜 Starting ULTRA aggressive scroll to load ALL 450 vehicles...")

            previous_count = len(await page.query_selector_all('[wire\\:key]'))

            # CRITICAL: Scroll 300 times to ensure we load ALL 450 vehicles
            # Each batch loads ~15 vehicles, so 450 / 15 = 30 batches minimum
            # We scroll 300 times (10x batches) to account for long gaps
            for i in range(300):
                # Larger scroll distance (1500px) to trigger more loading
                await page.evaluate("window.scrollBy(0, 1500)")
                await page.wait_for_timeout(600)  # 600ms between scrolls (faster)

                current_count = len(await page.query_selector_all('[wire\\:key]'))

                # Log progress every 10 scrolls or when vehicles load
                if current_count > previous_count:
                    logger.info(f"  Scroll {i+1}/300: {current_count} vehicles (+{current_count - previous_count})")
                    previous_count = current_count
                elif (i + 1) % 50 == 0:
                    # Log every 50 scrolls even if no new vehicles
                    logger.debug(f"  Scroll {i+1}/300: {current_count} vehicles (no change)")

            final_count = len(await page.query_selector_all('[wire\\:key]'))
            logger.info(f"✅ Scroll complete: {final_count} total vehicles loaded (target: 450)")

            if final_count < 400:
                logger.warning(f"⚠️ Only {final_count}/450 vehicles loaded - website may have changed")

        except Exception as e:
            logger.warning(f"⚠️ Scrolling failed: {e}")

    async def _extract_vehicles(self, page: Page) -> List[Dict[str, Any]]:
        """
        Extract vehicle data from loaded page.

        Args:
            page: Playwright page object

        Returns:
            List of vehicle dictionaries
        """
        vehicles = []

        try:
            # Seldenrijk uses Livewire with wire:key attributes for vehicle cards
            selector = '[wire\\:key]'
            vehicle_elements = await page.query_selector_all(selector)

            if not vehicle_elements:
                logger.error("❌ No vehicle elements found with wire:key selector")
                return []

            logger.info(f"✅ Found {len(vehicle_elements)} vehicle cards (wire:key elements)")
            logger.info(f"📊 Processing {len(vehicle_elements)} vehicle elements")

            for idx, element in enumerate(vehicle_elements, 1):
                try:
                    vehicle = await self._parse_vehicle_card(element)

                    if vehicle:
                        vehicles.append(vehicle)
                        logger.debug(f"✅ Parsed vehicle {idx}/{len(vehicle_elements)}: {vehicle['brand']} {vehicle['model']}")

                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse vehicle {idx}: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Vehicle extraction failed: {e}", exc_info=True)

        return vehicles

    async def _parse_vehicle_card(self, element) -> Optional[Dict[str, Any]]:
        """
        Parse individual vehicle card element (wire:key Livewire element).

        Args:
            element: Playwright element locator (wire:key div)

        Returns:
            Vehicle data dictionary or None if parsing fails
        """
        try:
            # Extract vehicle ID from wire:key attribute
            vehicle_id = await element.get_attribute("wire:key")
            if not vehicle_id:
                logger.debug("⚠️ No wire:key attribute found")
                return None

            # Find first link inside element (vehicle detail page)
            link = await element.query_selector("a")
            url = await link.get_attribute("href") if link else None

            if not url:
                logger.debug(f"⚠️ No URL found for vehicle {vehicle_id}")
                return None

            # Make URL absolute
            if url.startswith("/"):
                url = f"{self.base_url}{url}"

            # Extract all text content and split into lines
            text_content = await element.inner_text()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]

            # Parse structured data from text lines
            # Line structure (from inspection):
            # Lines 0-4: Image slider numbers (1, 2, 3, 4, 5)
            # Line 5: Brand + Model (e.g., "Audi Q5")
            # Line 6: Full description
            # Line 7: Year (e.g., "2017")
            # Line 8: Mileage (e.g., "100.060 km")
            # Line 9: Transmission (e.g., "Automaat")
            # Line 10+: Price and other data

            # Skip slider numbers (first 5 lines)
            data_lines = [l for l in lines if not l.isdigit()]

            # Extract brand and model (first data line)
            brand_model = data_lines[0] if len(data_lines) > 0 else "Unknown"
            brand, model = self._parse_brand_model(brand_model)

            # Extract full description (second data line)
            description = data_lines[1] if len(data_lines) > 1 else ""

            # Extract year (third data line)
            year_text = data_lines[2] if len(data_lines) > 2 else None
            build_year = self._parse_year(year_text) if year_text else None

            # Extract mileage (fourth data line)
            mileage_text = data_lines[3] if len(data_lines) > 3 else "0"
            mileage = self._parse_mileage(mileage_text)

            # Extract transmission (fifth data line)
            transmission = data_lines[4] if len(data_lines) > 4 else None

            # Extract price (look for € symbol in remaining lines)
            price = 0
            for line in data_lines[5:]:
                if "€" in line:
                    price = self._parse_price(line)
                    break

            # Extract fuel type from description (common patterns)
            fuel = "Onbekend"
            fuel_keywords = ["Benzine", "Diesel", "Hybride", "Elektrisch", "HYbrid", "TFSI", "TDI", "HDI"]
            for keyword in fuel_keywords:
                if keyword.lower() in description.lower():
                    fuel = keyword
                    break

            # Extract image
            img_elem = await element.query_selector("img")
            image = await img_elem.get_attribute("src") if img_elem else None

            # Build vehicle data
            vehicle = {
                "id": vehicle_id,
                "brand": brand,
                "model": model,
                "title": brand_model,
                "price": price,
                "buildYear": build_year,
                "mileage": mileage,
                "fuel": fuel,
                "transmission": transmission,
                "url": url,
                "image": image,
                "available": True,
                "scraped_at": datetime.now().isoformat()
            }

            return vehicle

        except Exception as e:
            logger.warning(f"Failed to parse vehicle card: {e}", exc_info=True)
            return None

    def _extract_id_from_url(self, url: str) -> str:
        """Extract vehicle ID from URL."""
        # Example URL: https://seldenrijk.nl/occasion/bmw-x5-xdrive30e-12345
        # Extract last segment or hash
        parts = url.rstrip("/").split("/")
        return parts[-1] if parts else url

    def _parse_brand_model(self, title: str) -> tuple:
        """
        Parse brand and model from title string.

        Args:
            title: Vehicle title (e.g., "BMW X5 2021")

        Returns:
            Tuple of (brand, model)
        """
        # Common brands at Seldenrijk
        brands = [
            "BMW", "Mercedes-Benz", "Mercedes", "Audi", "Volkswagen", "VW",
            "Volvo", "SEAT", "Škoda", "Skoda", "MINI", "Ford", "Opel",
            "Peugeot", "Renault", "Toyota", "Lexus", "Mazda", "Kia",
            "Hyundai", "Nissan", "Land Rover", "Jaguar", "Porsche",
            "CUPRA", "Cupra", "Aston Martin", "Jeep", "Fiat", "Citroën",
            "Citroen", "Dacia", "Mitsubishi", "Suzuki", "Dodge", "MG",
            "Lynk & Co", "Polestar", "Aiways"
        ]

        title_upper = title.upper()

        # Find brand
        brand = "Unknown"
        for b in brands:
            if b.upper() in title_upper:
                brand = b
                break

        # Extract model (everything after brand, before year)
        model_part = title.replace(brand, "", 1).strip()

        # Remove year from model (4 consecutive digits)
        model_part = re.sub(r'\b\d{4}\b', '', model_part).strip()

        model = model_part if model_part else "Unknown"

        return brand, model

    def _parse_price(self, price_text: str) -> int:
        """
        Parse price from text.

        Args:
            price_text: Price string (e.g., "€ 42.500", "42500")

        Returns:
            Price as integer
        """
        try:
            # Remove € symbol, spaces, dots
            price_clean = re.sub(r'[€\s.]', '', price_text)
            # Remove any non-digit characters except comma
            price_clean = re.sub(r'[^\d,]', '', price_clean)
            # Replace comma with empty (European format)
            price_clean = price_clean.replace(',', '')

            return int(price_clean) if price_clean else 0

        except Exception:
            return 0

    def _parse_mileage(self, mileage_text: str) -> int:
        """
        Parse mileage from text.

        Args:
            mileage_text: Mileage string (e.g., "45.000 km", "45000")

        Returns:
            Mileage as integer
        """
        try:
            # Remove km, spaces, dots
            mileage_clean = re.sub(r'[km\s.]', '', mileage_text.lower())
            # Remove any non-digit characters
            mileage_clean = re.sub(r'\D', '', mileage_clean)

            return int(mileage_clean) if mileage_clean else 0

        except Exception:
            return 0

    def _parse_year(self, year_text: str) -> Optional[int]:
        """
        Parse build year from text.

        Args:
            year_text: Year string (e.g., "2021", "Bouwjaar 2021")

        Returns:
            Year as integer or None
        """
        try:
            # Extract 4-digit year
            match = re.search(r'\b(19|20)\d{2}\b', year_text)
            return int(match.group()) if match else None

        except Exception:
            return None


# Singleton instance
_scraper = None


def get_scraper() -> SeldenrijkScraper:
    """Get singleton scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = SeldenrijkScraper()
    return _scraper
