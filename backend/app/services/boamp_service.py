"""
BOAMP Service for fetching public procurement notices from BOAMP API.

API Documentation: https://help.opendatasoft.com/apis/ods-explore-v2/
Dataset: https://boamp-datadila.opendatasoft.com/explore/dataset/boamp/
"""
import httpx
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BOAMPService:
    """
    Service for interacting with BOAMP (Bulletin Officiel des Annonces des Marchés Publics) API.
    """

    BASE_URL = "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records"

    # CPV codes for IT infrastructure & services
    RELEVANT_CPV_CODES = [
        "72000000",  # Services informatiques
        "72260000",  # Services logiciels
        "72500000",  # Services de conseil en informatique
        "50324000",  # Hébergement de sites informatiques
        "72700000",  # Services de réseau informatique
        "72310000",  # Services de traitement de données
        "72400000",  # Services internet
        "72600000",  # Services de soutien informatique
        "72410000",  # Services de fournisseur de services internet
        "72254000",  # Services de conseil en tests
        "72253000",  # Services de conseil en assistance informatique
        "72800000",  # Services de conseil en matériel informatique
    ]

    # Keywords for filtering relevant tenders
    KEYWORDS = [
        "hébergement",
        "datacenter",
        "infrastructure",
        "itil",
        "iso 27001",
        "supervision",
        "support",
        "maintenance informatique",
        "infogérance",
        "cloud",
        "serveur",
        "virtualisation",
        "stockage",
        "sauvegarde",
        "sécurité informatique",
        "réseau",
        "système d'information",
    ]

    def __init__(self, timeout: int = 30):
        """
        Initialize BOAMP service.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout

    async def fetch_latest_publications(
        self,
        limit: int = 100,
        days_back: int = 7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch latest BOAMP publications from API.

        Args:
            limit: Maximum number of records to fetch
            days_back: Number of days to look back from today
            filters: Optional additional filters (type_annonce, montant_min, etc.)

        Returns:
            List of publication records

        Raises:
            httpx.HTTPError: If API request fails
        """
        # Calculate date range
        date_from = (date.today() - timedelta(days=days_back)).isoformat()

        # Build query parameters
        params = {
            "limit": limit,
            "order_by": "dateparution desc",
            "where": f"dateparution >= date'{date_from}'"
        }

        # Add additional filters if provided
        if filters:
            if "type_annonce" in filters:
                params["where"] += f" AND typeannonce = '{filters['type_annonce']}'"
            if "montant_min" in filters:
                params["where"] += f" AND montant >= {filters['montant_min']}"

        logger.info(f"Fetching BOAMP publications with params: {params}")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            logger.info(f"Fetched {len(results)} publications from BOAMP")
            return results

    def filter_relevant_publications(
        self,
        publications: List[Dict[str, Any]],
        min_amount: Optional[float] = None,
        check_keywords: bool = True,
        check_cpv: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Filter publications to keep only relevant ones for IT infrastructure/services.

        Args:
            publications: List of raw BOAMP publications
            min_amount: Minimum contract amount in euros
            check_keywords: Enable keyword-based filtering
            check_cpv: Enable CPV code filtering

        Returns:
            Filtered list of relevant publications
        """
        relevant = []

        for pub in publications:
            fields = pub.get("fields", {})

            # Filter by amount if specified
            if min_amount:
                montant = fields.get("montant")
                if montant and float(montant) < min_amount:
                    continue

            # Check CPV codes
            if check_cpv:
                cpv_found = self._check_cpv_codes(fields)
                if not cpv_found:
                    continue

            # Check keywords in title and description
            if check_keywords:
                keyword_found = self._check_keywords(fields)
                if not keyword_found:
                    continue

            relevant.append(pub)

        logger.info(f"Filtered {len(relevant)}/{len(publications)} relevant publications")
        return relevant

    def _check_cpv_codes(self, fields: Dict[str, Any]) -> bool:
        """
        Check if publication has relevant CPV codes.

        Args:
            fields: Publication fields

        Returns:
            True if relevant CPV code found
        """
        cpv_codes = fields.get("codecpv", [])
        if not cpv_codes:
            return False

        # Check if any CPV code starts with our relevant prefixes
        for cpv in cpv_codes:
            cpv_str = str(cpv).strip()
            for relevant_cpv in self.RELEVANT_CPV_CODES:
                if cpv_str.startswith(relevant_cpv[:4]):  # Match first 4 digits
                    return True

        return False

    def _check_keywords(self, fields: Dict[str, Any]) -> bool:
        """
        Check if publication contains relevant keywords.

        Args:
            fields: Publication fields

        Returns:
            True if relevant keyword found
        """
        # Combine title and description
        text = " ".join([
            fields.get("objet", ""),
            fields.get("intitule", ""),
            fields.get("descripteurs", [])
        ]).lower()

        # Check if any keyword is present
        for keyword in self.KEYWORDS:
            if keyword.lower() in text:
                return True

        return False

    def parse_publication(self, raw_publication: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse raw BOAMP API response into structured format.

        Args:
            raw_publication: Raw publication dict from API

        Returns:
            Parsed publication data
        """
        fields = raw_publication.get("fields", {})
        record_id = raw_publication.get("record", {}).get("id", "")

        # Parse dates
        publication_date = self._parse_date(fields.get("dateparution"))
        deadline = self._parse_date(fields.get("datelimitereponse"))

        # Parse amount
        montant = None
        if fields.get("montant"):
            try:
                montant = float(fields["montant"])
            except (ValueError, TypeError):
                pass

        # Extract CPV codes
        cpv_codes = fields.get("codecpv", [])
        if isinstance(cpv_codes, str):
            cpv_codes = [cpv_codes]

        # Extract descriptors
        descripteurs = fields.get("descripteurs", [])
        if isinstance(descripteurs, str):
            descripteurs = [descripteurs]

        return {
            "boamp_id": record_id,
            "title": fields.get("objet", "") or fields.get("intitule", ""),
            "organization": fields.get("acheteur", "") or fields.get("nomorganisme", ""),
            "publication_date": publication_date,
            "deadline": deadline,
            "type_annonce": fields.get("typeannonce", ""),
            "objet": fields.get("objet", ""),
            "montant": montant,
            "lieu_execution": fields.get("lieuexecution", ""),
            "cpv_codes": cpv_codes,
            "descripteurs": descripteurs,
            "raw_data": raw_publication,
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """
        Parse date string from BOAMP API.

        Args:
            date_str: Date string in ISO format

        Returns:
            Parsed date or None
        """
        if not date_str:
            return None

        try:
            # Try ISO format first
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.date()
        except (ValueError, AttributeError):
            return None


# Global service instance
boamp_service = BOAMPService()
