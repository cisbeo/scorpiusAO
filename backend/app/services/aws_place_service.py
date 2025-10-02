"""
AWS PLACE Service for fetching government procurement notices.

AWS PLACE (Plateforme des Achats de l'État) is the main French government procurement platform.
It contains higher-value IT infrastructure contracts compared to BOAMP.

API Documentation: https://www.marches-publics.gouv.fr/
Note: AWS PLACE does not have a public REST API. This service uses web scraping with proper rate limiting.
"""
import httpx
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import logging
from bs4 import BeautifulSoup
import re
import asyncio

logger = logging.getLogger(__name__)


class AWSPlaceService:
    """
    Service for interacting with AWS PLACE (Plateforme des Achats de l'État).

    Note: AWS PLACE doesn't provide a public API, so we use web scraping with rate limiting.
    Alternative: Consider using data.gouv.fr DECP dataset for structured procurement data.
    """

    BASE_URL = "https://www.marches-publics.gouv.fr"
    SEARCH_URL = f"{BASE_URL}/?page=Entreprise.EntrepriseAdvancedSearch"

    # CPV codes for IT infrastructure & services (same as BOAMP, extended)
    RELEVANT_CPV_CODES = [
        # Core IT Services (72xxx)
        "72", "48", "30",  # Family codes for broad matching
        "72000000", "72260000", "72500000", "72700000", "72310000",
        "72400000", "72600000", "72410000", "72254000", "72253000",
        "72800000", "72322000", "72212000", "72230000", "72240000",
        "72611000",

        # Hosting & Infrastructure
        "50324000", "50324100", "50312000", "72318000",

        # Hardware & Equipment
        "30200000", "30230000", "30231000", "30236000",
        "48000000", "48800000", "48820000",

        # Telecom & Network
        "32400000", "32412000", "32420000", "32422000", "64200000",
    ]

    KEYWORDS = [
        # Core IT Infrastructure
        "hébergement", "datacenter", "data center", "infrastructure", "infogérance",
        "cloud", "serveur", "virtualisation", "stockage", "sauvegarde", "backup",
        "réseau", "système d'information", "si",

        # IT Services & Support
        "support informatique", "maintenance informatique", "supervision", "monitoring",
        "exploitation informatique", "administration système", "gestion de parc",
        "hotline", "helpdesk", "service desk", "astreinte",

        # Security & Compliance
        "sécurité informatique", "cybersécurité", "iso 27001", "iso27001",
        "rgpd", "gdpr", "firewall", "pare-feu", "antivirus", "soc", "siem",

        # Methodologies & Standards
        "itil", "devops", "agile", "scrum", "iso 9001", "iso 20000", "cobit",

        # Technologies & Solutions
        "erp", "crm", "gestion documentaire", "ged", "base de données", "sgbd",
        "middleware", "api", "web service", "interconnexion", "intégration", "migration",

        # Telecom & Network
        "voip", "téléphonie ip", "visioconférence", "fibre optique",
        "wan", "lan", "vpn", "wifi", "commutateur", "routeur", "switch",

        # Digital & Web
        "site web", "portail", "application web", "application mobile",
        "développement", "logiciel", "progiciel", "saas", "paas", "iaas",

        # Organizations (DSI keywords)
        "dsi", "direction informatique", "direction numérique",
        "transformation digitale", "transition numérique",
    ]

    def __init__(self, timeout: int = 30):
        """
        Initialize AWS PLACE service.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self._rate_limit_delay = 2  # Seconds between requests (respectful scraping)

    async def fetch_latest_consultations(
        self,
        limit: int = 50,
        days_back: int = 30,
        min_amount: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch latest consultations from AWS PLACE.

        Note: This is a placeholder implementation. AWS PLACE requires either:
        1. Web scraping (with proper rate limiting and robots.txt compliance)
        2. Using data.gouv.fr DECP (Données Essentielles de Commande Publique) dataset
        3. Commercial API access

        For production, recommend using DECP dataset from data.gouv.fr:
        https://data.gouv.fr/fr/datasets/donnees-essentielles-de-la-commande-publique/

        Args:
            limit: Maximum number of records to fetch
            days_back: Number of days to look back
            min_amount: Minimum contract amount in euros (for filtering)

        Returns:
            List of consultation dictionaries
        """
        logger.info(f"Fetching AWS PLACE consultations (last {days_back} days, limit={limit})")

        # For now, use DECP API as a structured alternative to web scraping
        return await self._fetch_from_decp_api(limit, days_back, min_amount)

    async def _fetch_from_decp_api(
        self,
        limit: int = 50,
        days_back: int = 30,
        min_amount: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch from DECP (Données Essentielles de Commande Publique) API.

        DECP is an open data API providing structured procurement contract data.
        It's more reliable than web scraping AWS PLACE.

        Note: DECP API endpoint has changed. This is a placeholder implementation.
        For production, configure access to DECP consolidated files or use commercial API.

        Options for production:
        1. DECP consolidated JSON: https://files.data.gouv.fr/decp/
        2. data.gouv.fr API: https://www.data.gouv.fr/api/1/datasets/
        3. Commercial AWS PLACE API access
        """

        # PLACEHOLDER: Return empty list for now
        # TODO: Implement proper DECP API integration when endpoint is confirmed
        logger.warning("AWS PLACE/DECP integration is a placeholder. Configure API access for production.")
        logger.info(f"AWS PLACE fetch requested: days_back={days_back}, limit={limit}, min_amount={min_amount}")

        # For testing purposes, return mock data
        consultations = []

        # Mock consultation for testing (remove in production)
        if days_back > 0 and limit > 0:
            mock_consultation = {
                "place_id": "MOCK-2025-001",
                "title": "Hébergement et infogérance de l'infrastructure informatique",
                "reference": "MOCK-REF-001",
                "organization": "Ministère de l'Exemple",
                "publication_date": (date.today() - timedelta(days=5)).isoformat(),
                "deadline": (date.today() + timedelta(days=25)).isoformat(),
                "description": "Marché d'hébergement datacenter et infogérance pour infrastructure critique",
                "cpv_codes": ["72000000", "50324000"],
                "consultation_type": "Appel d'offres ouvert",
                "procedure_type": "Procédure ouverte",
                "estimated_amount": 250000,
                "currency": "EUR",
                "execution_location": "Paris",
                "nuts_codes": ["FR1"],
                "duration_months": 36,
                "renewal_possible": True,
                "raw_data": {"mock": True},
                "url": "https://www.marches-publics.gouv.fr/mock",
                "documents_url": "https://www.marches-publics.gouv.fr/mock/docs",
            }
            consultations.append(mock_consultation)
            logger.info("Returning 1 mock consultation for testing")

        return consultations

    def _parse_decp_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a DECP API record into our standardized format.

        Args:
            record: Raw DECP API record

        Returns:
            Parsed consultation dictionary or None if parsing fails
        """
        try:
            # DECP record structure (may vary)
            return {
                "place_id": record.get("id", "") or record.get("uid", ""),
                "title": record.get("objet", "") or record.get("objetMarche", ""),
                "reference": record.get("marche_numero", "") or record.get("idMarche", ""),
                "organization": record.get("acheteur_nom", "") or record.get("nomAcheteur", ""),
                "publication_date": record.get("datePublicationDonnees", ""),
                "deadline": record.get("dateNotification", "") or record.get("datelimitereponse", ""),
                "description": record.get("description", "") or record.get("objet", ""),
                "cpv_codes": self._extract_cpv_codes(record),
                "consultation_type": record.get("nature", "") or record.get("typeMarche", ""),
                "procedure_type": record.get("procedure", "") or record.get("typeProcedure", ""),
                "estimated_amount": record.get("montant", 0) or record.get("montantMarche", 0),
                "currency": "EUR",
                "execution_location": record.get("lieuExecution_nom", "") or record.get("lieuExecutionNom", ""),
                "nuts_codes": [],
                "duration_months": record.get("dureeMois", None) or record.get("duree", None),
                "renewal_possible": False,
                "raw_data": record,
                "url": record.get("url", ""),
                "documents_url": record.get("urlDCE", "") or record.get("dceUrl", ""),
            }

        except Exception as e:
            logger.error(f"Error parsing DECP record: {e}")
            return None

    def _extract_cpv_codes(self, record: Dict[str, Any]) -> List[str]:
        """Extract CPV codes from DECP record"""
        cpv_codes = []

        # Try different field names
        for field in ["codeCPV", "cpv", "cpvCode", "cpvPrincipal"]:
            value = record.get(field)
            if value:
                if isinstance(value, list):
                    cpv_codes.extend([str(c) for c in value])
                else:
                    cpv_codes.append(str(value))

        return cpv_codes

    def filter_relevant_consultations(
        self,
        consultations: List[Dict[str, Any]],
        check_keywords: bool = True,
        check_cpv: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Filter consultations for IT infrastructure relevance.

        Args:
            consultations: List of consultation dictionaries
            check_keywords: Whether to check for keywords in title/description
            check_cpv: Whether to check CPV codes

        Returns:
            Filtered list of relevant consultations
        """
        relevant = []

        for consultation in consultations:
            is_relevant = False

            # Check CPV codes
            if check_cpv and self._check_cpv_codes(consultation):
                is_relevant = True

            # Check keywords
            if check_keywords and self._check_keywords(consultation):
                is_relevant = True

            if is_relevant:
                relevant.append(consultation)

        logger.info(f"Filtered {len(relevant)}/{len(consultations)} relevant consultations")
        return relevant

    def _check_cpv_codes(self, consultation: Dict[str, Any]) -> bool:
        """Check if consultation has relevant CPV codes"""
        cpv_codes = consultation.get("cpv_codes", []) or []

        for cpv in cpv_codes:
            cpv_str = str(cpv).strip()
            for relevant_cpv in self.RELEVANT_CPV_CODES:
                # Match by prefix (e.g., "72" matches "72000000", "72260000", etc.)
                if cpv_str.startswith(relevant_cpv[:2]):
                    return True

        return False

    def _check_keywords(self, consultation: Dict[str, Any]) -> bool:
        """Check if consultation contains relevant keywords"""
        # Combine title and description for searching
        text = " ".join([
            consultation.get("title", "").lower(),
            consultation.get("description", "").lower(),
        ])

        # Check for any keyword match
        for keyword in self.KEYWORDS:
            if keyword.lower() in text:
                return True

        return False


# Singleton instance
aws_place_service = AWSPlaceService()
