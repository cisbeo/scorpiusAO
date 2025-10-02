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

    # CPV codes for IT infrastructure & services (expanded coverage)
    RELEVANT_CPV_CODES = [
        # Core IT Services (72xxx)
        "72000000",  # Services informatiques (général)
        "72260000",  # Services logiciels
        "72500000",  # Services de conseil en informatique
        "72700000",  # Services de réseau informatique
        "72310000",  # Services de traitement de données
        "72400000",  # Services internet
        "72600000",  # Services de soutien informatique
        "72410000",  # Services de fournisseur de services internet
        "72254000",  # Services de conseil en tests
        "72253000",  # Services de conseil en assistance informatique
        "72800000",  # Services de conseil en matériel informatique
        "72322000",  # Services de gestion de données
        "72212000",  # Services de programmation de logiciels système
        "72230000",  # Services de développement de logiciels personnalisés
        "72240000",  # Services de conseil en analyse de systèmes et de programmation
        "72611000",  # Services de soutien technique

        # Hosting & Infrastructure (50xxx, 72xxx)
        "50324000",  # Hébergement de sites informatiques
        "50324100",  # Services d'hébergement
        "50312000",  # Services de mise à disposition de logiciels
        "72318000",  # Services de gestion de systèmes informatiques

        # Hardware & Equipment (30xxx, 48xxx)
        "30200000",  # Équipements informatiques
        "30230000",  # Matériel informatique
        "30231000",  # Consoles d'affichage, terminaux informatiques
        "30236000",  # Divers équipements informatiques
        "48000000",  # Progiciels et systèmes d'information
        "48800000",  # Systèmes et serveurs d'information
        "48820000",  # Serveurs

        # Telecom & Network (32xxx, 64xxx)
        "32400000",  # Réseaux
        "32412000",  # Réseau informatique
        "32420000",  # Équipements et matériel de réseau
        "32422000",  # Composants de réseau
        "64200000",  # Services de télécommunications

        # Security & Backup (72xxx, 79xxx)
        "72224000",  # Services de conseil en gestion de projet
        "72227000",  # Services de conseil en intégration de logiciels
        "72266000",  # Services de conseil en logiciels
        "72267000",  # Services de maintenance et de réparation de logiciels
        "72268000",  # Services de fourniture de logiciels
        "79800000",  # Services d'impression et services connexes
        "79995000",  # Services de sténographie et de soutien

        # Cloud & SaaS (broad match on 72xxx, 48xxx)
        "72",  # All IT services (2-digit family code)
        "48",  # All software/systems (2-digit family code)
        "30",  # All IT equipment (2-digit family code)
    ]

    # Keywords for filtering relevant tenders (expanded)
    KEYWORDS = [
        # Core IT Infrastructure
        "hébergement",
        "datacenter",
        "data center",
        "infrastructure",
        "infogérance",
        "cloud",
        "serveur",
        "virtualisation",
        "stockage",
        "sauvegarde",
        "backup",
        "réseau",
        "système d'information",
        "si",  # Système d'Information (acronym)

        # IT Services & Support
        "support informatique",
        "maintenance informatique",
        "supervision",
        "monitoring",
        "exploitation informatique",
        "administration système",
        "gestion de parc",
        "hotline",
        "helpdesk",
        "service desk",
        "astreinte",

        # Security & Compliance
        "sécurité informatique",
        "cybersécurité",
        "iso 27001",
        "iso27001",
        "rgpd",
        "gdpr",
        "firewall",
        "pare-feu",
        "antivirus",
        "soc",  # Security Operations Center
        "siem",

        # Methodologies & Standards
        "itil",
        "devops",
        "agile",
        "scrum",
        "iso 9001",
        "iso 20000",
        "cobit",

        # Technologies & Solutions
        "erp",
        "crm",
        "gestion documentaire",
        "ged",
        "base de données",
        "sgbd",
        "middleware",
        "api",
        "web service",
        "interconnexion",
        "intégration",
        "migration",

        # Telecom & Network
        "voip",
        "téléphonie ip",
        "visioconférence",
        "fibre optique",
        "wan",
        "lan",
        "vpn",
        "wifi",
        "commutateur",
        "routeur",
        "switch",

        # Digital & Web
        "site web",
        "portail",
        "application web",
        "application mobile",
        "développement",
        "logiciel",
        "progiciel",
        "saas",
        "paas",
        "iaas",

        # Organizations (DSI keywords)
        "dsi",  # Direction des Systèmes d'Information
        "direction informatique",
        "direction numérique",
        "transformation digitale",
        "transition numérique",
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
            "where": f"dateparution >= '{date_from}'"  # Fixed: removed 'date' prefix
        }

        # Add additional filters if provided
        if filters:
            if "type_annonce" in filters:
                params["where"] += f" AND typeannonce = '{filters['type_annonce']}'"
            if "montant_min" in filters:
                params["where"] += f" AND montant >= {filters['montant_min']}"

        logger.info(f"Fetching BOAMP publications with params: {params}")

        # BOAMP API has a limit of 100 results per request
        # Need to paginate if limit > 100
        max_per_request = 100
        all_results = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if limit <= max_per_request:
                # Single request
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                all_results = data.get("results", [])
            else:
                # Multiple requests with pagination
                offset = 0
                while len(all_results) < limit:
                    page_params = params.copy()
                    page_params["limit"] = max_per_request
                    page_params["offset"] = offset

                    response = await client.get(self.BASE_URL, params=page_params)
                    response.raise_for_status()
                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        break  # No more results

                    all_results.extend(results)
                    offset += max_per_request

                    logger.info(f"Fetched {len(all_results)}/{limit} publications (offset={offset})")

                    if len(results) < max_per_request:
                        break  # Last page

                # Trim to exact limit
                all_results = all_results[:limit]

        logger.info(f"Fetched {len(all_results)} publications from BOAMP")
        return all_results

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
            # NEW: Data is directly in pub, not nested in "fields"
            # Filter by amount if specified (skip for now as field not standard)
            # if min_amount:
            #     montant = pub.get("montant")
            #     if montant and float(montant) < min_amount:
            #         continue

            # Check CPV codes
            if check_cpv:
                cpv_found = self._check_cpv_codes(pub)
                if not cpv_found:
                    continue

            # Check keywords in title and description
            if check_keywords:
                keyword_found = self._check_keywords(pub)
                if not keyword_found:
                    continue

            relevant.append(pub)

        logger.info(f"Filtered {len(relevant)}/{len(publications)} relevant publications")
        return relevant

    def _check_cpv_codes(self, record: Dict[str, Any]) -> bool:
        """
        Check if publication has relevant CPV codes.

        Args:
            record: Publication record (data at root level)

        Returns:
            True if relevant CPV code found
        """
        # Try different CPV field names used by BOAMP
        descripteur_codes = record.get("descripteur_code", []) or record.get("dc", [])

        if not descripteur_codes:
            return False

        # Check if any code starts with our relevant prefixes
        for cpv in descripteur_codes:
            cpv_str = str(cpv).strip()
            for relevant_cpv in self.RELEVANT_CPV_CODES:
                # Match first 2-4 digits for broader coverage
                if cpv_str.startswith(relevant_cpv[:2]):
                    return True

        return False

    def _check_keywords(self, record: Dict[str, Any]) -> bool:
        """
        Check if publication contains relevant keywords.

        Args:
            record: Publication record (data at root level)

        Returns:
            True if relevant keyword found
        """
        # Get descriptors
        descripteurs = record.get("descripteur_libelle", []) or []
        if isinstance(descripteurs, str):
            descripteurs = [descripteurs]

        # Combine title and descriptors
        text_parts = [
            record.get("objet", ""),
            " ".join(descripteurs)
        ]

        text = " ".join(text_parts).lower()

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
        # NEW: Data is directly in raw_publication, not nested
        record_id = raw_publication.get("id", "") or raw_publication.get("idweb", "")

        # Parse dates
        publication_date = self._parse_date(raw_publication.get("dateparution"))
        deadline = self._parse_date(raw_publication.get("datelimitereponse"))

        # Parse amount (not always present)
        montant = None
        # Note: montant field not standard in BOAMP, skip for now

        # Extract CPV codes (use descripteur_code which is standard)
        cpv_codes = raw_publication.get("descripteur_code", []) or raw_publication.get("dc", [])
        if isinstance(cpv_codes, str):
            cpv_codes = [cpv_codes]

        # Extract descriptors
        descripteurs = raw_publication.get("descripteur_libelle", [])
        if isinstance(descripteurs, str):
            descripteurs = [descripteurs]

        return {
            "boamp_id": record_id,
            "title": raw_publication.get("objet", ""),
            "organization": raw_publication.get("nomacheteur", ""),
            "publication_date": publication_date,
            "deadline": deadline,
            "type_annonce": raw_publication.get("nature_libelle", ""),
            "objet": raw_publication.get("objet", ""),
            "montant": montant,
            "lieu_execution": None,  # Not in standard BOAMP response
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
