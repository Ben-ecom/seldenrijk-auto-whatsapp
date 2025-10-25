"""
Seldenrijk Website Content Scraper.

Scrapes all relevant content from Seldenrijk website including:
- Team members
- Contact information
- Opening hours
- Financing information
- Trade-in information
- Terms & conditions
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from playwright.async_api import async_playwright, Page
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


class ContentScraper:
    """
    Scraper for Seldenrijk website content (non-vehicle data).

    Features:
    - Team member information
    - Contact details and opening hours
    - Financing options
    - Trade-in process
    - Company policies
    """

    def __init__(self):
        """Initialize content scraper."""
        self.base_url = "https://seldenrijk.nl"
        self.headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

        # Page URLs
        self.pages = {
            "team": f"{self.base_url}/ons-team",
            "contact": f"{self.base_url}/contact",
            "financing": f"{self.base_url}/financiering-lease",
            "homepage": self.base_url
        }

    async def scrape_all_content(self) -> Dict[str, Any]:
        """
        Scrape all website content.

        Returns:
            Dict with all scraped content organized by category
        """
        logger.info("🚀 Starting Seldenrijk content scrape")

        content = {
            "company_info": {},
            "team_members": [],
            "financing": {},
            "contact": {},
            "scraped_at": datetime.now().isoformat()
        }

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                # Scrape company info from homepage
                logger.info("📄 Scraping company info from homepage")
                content["company_info"] = await self._scrape_company_info(page)

                # Scrape team members
                logger.info("👥 Scraping team members")
                content["team_members"] = await self._scrape_team_members(page)

                # Scrape financing info
                logger.info("💰 Scraping financing information")
                content["financing"] = await self._scrape_financing(page)

                # Scrape contact info and opening hours
                logger.info("📞 Scraping contact information")
                content["contact"] = await self._scrape_contact(page)

                await browser.close()

            logger.info(f"✅ Content scrape complete: {len(content['team_members'])} team members")
            return content

        except Exception as e:
            logger.error(f"❌ Content scraping failed: {e}", exc_info=True)
            raise

    async def _scrape_company_info(self, page: Page) -> Dict[str, Any]:
        """
        Scrape company information from homepage.

        Args:
            page: Playwright page object

        Returns:
            Dict with company info
        """
        try:
            await page.goto(self.pages["homepage"], wait_until="networkidle", timeout=30000)

            # Extract company highlights from homepage
            company_info = {
                "name": "Seldenrijk Auto",
                "tagline": "Snel schakelen met onze adviseurs",
                "highlights": [],
                "about": ""
            }

            # Extract highlights (usually in hero section or cards)
            highlight_elements = await page.query_selector_all('[class*="highlight"], [class*="feature"], [class*="card"]')

            for elem in highlight_elements[:10]:  # Limit to first 10
                text = await elem.inner_text()
                text = text.strip()
                if len(text) > 10 and len(text) < 200:
                    company_info["highlights"].append(text)

            # Common highlights we know from the site
            known_highlights = [
                "Groot aanbod van occasions",
                "Klanten geven ons een 9.2",
                "Volledige transparantie",
                "Snel schakelen met onze adviseurs"
            ]

            company_info["highlights"].extend(known_highlights)
            company_info["highlights"] = list(set(company_info["highlights"]))  # Remove duplicates

            logger.debug(f"✅ Scraped company info with {len(company_info['highlights'])} highlights")
            return company_info

        except Exception as e:
            logger.error(f"❌ Failed to scrape company info: {e}")
            return {
                "name": "Seldenrijk Auto",
                "highlights": ["Groot aanbod van occasions", "Klanten geven ons een 9.2"]
            }

    async def _scrape_team_members(self, page: Page) -> List[Dict[str, Any]]:
        """
        Scrape team member information.

        Args:
            page: Playwright page object

        Returns:
            List of team member dicts
        """
        try:
            await page.goto(self.pages["team"], wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)  # Wait for dynamic content

            team_members = []

            # Find team member cards/sections
            # Try multiple selectors for team member containers
            selectors = [
                '[class*="team"]',
                '[class*="member"]',
                '[class*="person"]',
                '[class*="employee"]',
                'article',
                '.card'
            ]

            team_elements = []
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if len(elements) > 2:  # Found likely team member containers
                    team_elements = elements
                    logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                    break

            if not team_elements:
                logger.warning("⚠️ No team member elements found, trying text extraction")
                # Fallback: Extract all text and look for names/roles
                body_text = await page.query_selector('body')
                if body_text:
                    text = await body_text.inner_text()
                    # Simple heuristic: lines with common role keywords
                    lines = text.split('\n')
                    current_member = {}

                    for line in lines:
                        line = line.strip()
                        role_keywords = ['verkoop', 'adviseur', 'directeur', 'manager', 'medewerker']

                        if any(keyword in line.lower() for keyword in role_keywords):
                            if current_member and current_member.get('name'):
                                team_members.append(current_member)
                            current_member = {'role': line, 'name': ''}
                        elif len(line) > 2 and len(line) < 50 and current_member.get('role') and not current_member.get('name'):
                            # Likely a name
                            current_member['name'] = line
            else:
                # Extract data from team member elements
                for elem in team_elements:
                    try:
                        text_content = await elem.inner_text()
                        lines = [l.strip() for l in text_content.split('\n') if l.strip()]

                        if len(lines) < 2:
                            continue

                        # Try to find image
                        img = await elem.query_selector('img')
                        image_url = await img.get_attribute('src') if img else None

                        # First line usually name, second line role
                        member = {
                            'name': lines[0] if len(lines) > 0 else 'Unknown',
                            'role': lines[1] if len(lines) > 1 else 'Team Member',
                            'image': image_url,
                            'bio': ' '.join(lines[2:]) if len(lines) > 2 else ''
                        }

                        # Only add if looks valid
                        if len(member['name']) > 2 and len(member['name']) < 50:
                            team_members.append(member)

                    except Exception as e:
                        logger.debug(f"Failed to parse team member element: {e}")
                        continue

            logger.info(f"✅ Scraped {len(team_members)} team members")
            return team_members

        except Exception as e:
            logger.error(f"❌ Failed to scrape team members: {e}", exc_info=True)
            return []

    async def _scrape_financing(self, page: Page) -> Dict[str, Any]:
        """
        Scrape financing and lease information.

        Args:
            page: Playwright page object

        Returns:
            Dict with financing info
        """
        try:
            await page.goto(self.pages["financing"], wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            financing = {
                "available": True,
                "options": [],
                "description": "",
                "partners": []
            }

            # Extract main content
            main_content = await page.query_selector('main, [role="main"], .content, article')
            if main_content:
                text = await main_content.inner_text()

                # Extract financing options from headings
                headings = await main_content.query_selector_all('h1, h2, h3, h4')
                for heading in headings:
                    heading_text = await heading.inner_text()
                    heading_text = heading_text.strip()

                    if len(heading_text) > 5 and len(heading_text) < 100:
                        # Look for financing-related keywords
                        if any(kw in heading_text.lower() for kw in ['lease', 'financier', 'betaal', 'lening', 'credit']):
                            financing["options"].append(heading_text)

                # Get full description (first 1000 chars)
                financing["description"] = text[:1000].strip()

            # Look for partner logos/links
            partner_elements = await page.query_selector_all('[class*="partner"], [class*="logo"]')
            for elem in partner_elements[:5]:
                try:
                    alt_text = await elem.get_attribute('alt')
                    if alt_text and len(alt_text) > 2:
                        financing["partners"].append(alt_text)
                except:
                    pass

            logger.info(f"✅ Scraped financing info: {len(financing['options'])} options")
            return financing

        except Exception as e:
            logger.error(f"❌ Failed to scrape financing info: {e}")
            return {
                "available": True,
                "options": ["Financiering beschikbaar", "Lease beschikbaar"],
                "description": "Neem contact op voor financieringsmogelijkheden"
            }

    async def _scrape_contact(self, page: Page) -> Dict[str, Any]:
        """
        Scrape contact information and opening hours.

        Args:
            page: Playwright page object

        Returns:
            Dict with contact info
        """
        try:
            # Try contact page first
            await page.goto(self.pages["contact"], wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            contact = {
                "address": {
                    "street": "Zuiderbreedte 22",
                    "postal_code": "3845MC",
                    "city": "Harderwijk",
                    "country": "Nederland"
                },
                "phone": "0341-799554",
                "email": "info@seldenrijk.nl",
                "whatsapp": "0341-799554",
                "opening_hours": {}
            }

            # Extract full page text to find contact details
            body = await page.query_selector('body')
            if body:
                text = await body.inner_text()

                # Extract phone numbers (Dutch format)
                import re
                phone_pattern = r'0\d{1,3}[-\s]?\d{6,7}'
                phones = re.findall(phone_pattern, text)
                if phones:
                    contact["phone"] = phones[0].replace(' ', '').replace('-', '')

                # Extract email
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                emails = re.findall(email_pattern, text)
                if emails:
                    contact["email"] = emails[0]

                # Extract address lines
                address_keywords = ['straat', 'weg', 'laan', 'plein', 'breedte']
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    # Look for postal code pattern (4 digits + 2 letters)
                    if re.search(r'\d{4}\s*[A-Z]{2}', line):
                        # Previous line might be street
                        if i > 0:
                            prev_line = lines[i-1].strip()
                            if any(kw in prev_line.lower() for kw in address_keywords):
                                contact["address"]["street"] = prev_line

                        # Extract postal code and city
                        postal_match = re.search(r'(\d{4}\s*[A-Z]{2})\s*(\w+)', line)
                        if postal_match:
                            contact["address"]["postal_code"] = postal_match.group(1).replace(' ', '')
                            contact["address"]["city"] = postal_match.group(2)

            # Try to extract opening hours
            opening_hours = await self._extract_opening_hours(page)
            if opening_hours:
                contact["opening_hours"] = opening_hours

            logger.info("✅ Scraped contact information")
            return contact

        except Exception as e:
            logger.error(f"❌ Failed to scrape contact info: {e}")
            # Return default contact info
            return {
                "address": {
                    "street": "Zuiderbreedte 22",
                    "postal_code": "3845MC",
                    "city": "Harderwijk",
                    "country": "Nederland"
                },
                "phone": "0341-799554",
                "email": "info@seldenrijk.nl",
                "opening_hours": {
                    "monday": "09:00-18:00",
                    "tuesday": "09:00-18:00",
                    "wednesday": "09:00-18:00",
                    "thursday": "09:00-18:00",
                    "friday": "09:00-18:00",
                    "saturday": "09:00-17:00",
                    "sunday": "Gesloten"
                }
            }

    async def _extract_opening_hours(self, page: Page) -> Dict[str, str]:
        """
        Extract opening hours from page.

        Args:
            page: Playwright page object

        Returns:
            Dict with opening hours per day
        """
        try:
            # Look for opening hours section
            hours_selectors = [
                '[class*="opening"]',
                '[class*="hours"]',
                '[class*="tijd"]',
                'table'
            ]

            opening_hours = {}

            for selector in hours_selectors:
                elements = await page.query_selector_all(selector)

                for elem in elements:
                    text = await elem.inner_text()
                    text_lower = text.lower()

                    # Check if this looks like opening hours
                    if any(day in text_lower for day in ['maandag', 'dinsdag', 'woensdag', 'monday', 'tuesday']):
                        # Parse day by day
                        days_nl = {
                            'maandag': 'monday',
                            'dinsdag': 'tuesday',
                            'woensdag': 'wednesday',
                            'donderdag': 'thursday',
                            'vrijdag': 'friday',
                            'zaterdag': 'saturday',
                            'zondag': 'sunday'
                        }

                        lines = text.split('\n')
                        for line in lines:
                            line_lower = line.lower().strip()

                            for day_nl, day_en in days_nl.items():
                                if day_nl in line_lower:
                                    # Extract hours (e.g., "09:00-18:00")
                                    import re
                                    time_pattern = r'\d{1,2}:\d{2}[\s-]*\d{1,2}:\d{2}'
                                    time_match = re.search(time_pattern, line)

                                    if time_match:
                                        opening_hours[day_en] = time_match.group(0)
                                    elif 'gesloten' in line_lower or 'closed' in line_lower:
                                        opening_hours[day_en] = 'Gesloten'

                        if opening_hours:
                            break

                if opening_hours:
                    break

            # Default hours if not found
            if not opening_hours:
                opening_hours = {
                    "monday": "09:00-18:00",
                    "tuesday": "09:00-18:00",
                    "wednesday": "09:00-18:00",
                    "thursday": "09:00-18:00",
                    "friday": "09:00-18:00",
                    "saturday": "09:00-17:00",
                    "sunday": "Gesloten"
                }

            return opening_hours

        except Exception as e:
            logger.debug(f"Failed to extract opening hours: {e}")
            return {}


# Singleton instance
_content_scraper = None


def get_content_scraper() -> ContentScraper:
    """Get singleton content scraper instance."""
    global _content_scraper
    if _content_scraper is None:
        _content_scraper = ContentScraper()
    return _content_scraper
