"""
RAG Agent - Real-time inventory search using Playwright MCP.

Uses Playwright to:
- Search Marktplaats for dealer listings
- Search Seldenrijk website for inventory
- Extract structured car data
- Filter based on customer preferences
- Cache results for 10 minutes

Phase 1: Marktplaats scraping (implemented)
Phase 2: Website scraping (TODO)
Phase 3: Advanced features (TODO)
"""
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.agents.base import BaseAgent
from app.config.agents_config import AGENT_CONFIGS
from app.orchestration.state import ConversationState
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


class RAGAgent(BaseAgent):
    """
    RAG Agent for real-time car inventory scraping.

    Scrapes:
    - Marktplaats dealer profile (Phase 1)
    - Seldenrijk website (Phase 2)

    Features:
    - Dual-source scraping
    - 10-minute result caching
    - Intelligent ranking
    - Error fallback
    """

    def __init__(self):
        """Initialize RAG Agent."""
        # Use same config as router agent (fast, simple agent)
        config = AGENT_CONFIGS["router"]

        super().__init__(
            agent_name="rag",
            model=config["model"],
            max_retries=config["max_retries"],
            timeout_seconds=config["timeout_seconds"]
        )

        # Cache for scraped results (in-memory for now)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_duration = 600  # 10 minutes

        logger.info("✅ RAG Agent initialized for car inventory scraping")

    def _execute(self, state: ConversationState) -> Dict[str, Any]:
        """
        Execute RAG agent to search for cars in real-time.

        Args:
            state: Current conversation state

        Returns:
            Dict with rag_results and metadata
        """
        # Extract customer criteria
        extraction = state.get("extraction_output", {})
        car_prefs = extraction.get("car_preferences", {})

        make = car_prefs.get("make", "")
        model = car_prefs.get("model", "")
        fuel_type = car_prefs.get("fuel_type", "")
        max_price = car_prefs.get("max_price")
        preferred_color = car_prefs.get("preferred_color", "")
        max_mileage = car_prefs.get("max_mileage")

        logger.info(
            "🔍 RAG search initiated",
            extra={
                "message_id": state["message_id"],
                "make": make,
                "model": model,
                "fuel_type": fuel_type,
                "max_price": max_price
            }
        )

        # Build cache key
        cache_key = f"{make}_{model}_{fuel_type}_{max_price}"

        # Check cache first
        cached_results = self._get_from_cache(cache_key)
        if cached_results:
            logger.info(
                "💾 Using cached results",
                extra={"cache_key": cache_key, "results_count": len(cached_results)}
            )
            return {
                "rag_results": cached_results[:3],  # Top 3
                "total_found": len(cached_results),
                "cache_hit": True
            }

        # Store state for access in search method
        self.state = state

        # Phase 1: Search Supabase vector store (PRIMARY SOURCE)
        import asyncio
        redis_results = asyncio.run(self._search_redis_inventory(make, model, fuel_type))

        # Phase 2: Search Marktplaats (FALLBACK if Supabase has no results)
        marktplaats_results = []
        if not redis_results:
            logger.info("No results in Supabase, falling back to Marktplaats")
            marktplaats_results = self._search_marktplaats(make, model, fuel_type)

        # Combine results (Redis takes priority)
        all_results = redis_results + marktplaats_results

        # Filter by criteria
        filtered_results = self._filter_by_criteria(
            all_results,
            max_price=max_price,
            fuel_type=fuel_type,
            preferred_color=preferred_color,
            max_mileage=max_mileage
        )

        # Rank results
        ranked_results = self._rank_results(filtered_results, car_prefs)

        # Cache results
        self._cache_results(cache_key, ranked_results)

        logger.info(
            "✅ RAG search complete",
            extra={
                "total_found": len(all_results),
                "filtered": len(filtered_results),
                "top_results": len(ranked_results[:3])
            }
        )

        return {
            "rag_results": ranked_results[:3],  # Top 3 matches
            "total_found": len(all_results),
            "filtered_count": len(filtered_results),
            "cache_hit": False
        }

    async def _search_redis_inventory(
        self,
        make: str,
        model: str,
        fuel_type: str
    ) -> List[Dict[str, Any]]:
        """
        Search Supabase vector store for cars matching criteria.

        Uses semantic similarity search with filters for precise matches.

        Args:
            make: Car make (e.g., "Audi")
            model: Car model (e.g., "Q5")
            fuel_type: Fuel type (e.g., "diesel")

        Returns:
            List of car dicts from Supabase vector store
        """
        try:
            from app.services.vector_store import get_vector_store

            vector_store = get_vector_store()

            # Build semantic search query
            query_parts = []
            if make:
                query_parts.append(make)
            if model:
                query_parts.append(model)
            if fuel_type:
                query_parts.append(fuel_type)

            query = " ".join(query_parts) if query_parts else "auto"

            # Extract car preferences from state for filtering
            extraction = self.state.get("extraction_output", {}) if hasattr(self, 'state') else {}
            car_prefs = extraction.get("car_preferences", {})

            max_price = car_prefs.get("max_price")
            max_mileage = car_prefs.get("max_mileage")
            min_year = car_prefs.get("min_year")

            logger.info(
                f"🔍 Supabase vector search: '{query}'",
                extra={
                    "make": make,
                    "model": model,
                    "fuel_type": fuel_type,
                    "max_price": max_price,
                    "max_mileage": max_mileage,
                    "min_year": min_year
                }
            )

            # Perform semantic search with filters
            vehicles = await vector_store.search_vehicles(
                query=query,
                max_price=max_price,
                fuel_type=fuel_type,
                max_mileage=max_mileage,
                min_year=min_year,
                match_threshold=0.7,  # 70% similarity
                match_count=10  # Get more results for ranking
            )

            # Convert to standard format
            results = []
            for vehicle in vehicles:
                results.append({
                    "source": "seldenrijk_website",
                    "dealer": "Seldenrijk B.V.",
                    "location": "Harderwijk",
                    "make": vehicle.get("brand"),
                    "model": vehicle.get("model"),
                    "full_title": vehicle.get("title"),
                    "year": vehicle.get("build_year"),
                    "mileage": vehicle.get("mileage"),
                    "fuel_type": vehicle.get("fuel", "").lower(),
                    "transmission": vehicle.get("transmission"),
                    "price": vehicle.get("price"),
                    "url": vehicle.get("url"),
                    "image": vehicle.get("image_url"),
                    "available": vehicle.get("available", True),
                    "similarity": vehicle.get("similarity", 0.0)  # Semantic similarity score
                })

            logger.info(f"✅ Supabase vector search complete: {len(results)} matching vehicles")
            return results

        except Exception as e:
            logger.error(f"❌ Supabase vector search failed: {e}", exc_info=True)
            return []

    def _search_marktplaats(
        self,
        make: str,
        model: str,
        fuel_type: str
    ) -> List[Dict[str, Any]]:
        """
        Search Marktplaats dealer profile for cars.

        Args:
            make: Car make (e.g., "Volkswagen")
            model: Car model (e.g., "Golf 8")
            fuel_type: Fuel type (e.g., "diesel")

        Returns:
            List of car dicts
        """
        try:
            # Import Playwright MCP tools
            from app.utils.playwright_helper import (
                navigate,
                get_visible_text,
                close_browser
            )

            # Build search URL
            dealer_url = "https://www.marktplaats.nl/u/seldenrijk-bv/10866554/"

            # Add search query if make/model specified
            if make or model:
                search_term = f"{make} {model}".strip()
                search_url = f"{dealer_url}?query={search_term.replace(' ', '+')}"
            else:
                search_url = dealer_url

            logger.info(f"🔵 Scraping Marktplaats: {search_url}")

            # Navigate to page
            navigate(search_url)

            # Get visible text
            content = get_visible_text()

            # Parse listings
            listings = self._parse_marktplaats_listings(content)

            # Close browser
            close_browser()

            logger.info(f"✅ Found {len(listings)} listings on Marktplaats")

            return listings

        except Exception as e:
            logger.error(
                f"❌ Marktplaats scraping failed: {e}",
                exc_info=True
            )
            return []  # Return empty list on error

    def _parse_marktplaats_listings(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse Marktplaats listings from visible text.

        Expected pattern:
        [Make] [Model] [Specs] | [Features]
        [Description in lowercase]
        [Year]
        [Mileage] km
        € [Price],-
        [Date]

        Args:
            content: Visible text from page

        Returns:
            List of parsed car dicts
        """
        listings = []

        # Split content into lines
        lines = content.split("\n")

        # Find car listings (start with make + model)
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this looks like a car title
            # (contains make and price pattern nearby)
            if self._looks_like_car_title(line):
                # Try to extract full listing
                listing = self._extract_marktplaats_listing(lines, i)
                if listing:
                    listings.append(listing)
                    i += 10  # Skip ahead (listings are ~10 lines each)
                else:
                    i += 1
            else:
                i += 1

        return listings

    def _looks_like_car_title(self, line: str) -> bool:
        """
        Check if line looks like a car listing title.

        Args:
            line: Text line

        Returns:
            True if looks like car title
        """
        # Common car makes in inventory
        makes = [
            "volkswagen", "vw", "golf", "passat", "tiguan",
            "bmw", "mercedes", "audi", "skoda", "seat",
            "cupra", "ford", "toyota", "renault", "volvo",
            "kia", "hyundai", "mazda", "peugeot", "opel"
        ]

        line_lower = line.lower()

        # Check if line contains any make
        return any(make in line_lower for make in makes)

    def _extract_marktplaats_listing(
        self,
        lines: List[str],
        start_idx: int
    ) -> Optional[Dict[str, Any]]:
        """
        Extract single car listing from lines.

        Args:
            lines: All lines from page
            start_idx: Index of title line

        Returns:
            Car dict or None
        """
        try:
            # Get next 15 lines for this listing
            listing_lines = lines[start_idx:start_idx + 15]

            # Initialize car data
            car = {
                "source": "marktplaats",
                "dealer": "Seldenrijk B.V.",
                "location": "Harderwijk"
            }

            # Extract title (first line)
            car["full_title"] = listing_lines[0].strip()

            # Extract make and model from title
            title_parts = car["full_title"].split()
            if len(title_parts) >= 2:
                car["make"] = title_parts[0]
                car["model"] = title_parts[1]

            # Look for year (4-digit number)
            for line in listing_lines:
                year_match = re.search(r"\b(20\d{2})\b", line)
                if year_match:
                    car["year"] = int(year_match.group(1))
                    break

            # Look for mileage (number + "km")
            for line in listing_lines:
                mileage_match = re.search(r"([\d.]+)\s*km", line)
                if mileage_match:
                    mileage_str = mileage_match.group(1).replace(".", "")
                    car["mileage"] = int(mileage_str)
                    break

            # Look for price (€ X.XXX,-)
            for line in listing_lines:
                price_match = re.search(r"€\s*([\d.]+),-", line)
                if price_match:
                    price_str = price_match.group(1).replace(".", "")
                    car["price"] = int(price_str)
                    break

            # Look for date posted
            for line in listing_lines:
                if "Vandaag" in line:
                    car["date_posted"] = "Vandaag"
                    break
                elif "Gisteren" in line:
                    car["date_posted"] = "Gisteren"
                    break

            # Check for quality indicators
            full_text = " ".join(listing_lines)
            car["nap_verified"] = "NAP gecontroleerd" in full_text
            car["service_book"] = "Onderhoudsboekje" in full_text
            car["financing_available"] = "Financiering mogelijk" in full_text
            car["featured"] = "Dagtopper" in full_text

            # Detect fuel type from title
            title_lower = car["full_title"].lower()
            if "diesel" in title_lower or "tdi" in title_lower:
                car["fuel_type"] = "diesel"
            elif "hybr" in title_lower or "phev" in title_lower:
                car["fuel_type"] = "hybride"
            elif "elektr" in title_lower or "ev" in title_lower or "e-tron" in title_lower:
                car["fuel_type"] = "elektrisch"
            elif "tsi" in title_lower or "benzine" in title_lower:
                car["fuel_type"] = "benzine"
            else:
                car["fuel_type"] = "onbekend"

            # Require minimum fields
            if "year" in car and "price" in car:
                return car
            else:
                return None

        except Exception as e:
            logger.warning(f"Failed to parse listing: {e}")
            return None

    def _filter_by_criteria(
        self,
        results: List[Dict[str, Any]],
        max_price: Optional[float] = None,
        fuel_type: Optional[str] = None,
        preferred_color: Optional[str] = None,
        max_mileage: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter results based on customer criteria.

        Args:
            results: Raw search results
            max_price: Maximum price
            fuel_type: Desired fuel type
            preferred_color: Preferred color
            max_mileage: Maximum mileage

        Returns:
            Filtered results
        """
        filtered = []

        for car in results:
            # Filter by price
            if max_price and car.get("price", float('inf')) > max_price:
                continue

            # Filter by fuel type
            if fuel_type and car.get("fuel_type", "").lower() != fuel_type.lower():
                continue

            # Filter by mileage
            if max_mileage and car.get("mileage", float('inf')) > max_mileage:
                continue

            # Color is a bonus, not a filter (too strict)
            filtered.append(car)

        return filtered

    def _rank_results(
        self,
        results: List[Dict[str, Any]],
        criteria: dict
    ) -> List[Dict[str, Any]]:
        """
        Rank results by relevance to customer criteria.

        Args:
            results: Filtered results
            criteria: Customer preferences

        Returns:
            Sorted results (best first)
        """
        for car in results:
            score = 0

            # Source priority (website > Marktplaats)
            if car.get("source") == "seldenrijk_website":
                score += 100
            else:
                score += 50

            # Exact make match
            if criteria.get("make", "").lower() in car.get("make", "").lower():
                score += 50

            # Exact model match
            if criteria.get("model", "").lower() in car.get("model", "").lower():
                score += 50

            # Fuel type match
            if criteria.get("fuel_type", "").lower() == car.get("fuel_type", "").lower():
                score += 30

            # Price score (closer to max = better)
            max_price = criteria.get("max_price")
            if max_price and car.get("price"):
                price_diff = max_price - car["price"]
                if price_diff >= 0:
                    # Within budget: closer to max = higher score
                    score += min(20, int(price_diff / 1000))

            # Recency bonus
            if car.get("date_posted") == "Vandaag":
                score += 10
            elif car.get("date_posted") == "Gisteren":
                score += 5

            # Lower mileage = better
            if car.get("mileage"):
                if car["mileage"] < 50000:
                    score += 15
                elif car["mileage"] < 100000:
                    score += 10
                elif car["mileage"] < 150000:
                    score += 5

            # Quality indicators
            if car.get("nap_verified"):
                score += 5
            if car.get("service_book"):
                score += 5
            if car.get("featured"):
                score += 3

            # Color match (bonus)
            preferred_color = criteria.get("preferred_color", "").lower()
            if preferred_color and preferred_color in car.get("full_title", "").lower():
                score += 15

            car["relevance_score"] = score

        # Sort by score (highest first)
        return sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get results from cache if fresh.

        Args:
            cache_key: Cache key

        Returns:
            Cached results or None
        """
        if cache_key not in self._cache:
            return None

        cached = self._cache[cache_key]
        cached_time = cached["timestamp"]
        current_time = time.time()

        # Check if cache is still fresh (< 10 minutes old)
        if current_time - cached_time < self._cache_duration:
            return cached["results"]
        else:
            # Cache expired, remove it
            del self._cache[cache_key]
            return None

    def _cache_results(self, cache_key: str, results: List[Dict[str, Any]]):
        """
        Cache search results.

        Args:
            cache_key: Cache key
            results: Results to cache
        """
        self._cache[cache_key] = {
            "timestamp": time.time(),
            "results": results
        }

        # Clean old cache entries (older than 20 minutes)
        current_time = time.time()
        expired_keys = [
            key for key, value in self._cache.items()
            if current_time - value["timestamp"] > (self._cache_duration * 2)
        ]
        for key in expired_keys:
            del self._cache[key]
