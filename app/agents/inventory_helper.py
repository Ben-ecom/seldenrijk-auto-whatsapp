"""
Inventory Helper for Conversation Agent.

Detects vehicle inquiries and searches Seldenrijk inventory cache.
Provides vehicle context for agent responses.
"""
import re
from typing import Dict, Any, List, Optional
from app.services.inventory_service import get_inventory_service
from app.monitoring.logging_config import get_logger

logger = get_logger(__name__)


class InventoryHelper:
    """
    Helper class for integrating vehicle inventory into conversations.

    Features:
    - Detect vehicle inquiries from user messages
    - Search inventory cache for matching vehicles
    - Format vehicle data for agent context
    - Extract search parameters from natural language
    """

    def __init__(self):
        """Initialize inventory helper."""
        self.inventory_service = get_inventory_service()

        # Common brand variations
        self.brand_mappings = {
            "beemer": "BMW",
            "bimmer": "BMW",
            "merc": "Mercedes-Benz",
            "mercedes": "Mercedes-Benz",
            "vw": "Volkswagen",
            "volks": "Volkswagen",
            "golf": "Volkswagen",  # Model → Brand mapping
            "polo": "Volkswagen",
            "beetle": "Volkswagen",
            "passat": "Volkswagen",
            "tiguan": "Volkswagen",
        }

        # Common model variations
        self.model_patterns = {
            r'\b(x[1-7])\b': r'\1',  # BMW X1, X5, etc.
            r'\b(serie [1-7])\b': r'Serie \1',  # BMW 3 Serie
            r'\b(klasse [a-z])\b': r'\1-Klasse',  # Mercedes A-Klasse
            r'\b(c-klasse|e-klasse|s-klasse)\b': r'\1',  # Mercedes classes
        }

    async def is_vehicle_inquiry(self, message: str) -> bool:
        """
        Detect if message is asking about vehicles.

        Args:
            message: User message text

        Returns:
            True if message likely about vehicle inquiry
        """
        message_lower = message.lower()

        # Vehicle inquiry keywords
        vehicle_keywords = [
            "auto", "wagen", "voertuig", "occasion",
            "tweedehands", "car", "vehicle",
            "bmw", "mercedes", "audi", "volkswagen", "vw",
            "golf", "polo", "x5", "x3", "c-klasse", "e-klasse",
            "suv", "sedan", "hatchback", "stationwagen"
        ]

        # Inquiry action words
        inquiry_keywords = [
            "heb", "heeft", "hebben", "beschikbaar", "voorraad",
            "kost", "prijs", "interesseer", "zoek", "wil", "graag",
            "verkoop", "aanbod", "zie", "zag", "website"
        ]

        has_vehicle_keyword = any(kw in message_lower for kw in vehicle_keywords)
        has_inquiry_keyword = any(kw in message_lower for kw in inquiry_keywords)

        return has_vehicle_keyword and has_inquiry_keyword

    async def extract_search_params(self, message: str) -> Dict[str, Any]:
        """
        Extract search parameters from natural language message.

        Args:
            message: User message text

        Returns:
            Dict with search parameters (brand, model, max_price, fuel_type, etc.)
        """
        params = {}
        message_lower = message.lower()

        # Extract brand
        brand = self._extract_brand(message_lower)
        if brand:
            params["brand"] = brand

        # Extract model
        model = self._extract_model(message_lower, brand)
        if model:
            params["model"] = model

        # Extract price constraint
        max_price = self._extract_price(message_lower)
        if max_price:
            params["max_price"] = max_price

        # Extract fuel type
        fuel_type = self._extract_fuel_type(message_lower)
        if fuel_type:
            params["fuel_type"] = fuel_type

        # Extract year constraint
        min_year = self._extract_year(message_lower)
        if min_year:
            params["min_year"] = min_year

        logger.debug(
            f"📊 Extracted search params from message",
            extra={"params": params, "message_preview": message[:50]}
        )

        return params

    async def search_inventory(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search inventory with extracted parameters.

        Args:
            params: Search parameters from extract_search_params()

        Returns:
            List of matching vehicles
        """
        try:
            vehicles = await self.inventory_service.search_vehicles(
                brand=params.get("brand"),
                model=params.get("model"),
                max_price=params.get("max_price"),
                min_price=params.get("min_price"),
                fuel_type=params.get("fuel_type"),
                max_mileage=params.get("max_mileage"),
                min_year=params.get("min_year"),
                limit=params.get("limit", 10)
            )

            logger.info(
                f"🔍 Inventory search complete: {len(vehicles)} matches",
                extra={"params": params, "result_count": len(vehicles)}
            )

            return vehicles

        except Exception as e:
            logger.error(f"❌ Inventory search failed: {e}", exc_info=True)
            return []

    def format_vehicle_context(self, vehicles: List[Dict[str, Any]], limit: int = 5) -> str:
        """
        Format vehicle data for agent context.

        Args:
            vehicles: List of vehicle dicts
            limit: Max number of vehicles to include in context

        Returns:
            Formatted string for agent prompt
        """
        if not vehicles:
            return """
📋 **BESCHIKBARE VOERTUIGEN:**

Geen voertuigen gevonden die aan de zoekcriteria voldoen.

**KRITISCH:**
- Zeg de klant dat deze specifieke auto momenteel niet beschikbaar is
- Vraag of ze interesse hebben in alternatieven
- Verwijs naar website voor volledige aanbod: https://seldenrijk.nl
"""

        # Limit vehicles to avoid context overflow
        vehicles_to_show = vehicles[:limit]

        context_parts = [
            "📋 **BESCHIKBARE VOERTUIGEN (Seldenrijk.nl):**",
            ""
        ]

        for idx, v in enumerate(vehicles_to_show, 1):
            vehicle_text = f"""**{idx}. {v['brand']} {v['model']}** (€{v['price']:,})
- Bouwjaar: {v.get('buildYear', 'Onbekend')}
- Kilometerstand: {v.get('mileage', 0):,} km
- Brandstof: {v.get('fuel', 'Onbekend')}
- Transmissie: {v.get('transmission', 'Onbekend')}
- Link: {v['url']}
"""
            context_parts.append(vehicle_text)

        # Add footer instructions
        context_parts.extend([
            "",
            "**KRITISCH - AGENT INSTRUCTIES:**",
            "- Gebruik ALLEEN data uit bovenstaande lijst",
            "- Als gevraagde auto niet in lijst: zeg dat deze NIET beschikbaar is",
            "- Geen prijzen/specs verzinnen",
            "- Verwijs altijd naar link voor foto's en volledige details",
            "- Bied alternatieven aan uit de lijst als exacte match niet beschikbaar",
            "",
            f"**TOTAAL:** {len(vehicles)} voertuigen gevonden (toont top {len(vehicles_to_show)})"
        ])

        return "\n".join(context_parts)

    def _extract_brand(self, message: str) -> Optional[str]:
        """Extract brand from message."""
        # Check direct brand mentions
        brands = [
            "BMW", "Mercedes-Benz", "Mercedes", "Audi", "Volkswagen", "VW",
            "Volvo", "SEAT", "Skoda", "MINI", "Ford", "Opel",
            "Peugeot", "Renault", "Toyota", "Lexus", "Mazda", "Kia",
            "Hyundai", "Nissan", "Land Rover", "Jaguar", "Porsche",
            "CUPRA", "Cupra"
        ]

        for brand in brands:
            if brand.lower() in message:
                return brand

        # Check brand mappings (nicknames)
        for nickname, brand in self.brand_mappings.items():
            if nickname in message:
                return brand

        return None

    def _extract_model(self, message: str, brand: Optional[str]) -> Optional[str]:
        """Extract model from message."""
        # Common models to look for
        models = [
            # BMW
            "X1", "X2", "X3", "X4", "X5", "X6", "X7",
            "1 Serie", "2 Serie", "3 Serie", "4 Serie", "5 Serie", "6 Serie", "7 Serie",
            # Mercedes
            "A-Klasse", "B-Klasse", "C-Klasse", "E-Klasse", "S-Klasse",
            "GLA", "GLB", "GLC", "GLE", "GLS",
            # VW
            "Golf", "Polo", "Passat", "Tiguan", "T-Roc", "Arteon",
            # Audi
            "A1", "A3", "A4", "A5", "A6", "A7", "A8",
            "Q2", "Q3", "Q5", "Q7", "Q8"
        ]

        for model in models:
            if model.lower() in message:
                return model

        # Try regex patterns
        for pattern, replacement in self.model_patterns.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return None

    def _extract_price(self, message: str) -> Optional[int]:
        """Extract maximum price constraint."""
        # Look for patterns like "max €25.000", "tot 25000", "budget 25k"
        patterns = [
            r'max(?:imum)?\s*€?\s*(\d{1,3}(?:[.,]\d{3})*)',
            r'tot\s*€?\s*(\d{1,3}(?:[.,]\d{3})*)',
            r'budget\s*€?\s*(\d{1,3}(?:[.,]\d{3})*)',
            r'€\s*(\d{1,3}(?:[.,]\d{3})*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                price_str = match.group(1).replace(".", "").replace(",", "")
                try:
                    return int(price_str)
                except ValueError:
                    continue

        return None

    def _extract_fuel_type(self, message: str) -> Optional[str]:
        """Extract fuel type preference."""
        fuel_types = {
            "benzine": "Benzine",
            "diesel": "Diesel",
            "hybride": "Hybride",
            "elektrisch": "Elektrisch",
            "electric": "Elektrisch",
            "lpg": "LPG"
        }

        for keyword, fuel in fuel_types.items():
            if keyword in message:
                return fuel

        return None

    def _extract_year(self, message: str) -> Optional[int]:
        """Extract minimum year constraint."""
        # Look for patterns like "vanaf 2020", "min 2019", "nieuwer dan 2018"
        patterns = [
            r'vanaf\s*(\d{4})',
            r'min(?:imum)?\s*(\d{4})',
            r'nieuwer\s+dan\s*(\d{4})',
            r'na\s*(\d{4})',
        ]

        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue

        return None


# Singleton instance
_inventory_helper = None


def get_inventory_helper() -> InventoryHelper:
    """Get singleton inventory helper instance."""
    global _inventory_helper
    if _inventory_helper is None:
        _inventory_helper = InventoryHelper()
    return _inventory_helper
