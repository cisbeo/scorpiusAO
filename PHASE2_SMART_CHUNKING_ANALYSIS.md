# 🧩 PHASE 2 - Smart Chunking : Analyse approfondie

**Date** : 2025-10-01
**Statut** : ✅ **COMPLÉTÉ**
**Effort réel** : 13h (7 tâches)
**Prérequis** : PHASE 1 complétée ✅

---

## 📋 Table des matières

1. [Problématique actuelle](#problématique-actuelle)
2. [Objectifs de la PHASE 2](#objectifs-de-la-phase-2)
3. [Analyse des types de documents](#analyse-des-types-de-documents)
4. [Stratégies de chunking](#stratégies-de-chunking)
5. [Architecture proposée](#architecture-proposée)
6. [Implémentation détaillée](#implémentation-détaillée)
7. [Métadonnées enrichies](#métadonnées-enrichies)
8. [Plan de tests](#plan-de-tests)
9. [Questions critiques](#questions-critiques)

---

## 🎯 Problématique actuelle

### État actuel du chunking (PHASE 1)

Le chunking actuel dans [rag_service.py:472-490](backend/app/services/rag_service.py#L472) est **basique et naïf** :

```python
def chunk_text(self, text: str) -> List[str]:
    """Split text into chunks with overlap."""
    words = text.split()
    chunks = []

    for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
        chunk = " ".join(words[i:i + self.chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks
```

**Configuration actuelle** ([config.py:45-46](backend/app/core/config.py#L45)) :

- `chunk_size = 1024` (mots, pas tokens !)
- `chunk_overlap = 200` (mots)

### ❌ Problèmes identifiés

| Problème | Impact | Exemple concret |
|----------|--------|-----------------|
| **Découpage au milieu de sections** | Perte de contexte sémantique | Une section "Méthodologie Agile" coupée entre 2 chunks |
| **Taille en mots ≠ tokens** | Risque dépassement limite embeddings (8191 tokens) | 1024 mots ≈ 1365 tokens en moyenne |
| **Pas de détection de structure** | Headers/titres perdus | Titre "3.2 Certifications ISO" séparé du contenu |
| **Overlap fixe inadapté** | Redondance inutile pour certains docs | Templates courts sur-découpés |
| **Chunks trop grands** | Résultats peu précis en recherche | 1024 mots = ~5000 chars, difficile à exploiter |
| **Perte métadonnées structurelles** | Impossible de filtrer par section | "Chercher uniquement dans sections sécurité" impossible |

### 📊 Résultat des tests PHASE 1

Dans le test USE CASE 3 ([tests/run_rag_tests.py](backend/tests/run_rag_tests.py)), on observe :

- **1 chunk géant** pour un document de certification de 2500 caractères
- **Similarity scores faibles** (0.38-0.58) au lieu de >0.7 attendus
- Seuil abaissé à 0.3 pour compenser le chunking basique

> ⚠️ **Conclusion** : Le chunking actuel fonctionne mais n'exploite pas la structure des documents. PHASE 2 est critique pour améliorer la pertinence.

---

## 🎯 Objectifs de la PHASE 2

### Objectifs fonctionnels

1. ✅ **Respect de la structure documentaire**
   - Détecter les sections (H1, H2, H3)
   - Préserver les paragraphes logiques
   - Identifier les listes, tableaux, blocs de code

2. ✅ **Chunks optimaux pour recherche sémantique**
   - Taille : **256-1024 tokens** (pas mots)
   - Contexte : Inclure titre de section dans chunk
   - Granularité : Adaptée au type de document

3. ✅ **Métadonnées enrichies**
   - Section parente (ex: "3.2 Certifications ISO")
   - Niveau hiérarchique (H1, H2, H3)
   - Position dans document (chunk 3/10)
   - Type de contenu (texte, liste, tableau)

4. ✅ **Stratégies adaptatives**
   - Différentes stratégies par `document_type`
   - Configuration flexible par type

### Objectifs techniques

1. ✅ **Interface générique** : `ChunkingStrategy` abstrait
2. ✅ **Implémentations multiples** : Fixed, Section, Semantic
3. ✅ **Token counting précis** : Utiliser `tiktoken` (OpenAI)
4. ✅ **Backward compatible** : Méthode `chunk_text()` préservée
5. ✅ **Tests robustes** : 1 test par stratégie + tests d'intégration

---

## 📚 Analyse des types de documents

### 1️⃣ `past_proposal` (Réponses gagnantes passées)

**Structure typique** :

```
# Mémoire Technique - Appel d'offre Ministère XYZ

## 1. Présentation de l'entreprise
### 1.1 Historique et chiffres clés
### 1.2 Certifications et labels

## 2. Méthodologie proposée
### 2.1 Approche projet
### 2.2 Méthode Agile / SCRUM
### 2.3 Outils et technologies

## 3. Équipe dédiée
### 3.1 Organigramme
### 3.2 CV des intervenants
### 3.3 Plan de formation

## 4. Garanties et engagements
### 4.1 SLA et KPI
### 4.2 Processus qualité
### 4.3 Sécurité et conformité
```

**Caractéristiques** :

- 📏 **Longueur** : 10 000 - 50 000 mots (50-250 pages)
- 🏗️ **Structure** : Très hiérarchisée (H1 > H2 > H3)
- 📊 **Contenu** : Texte + tableaux + listes + schémas
- 🎯 **Objectif RAG** : Retrouver sections pertinentes pour réutilisation

**Stratégie de chunking recommandée** : **Section-Based**

- Découper par section H2 ou H3 (selon taille)
- Inclure le titre de section dans le chunk
- Overlap : 50 tokens (contexte minimal)
- Taille cible : **512 tokens** par chunk

**Exemple chunk** :

```
Section: 2.2 Méthode Agile / SCRUM
Niveau: H2

Notre approche repose sur la méthodologie Agile avec framework SCRUM.
Nous organisons le projet en sprints de 2 semaines...
[contenu de la section]

Métadonnées:
- section_title: "Méthode Agile / SCRUM"
- section_number: "2.2"
- section_level: "H2"
- parent_section: "2. Méthodologie proposée"
```

---

### 2️⃣ `certification` (Certifications ISO, HDS, etc.)

**Structure typique** :

```
CERTIFICAT ISO 27001:2013

Organisme certificateur: AFNOR Certification
Date d'émission: 15/06/2024
Date d'expiration: 14/06/2027

Périmètre de certification:
Système de management de la sécurité de l'information...

Processus couverts:
- Gestion des accès
- Sécurité physique
- Continuité d'activité
- Gestion des incidents

Annexe: Liste des sites certifiés
- Paris La Défense (siège)
- Lyon Part-Dieu (datacenter)
```

**Caractéristiques** :

- 📏 **Longueur** : 500 - 5 000 mots (2-10 pages)
- 🏗️ **Structure** : Faible hiérarchie, blocs de métadonnées
- 📊 **Contenu** : Texte structuré + listes + tableaux
- 🎯 **Objectif RAG** : Retrouver certifications spécifiques (ISO 27001, HDS)

**Stratégie de chunking recommandée** : **Semantic Paragraphs**

- Découper par paragraphes logiques (séparés par 2+ sauts de ligne)
- Préserver les listes et tableaux intégralement
- Overlap : 0 token (blocs indépendants)
- Taille cible : **256-512 tokens** par chunk

**Exemple chunk** :

```
Chunk: Périmètre de certification

Système de management de la sécurité de l'information
pour les activités de:
- Hébergement et infogérance d'infrastructures IT
- Services Cloud privé et hybride
- Support technique niveau 1, 2, 3

Métadonnées:
- certification_type: "ISO 27001"
- certification_number: "FR-123456"
- valid_until: "2027-06-14"
- issuer: "AFNOR Certification"
```

---

### 3️⃣ `case_study` (Références clients)

**Structure typique** :

```
# Cas client: Ministère de la Défense

## Contexte
Le Ministère de la Défense recherchait un partenaire...

## Enjeux
- Disponibilité 24/7/365
- Conformité SecNumCloud
- Capacité de montée en charge

## Solution proposée
### Architecture technique
- Datacenter Tier 4 redondé
- Infrastructure VMware vSphere 8
- Sauvegarde Veeam avec réplication géographique

### Équipe dédiée
- 1 Chef de projet certifié PMP
- 2 Ingénieurs sécurité (CISSP)
- 4 Techniciens support niveau 2

## Résultats
- ✅ 99.99% de disponibilité (SLA respecté)
- ✅ 0 incident de sécurité en 2 ans
- ✅ Économie de 30% vs solution précédente

## Témoignage client
"Un partenaire de confiance qui a su comprendre nos enjeux..."
```

**Caractéristiques** :

- 📏 **Longueur** : 1 000 - 10 000 mots (5-20 pages)
- 🏗️ **Structure** : Hiérarchisée (H1 > H2 > H3)
- 📊 **Contenu** : Texte + listes + chiffres clés + témoignage
- 🎯 **Objectif RAG** : Retrouver cas similaires par secteur/technologie

**Stratégie de chunking recommandée** : **Section-Based**

- Découper par section H2 (Contexte, Enjeux, Solution, Résultats)
- Overlap : 50 tokens
- Taille cible : **512 tokens** par chunk

**Exemple chunk** :

```
Section: Solution proposée > Architecture technique
Niveau: H3

Architecture technique redondée sur 2 datacenters Tier 4:
- Site principal: Paris-Saclay (500m²)
- Site de secours: Lyon Confluence (500m²)
[contenu détaillé]

Métadonnées:
- section_title: "Architecture technique"
- section_level: "H3"
- client_sector: "defense"
- technologies: ["VMware", "Veeam"]
```

---

### 4️⃣ `documentation` (Processus internes)

**Structure typique** :

```
# Processus ITSM - Gestion des incidents

## 1. Objectif
Définir le processus de gestion des incidents selon ITIL v4...

## 2. Périmètre
Tous les incidents affectant les services IT...

## 3. Flux de traitement
### 3.1 Détection
- Monitoring automatique (Nagios, Zabbix)
- Signalement utilisateur (portail, email, téléphone)

### 3.2 Qualification
- Catégorisation (réseau, serveur, application)
- Priorisation (P1 à P4 selon matrice d'impact)

### 3.3 Résolution
- Investigation niveau 1 (support)
- Escalade niveau 2 (experts)
- Escalade niveau 3 (éditeurs)

## 4. Indicateurs KPI
- MTTR (Mean Time To Resolve) < 4h (P1)
- MTTR < 24h (P2)
- Taux de résolution niveau 1 > 70%
```

**Caractéristiques** :

- 📏 **Longueur** : 2 000 - 20 000 mots (10-50 pages)
- 🏗️ **Structure** : Très hiérarchisée (procédures)
- 📊 **Contenu** : Texte + listes + tableaux + workflows
- 🎯 **Objectif RAG** : Retrouver processus spécifiques (ITSM, ITIL, DevOps)

**Stratégie de chunking recommandée** : **Section-Based**

- Découper par section H2 ou H3
- Overlap : 100 tokens (contexte procédural important)
- Taille cible : **512-1024 tokens** par chunk

**Exemple chunk** :

```
Section: 3.2 Qualification
Niveau: H2

Processus de qualification d'incident:

1. Catégorisation selon taxonomie ITIL:
   - Infrastructure (réseau, serveur, stockage)
   - Application (ERP, CRM, métier)
   - Sécurité (intrusion, malware, fuite)

2. Priorisation avec matrice impact/urgence:
[tableau P1-P4]

Métadonnées:
- process_type: "ITSM"
- process_name: "Gestion des incidents"
- section_title: "Qualification"
```

---

### 5️⃣ `template` (Templates pré-rédigés)

**Structure typique** :

```
# Template: Présentation entreprise

[ACME IT Services] est une société spécialisée dans [l'hébergement
et l'infogérance d'infrastructures IT critiques].

Créée en [2010], nous accompagnons [150+ clients] issus des secteurs
[public, santé, finance] dans leur transformation numérique.

## Nos certifications
- ISO 27001 (sécurité de l'information)
- ISO 9001 (qualité)
- HDS (hébergeur de données de santé)

## Nos chiffres clés
- [150+] clients actifs
- [200] collaborateurs
- [2] datacenters Tier 4
- [99.99%] de disponibilité

---

# Template: Méthodologie Agile

Notre approche projet repose sur les principes Agile...
[paragraphe réutilisable]
```

**Caractéristiques** :

- 📏 **Longueur** : 200 - 2 000 mots (1-5 pages)
- 🏗️ **Structure** : Sections courtes autonomes
- 📊 **Contenu** : Blocs textuels réutilisables
- 🎯 **Objectif RAG** : Retrouver paragraphes exacts pour insertion

**Stratégie de chunking recommandée** : **No Split / Minimal**

- **Ne PAS découper** si < 1024 tokens
- Si > 1024 tokens : découper par sections H1
- Overlap : 0 token (blocs autonomes)
- Taille cible : **Chunk unique** ou **256-512 tokens**

**Exemple chunk** :

```
Chunk unique: Template présentation entreprise

[Contenu complet du template sans découpage]

Métadonnées:
- template_type: "company_presentation"
- template_name: "Présentation entreprise standard"
- variables: ["COMPANY_NAME", "YEAR", "CLIENT_COUNT"]
- last_updated: "2024-09-15"
```

---

## 🛠️ Stratégies de chunking

### Vue d'ensemble

| Stratégie | Use Case | Taille chunk | Overlap | Détection structure |
|-----------|----------|--------------|---------|---------------------|
| **Fixed** | Fallback générique | 512 tokens | 50 tokens | ❌ Non |
| **Section** | Docs hiérarchisés | 256-1024 tokens | 50-100 tokens | ✅ Headers (H1-H3) |
| **Semantic** | Docs courts structurés | 256-512 tokens | 0 token | ✅ Paragraphes |
| **NoSplit** | Templates courts | N/A (chunk unique) | 0 token | ❌ Non |

### Matrice décisionnelle

```python
CHUNKING_STRATEGY_MAP = {
    # Knowledge Base types
    "past_proposal": "section",      # Hiérarchie H1-H3, long
    "certification": "semantic",     # Paragraphes, court
    "case_study": "section",         # Hiérarchie H1-H3, moyen
    "documentation": "section",      # Procédures, très structuré
    "template": "nosplit",           # Blocs courts autonomes

    # Future: Tender Archive (PHASE 6)
    "past_tender_won": "section",
    "past_tender_strategic": "section"
}
```

---

## 🏗️ Architecture proposée

### Diagramme de classes

```
┌──────────────────────────────────────────┐
│     ChunkingStrategy (ABC)               │
├──────────────────────────────────────────┤
│ + chunk(text, metadata) -> List[Chunk]   │
│ + get_token_count(text) -> int           │
│ # _extract_metadata(chunk) -> dict       │
└──────────────────────────────────────────┘
                    △
                    │
       ┌────────────┼────────────┬─────────────┐
       │            │            │             │
┌──────┴──────┐ ┌───┴─────┐ ┌───-┴──────┐ ┌────┴─────┐
│FixedChunking│ │SectionCh│ │SemanticCh │ │NoSplitCh │
│  Strategy   │ │ unking  │ │ unking    │ │ unking   │
└─────────────┘ └─────────┘ └───────────┘ └──────────┘
```

### Classe `Chunk` (output)

```python
@dataclass
class Chunk:
    """Représente un chunk avec métadonnées."""
    text: str
    index: int
    total_chunks: int
    token_count: int
    metadata: Dict[str, Any]

    # Section metadata (si applicable)
    section_title: Optional[str] = None
    section_level: Optional[str] = None  # H1, H2, H3
    section_number: Optional[str] = None  # "2.3.1"
    parent_section: Optional[str] = None

    # Content type
    content_type: str = "text"  # text, list, table, code
```

---

## 💻 Implémentation détaillée

### 1. Interface abstraite `ChunkingStrategy`

**Fichier** : `backend/app/services/chunking/base.py` (nouveau)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import tiktoken

@dataclass
class Chunk:
    """Chunk with enriched metadata."""
    text: str
    index: int
    total_chunks: int
    token_count: int
    metadata: Dict[str, Any]

    # Section metadata
    section_title: Optional[str] = None
    section_level: Optional[str] = None
    section_number: Optional[str] = None
    parent_section: Optional[str] = None

    # Content type
    content_type: str = "text"

class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    def __init__(
        self,
        target_chunk_size: int = 512,
        max_chunk_size: int = 1024,
        overlap: int = 50,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize chunking strategy.

        Args:
            target_chunk_size: Target tokens per chunk
            max_chunk_size: Maximum tokens per chunk
            overlap: Overlap in tokens between chunks
            encoding_name: tiktoken encoding (cl100k_base for OpenAI)
        """
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

        # Initialize tiktoken encoder
        self.encoder = tiktoken.get_encoding(encoding_name)

    def get_token_count(self, text: str) -> int:
        """
        Count tokens using tiktoken (exact for OpenAI).

        Args:
            text: Input text

        Returns:
            Token count
        """
        return len(self.encoder.encode(text))

    @abstractmethod
    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into chunks with strategy-specific logic.

        Args:
            text: Text to chunk
            metadata: Base metadata to include in all chunks

        Returns:
            List of Chunk objects
        """
        pass

    def _create_chunk(
        self,
        text: str,
        index: int,
        total_chunks: int,
        base_metadata: Dict[str, Any]
    ) -> Chunk:
        """
        Helper to create Chunk object with common metadata.

        Args:
            text: Chunk text
            index: Chunk index (0-based)
            total_chunks: Total number of chunks
            base_metadata: Base metadata dict

        Returns:
            Chunk object
        """
        return Chunk(
            text=text,
            index=index,
            total_chunks=total_chunks,
            token_count=self.get_token_count(text),
            metadata=base_metadata
        )
```

---

### 2. Stratégie `FixedChunkingStrategy` (fallback)

**Fichier** : `backend/app/services/chunking/fixed.py` (nouveau)

```python
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk

class FixedChunkingStrategy(ChunkingStrategy):
    """
    Fixed-size chunking with token-based overlap.

    Use case: Fallback for unstructured text.
    """

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text into fixed-size chunks with overlap.

        Algorithm:
        1. Tokenize entire text
        2. Create chunks of target_chunk_size tokens
        3. Add overlap tokens from previous chunk
        4. Generate Chunk objects

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        metadata = metadata or {}

        # Tokenize entire text
        tokens = self.encoder.encode(text)

        chunks = []
        start = 0

        while start < len(tokens):
            # Extract chunk tokens
            end = min(start + self.target_chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]

            # Decode tokens back to text
            chunk_text = self.encoder.decode(chunk_tokens)

            chunks.append(chunk_text)

            # Move start with overlap
            start = end - self.overlap

        # Create Chunk objects
        return [
            self._create_chunk(
                text=chunk_text,
                index=idx,
                total_chunks=len(chunks),
                base_metadata={
                    **metadata,
                    "chunking_strategy": "fixed",
                    "chunk_size_tokens": self.target_chunk_size,
                    "overlap_tokens": self.overlap
                }
            )
            for idx, chunk_text in enumerate(chunks)
        ]
```

---

### 3. Stratégie `SectionChunkingStrategy` (hiérarchie)

**Fichier** : `backend/app/services/chunking/section.py` (nouveau)

```python
import re
from typing import List, Dict, Any, Optional, Tuple
from .base import ChunkingStrategy, Chunk

class SectionChunkingStrategy(ChunkingStrategy):
    """
    Section-based chunking for hierarchical documents.

    Use case: past_proposal, case_study, documentation

    Algorithm:
    1. Detect headers (Markdown # ## ### or numbered 1. 1.1 1.1.1)
    2. Split by sections (H1, H2, or H3 depending on size)
    3. If section > max_chunk_size, split recursively
    4. Include section title in each chunk
    5. Extract section metadata (title, level, number, parent)
    """

    # Regex patterns
    MARKDOWN_HEADER_PATTERN = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
    NUMBERED_HEADER_PATTERN = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)$', re.MULTILINE)

    def __init__(
        self,
        target_chunk_size: int = 512,
        max_chunk_size: int = 1024,
        overlap: int = 50,
        encoding_name: str = "cl100k_base",
        split_level: str = "auto"  # auto, H1, H2, H3
    ):
        """
        Initialize section-based chunking.

        Args:
            target_chunk_size: Target tokens per chunk
            max_chunk_size: Maximum tokens per chunk
            overlap: Overlap in tokens
            encoding_name: tiktoken encoding
            split_level: At which header level to split (auto, H1, H2, H3)
        """
        super().__init__(target_chunk_size, max_chunk_size, overlap, encoding_name)
        self.split_level = split_level

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text by sections with hierarchy detection.

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List of Chunk objects with section metadata
        """
        metadata = metadata or {}

        # 1. Detect all sections
        sections = self._detect_sections(text)

        # 2. Determine split level (auto-detect if needed)
        if self.split_level == "auto":
            split_level = self._auto_detect_split_level(sections)
        else:
            split_level = self.split_level

        # 3. Split by sections at chosen level
        chunks = []
        for section in sections:
            if section['level'] == split_level or split_level == "all":
                section_chunks = self._chunk_section(section, metadata)
                chunks.extend(section_chunks)

        # 4. Update total_chunks count
        for idx, chunk in enumerate(chunks):
            chunk.index = idx
            chunk.total_chunks = len(chunks)

        return chunks

    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect all sections (Markdown or numbered).

        Args:
            text: Input text

        Returns:
            List of section dicts with:
            - level: H1, H2, H3
            - title: Section title
            - number: Section number (if numbered)
            - start_pos: Start position in text
            - end_pos: End position in text
            - content: Section content
        """
        sections = []

        # Try Markdown headers first
        markdown_matches = list(self.MARKDOWN_HEADER_PATTERN.finditer(text))

        if markdown_matches:
            for i, match in enumerate(markdown_matches):
                level = f"H{len(match.group(1))}"  # # -> H1, ## -> H2
                title = match.group(2).strip()
                start_pos = match.start()

                # End position is start of next header or end of text
                end_pos = (
                    markdown_matches[i + 1].start()
                    if i + 1 < len(markdown_matches)
                    else len(text)
                )

                content = text[start_pos:end_pos].strip()

                sections.append({
                    'level': level,
                    'title': title,
                    'number': None,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'content': content
                })

        # Try numbered headers (1. 1.1 1.1.1)
        else:
            numbered_matches = list(self.NUMBERED_HEADER_PATTERN.finditer(text))

            for i, match in enumerate(numbered_matches):
                number = match.group(1)
                title = match.group(2).strip()

                # Determine level from number depth
                depth = number.count('.') + 1
                level = f"H{min(depth, 3)}"

                start_pos = match.start()
                end_pos = (
                    numbered_matches[i + 1].start()
                    if i + 1 < len(numbered_matches)
                    else len(text)
                )

                content = text[start_pos:end_pos].strip()

                sections.append({
                    'level': level,
                    'title': title,
                    'number': number,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'content': content
                })

        # If no sections detected, treat whole text as single section
        if not sections:
            sections.append({
                'level': 'H1',
                'title': 'Document',
                'number': None,
                'start_pos': 0,
                'end_pos': len(text),
                'content': text
            })

        return sections

    def _auto_detect_split_level(self, sections: List[Dict]) -> str:
        """
        Auto-detect optimal split level based on section sizes.

        Strategy:
        - If H2 sections average ~512 tokens -> split at H2
        - If H2 too large -> split at H3
        - If H3 too large -> split at all levels

        Args:
            sections: List of detected sections

        Returns:
            Split level (H1, H2, H3, all)
        """
        # Count sections by level
        h2_sections = [s for s in sections if s['level'] == 'H2']
        h3_sections = [s for s in sections if s['level'] == 'H3']

        # Calculate average tokens per H2 section
        if h2_sections:
            avg_h2_tokens = sum(
                self.get_token_count(s['content']) for s in h2_sections
            ) / len(h2_sections)

            if avg_h2_tokens <= self.max_chunk_size:
                return 'H2'

        # Calculate average tokens per H3 section
        if h3_sections:
            avg_h3_tokens = sum(
                self.get_token_count(s['content']) for s in h3_sections
            ) / len(h3_sections)

            if avg_h3_tokens <= self.max_chunk_size:
                return 'H3'

        # Fallback: split at all levels
        return 'all'

    def _chunk_section(
        self,
        section: Dict[str, Any],
        base_metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Chunk a single section.

        If section fits in max_chunk_size -> single chunk
        Otherwise -> split recursively with overlap

        Args:
            section: Section dict
            base_metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        content = section['content']
        token_count = self.get_token_count(content)

        chunks = []

        # Case 1: Section fits in single chunk
        if token_count <= self.max_chunk_size:
            chunk = Chunk(
                text=content,
                index=0,  # Will be updated later
                total_chunks=0,  # Will be updated later
                token_count=token_count,
                metadata={
                    **base_metadata,
                    "chunking_strategy": "section"
                },
                section_title=section['title'],
                section_level=section['level'],
                section_number=section['number'],
                content_type="section"
            )
            chunks.append(chunk)

        # Case 2: Section too large, split with overlap
        else:
            # Tokenize section
            tokens = self.encoder.encode(content)

            start = 0
            chunk_idx = 0

            while start < len(tokens):
                end = min(start + self.target_chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = self.encoder.decode(chunk_tokens)

                chunk = Chunk(
                    text=chunk_text,
                    index=chunk_idx,
                    total_chunks=0,  # Will be updated later
                    token_count=len(chunk_tokens),
                    metadata={
                        **base_metadata,
                        "chunking_strategy": "section",
                        "section_split": True,
                        "section_part": f"{chunk_idx + 1}"
                    },
                    section_title=section['title'],
                    section_level=section['level'],
                    section_number=section['number'],
                    content_type="section_part"
                )

                chunks.append(chunk)
                chunk_idx += 1
                start = end - self.overlap

        return chunks
```

---

### 4. Stratégie `SemanticChunkingStrategy` (paragraphes)

**Fichier** : `backend/app/services/chunking/semantic.py` (nouveau)

```python
import re
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk

class SemanticChunkingStrategy(ChunkingStrategy):
    """
    Semantic chunking by paragraphs and lists.

    Use case: certification, short structured documents

    Algorithm:
    1. Split by paragraph boundaries (2+ newlines)
    2. Detect lists (- bullet, 1. numbered)
    3. Group paragraphs to reach target_chunk_size
    4. Never split within paragraph or list
    """

    # Paragraph separator (2+ newlines)
    PARAGRAPH_SEPARATOR = re.compile(r'\n{2,}')

    # List patterns
    BULLET_LIST_PATTERN = re.compile(r'^[\-\*\+]\s+', re.MULTILINE)
    NUMBERED_LIST_PATTERN = re.compile(r'^\d+\.\s+', re.MULTILINE)

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Split text by semantic paragraphs.

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        metadata = metadata or {}

        # 1. Split into paragraphs
        paragraphs = self._split_paragraphs(text)

        # 2. Detect content types (text, list, table)
        typed_paragraphs = [
            {
                'text': p,
                'type': self._detect_content_type(p),
                'tokens': self.get_token_count(p)
            }
            for p in paragraphs
        ]

        # 3. Group paragraphs into chunks
        chunks = self._group_paragraphs(typed_paragraphs, metadata)

        return chunks

    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs.

        Args:
            text: Input text

        Returns:
            List of paragraphs
        """
        paragraphs = self.PARAGRAPH_SEPARATOR.split(text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _detect_content_type(self, paragraph: str) -> str:
        """
        Detect content type of paragraph.

        Args:
            paragraph: Paragraph text

        Returns:
            Content type (text, bullet_list, numbered_list, table)
        """
        # Check for bullet lists
        if self.BULLET_LIST_PATTERN.search(paragraph):
            return "bullet_list"

        # Check for numbered lists
        if self.NUMBERED_LIST_PATTERN.search(paragraph):
            return "numbered_list"

        # Check for table (simple heuristic: contains |)
        if '|' in paragraph and paragraph.count('|') >= 4:
            return "table"

        return "text"

    def _group_paragraphs(
        self,
        paragraphs: List[Dict[str, Any]],
        base_metadata: Dict[str, Any]
    ) -> List[Chunk]:
        """
        Group paragraphs into chunks targeting chunk_size.

        Algorithm:
        - Start with empty chunk
        - Add paragraphs until target_chunk_size reached
        - If single paragraph > max_chunk_size, split it (fallback)

        Args:
            paragraphs: List of paragraph dicts
            base_metadata: Base metadata

        Returns:
            List of Chunk objects
        """
        chunks = []
        current_chunk_paragraphs = []
        current_chunk_tokens = 0

        for para in paragraphs:
            # Case 1: Adding paragraph keeps chunk under target
            if current_chunk_tokens + para['tokens'] <= self.target_chunk_size:
                current_chunk_paragraphs.append(para)
                current_chunk_tokens += para['tokens']

            # Case 2: Adding would exceed target -> finish current chunk
            else:
                if current_chunk_paragraphs:
                    chunk_text = "\n\n".join(p['text'] for p in current_chunk_paragraphs)
                    content_types = list(set(p['type'] for p in current_chunk_paragraphs))

                    chunks.append(
                        Chunk(
                            text=chunk_text,
                            index=len(chunks),
                            total_chunks=0,  # Updated later
                            token_count=current_chunk_tokens,
                            metadata={
                                **base_metadata,
                                "chunking_strategy": "semantic",
                                "paragraph_count": len(current_chunk_paragraphs)
                            },
                            content_type=content_types[0] if len(content_types) == 1 else "mixed"
                        )
                    )

                # Start new chunk with current paragraph
                current_chunk_paragraphs = [para]
                current_chunk_tokens = para['tokens']

        # Add last chunk
        if current_chunk_paragraphs:
            chunk_text = "\n\n".join(p['text'] for p in current_chunk_paragraphs)
            content_types = list(set(p['type'] for p in current_chunk_paragraphs))

            chunks.append(
                Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    total_chunks=0,
                    token_count=current_chunk_tokens,
                    metadata={
                        **base_metadata,
                        "chunking_strategy": "semantic",
                        "paragraph_count": len(current_chunk_paragraphs)
                    },
                    content_type=content_types[0] if len(content_types) == 1 else "mixed"
                )
            )

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks
```

---

### 5. Stratégie `NoSplitChunkingStrategy` (templates)

**Fichier** : `backend/app/services/chunking/nosplit.py` (nouveau)

```python
from typing import List, Dict, Any, Optional
from .base import ChunkingStrategy, Chunk

class NoSplitChunkingStrategy(ChunkingStrategy):
    """
    No-split chunking for short documents.

    Use case: template (short reusable blocks)

    Algorithm:
    - If document < max_chunk_size -> single chunk
    - If document > max_chunk_size -> fallback to FixedChunkingStrategy
    """

    def chunk(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Return single chunk if possible, otherwise split.

        Args:
            text: Text to chunk
            metadata: Base metadata

        Returns:
            List with 1 Chunk (or more if text too large)
        """
        metadata = metadata or {}

        token_count = self.get_token_count(text)

        # Case 1: Fits in single chunk
        if token_count <= self.max_chunk_size:
            return [
                Chunk(
                    text=text,
                    index=0,
                    total_chunks=1,
                    token_count=token_count,
                    metadata={
                        **metadata,
                        "chunking_strategy": "nosplit"
                    },
                    content_type="template"
                )
            ]

        # Case 2: Too large, fallback to fixed chunking
        else:
            from .fixed import FixedChunkingStrategy

            fallback_strategy = FixedChunkingStrategy(
                target_chunk_size=self.target_chunk_size,
                max_chunk_size=self.max_chunk_size,
                overlap=self.overlap
            )

            chunks = fallback_strategy.chunk(text, metadata)

            # Update metadata to indicate fallback
            for chunk in chunks:
                chunk.metadata["chunking_strategy"] = "nosplit_fallback"

            return chunks
```

---

### 6. Factory et intégration dans `RAGService`

**Fichier** : `backend/app/services/chunking/factory.py` (nouveau)

```python
from typing import Dict, Type
from .base import ChunkingStrategy
from .fixed import FixedChunkingStrategy
from .section import SectionChunkingStrategy
from .semantic import SemanticChunkingStrategy
from .nosplit import NoSplitChunkingStrategy

# Strategy map by document type
CHUNKING_STRATEGY_MAP = {
    # Knowledge Base types
    "past_proposal": "section",
    "certification": "semantic",
    "case_study": "section",
    "documentation": "section",
    "template": "nosplit",

    # Future: Tender Archive (PHASE 6)
    "past_tender_won": "section",
    "past_tender_strategic": "section"
}

# Strategy class registry
STRATEGY_CLASSES: Dict[str, Type[ChunkingStrategy]] = {
    "fixed": FixedChunkingStrategy,
    "section": SectionChunkingStrategy,
    "semantic": SemanticChunkingStrategy,
    "nosplit": NoSplitChunkingStrategy
}

def get_chunking_strategy(
    document_type: str,
    **kwargs
) -> ChunkingStrategy:
    """
    Get appropriate chunking strategy for document type.

    Args:
        document_type: Type of document (past_proposal, certification, etc.)
        **kwargs: Strategy-specific parameters

    Returns:
        ChunkingStrategy instance
    """
    # Get strategy name from map (default to fixed)
    strategy_name = CHUNKING_STRATEGY_MAP.get(document_type, "fixed")

    # Get strategy class
    strategy_class = STRATEGY_CLASSES[strategy_name]

    # Instantiate with kwargs
    return strategy_class(**kwargs)
```

**Modification** : `backend/app/services/rag_service.py`

```python
# Add import at top
from app.services.chunking.factory import get_chunking_strategy
from app.services.chunking.base import Chunk

# Modify ingest_document method
async def ingest_document(
    self,
    db: AsyncSession,
    document_id: UUID,
    content: str,
    document_type: str,
    metadata: Dict[str, Any] | None = None
) -> int:
    """
    Ingest document into vector database with smart chunking.

    Args:
        db: Database session
        document_id: Unique document identifier
        content: Document content
        document_type: Type of document (past_proposal, certification, etc.)
        metadata: Additional metadata

    Returns:
        Number of chunks created
    """
    metadata = metadata or {}

    # PHASE 2: Use smart chunking strategy
    strategy = get_chunking_strategy(
        document_type=document_type,
        target_chunk_size=512,
        max_chunk_size=1024,
        overlap=50
    )

    chunks: List[Chunk] = strategy.chunk(content, metadata)

    count = 0
    for chunk in chunks:
        # Create embedding
        embedding = await self.create_embedding(chunk.text)

        # Store in database
        doc_embedding = DocumentEmbedding(
            document_id=document_id,
            document_type=document_type,
            chunk_text=chunk.text,
            embedding=embedding,
            metadata={
                **chunk.metadata,
                "chunk_index": chunk.index,
                "total_chunks": chunk.total_chunks,
                "token_count": chunk.token_count,
                "section_title": chunk.section_title,
                "section_level": chunk.section_level,
                "section_number": chunk.section_number,
                "content_type": chunk.content_type
            }
        )

        db.add(doc_embedding)
        count += 1

    await db.commit()
    logger.info(f"Ingested document {document_id} with {count} chunks using {strategy.__class__.__name__}")

    return count
```

---

## 🏷️ Métadonnées enrichies

### Schéma complet des métadonnées

```json
{
  // Core metadata
  "document_id": "uuid",
  "document_type": "past_proposal",
  "chunk_index": 3,
  "total_chunks": 10,
  "token_count": 487,

  // Chunking metadata
  "chunking_strategy": "section",
  "chunk_size_tokens": 512,
  "overlap_tokens": 50,

  // Section metadata (if applicable)
  "section_title": "Méthodologie Agile / SCRUM",
  "section_level": "H2",
  "section_number": "2.2",
  "parent_section": "2. Méthodologie proposée",

  // Content metadata
  "content_type": "section",  // text, section, list, table, code, template

  // Document-specific metadata (passed from ingestion)
  "source_file": "memoire_technique_defense_2024.pdf",
  "upload_date": "2024-09-15",
  "tags": ["agile", "scrum", "methodologie"],

  // Certification-specific (example)
  "certification_type": "ISO 27001",
  "valid_until": "2027-06-14",

  // Case study-specific (example)
  "client_sector": "defense",
  "technologies": ["VMware", "Veeam"]
}
```

### Utilisation des métadonnées pour filtrage

```python
# Exemple: Recherche uniquement dans sections "sécurité"
results = await rag_service.retrieve_relevant_content(
    db=db,
    query="processus gestion incidents sécurité",
    document_types=["documentation"],
    top_k=5,
    metadata_filters={
        "section_title__contains": "sécurité"  # SQL LIKE '%sécurité%'
    }
)
```

---

## 🧪 Plan de tests

### Tests unitaires (par stratégie)

**Fichier** : `backend/tests/test_chunking_strategies.py` (nouveau)

```python
import pytest
from app.services.chunking.fixed import FixedChunkingStrategy
from app.services.chunking.section import SectionChunkingStrategy
from app.services.chunking.semantic import SemanticChunkingStrategy
from app.services.chunking.nosplit import NoSplitChunkingStrategy

class TestFixedChunkingStrategy:
    """Test FixedChunkingStrategy."""

    def test_basic_chunking(self):
        """Test basic fixed-size chunking."""
        strategy = FixedChunkingStrategy(target_chunk_size=100, overlap=10)

        text = "word " * 500  # 500 words
        chunks = strategy.chunk(text)

        assert len(chunks) > 1
        assert all(chunk.token_count <= 150 for chunk in chunks)
        assert all(chunk.metadata["chunking_strategy"] == "fixed" for chunk in chunks)

    def test_overlap(self):
        """Test overlap between chunks."""
        strategy = FixedChunkingStrategy(target_chunk_size=50, overlap=10)

        text = "word " * 200
        chunks = strategy.chunk(text)

        # Verify overlap exists
        for i in range(len(chunks) - 1):
            chunk1_end = chunks[i].text[-50:]
            chunk2_start = chunks[i + 1].text[:50]

            # Some overlap should exist
            assert any(word in chunk2_start for word in chunk1_end.split())

class TestSectionChunkingStrategy:
    """Test SectionChunkingStrategy."""

    def test_markdown_header_detection(self):
        """Test Markdown header detection."""
        strategy = SectionChunkingStrategy()

        text = """
# Introduction

This is intro.

## Section 2.1

Content here.

### Subsection 2.1.1

More content.
"""

        chunks = strategy.chunk(text)

        # Verify section metadata
        assert any(chunk.section_level == "H1" for chunk in chunks)
        assert any(chunk.section_level == "H2" for chunk in chunks)
        assert any(chunk.section_title == "Section 2.1" for chunk in chunks)

    def test_numbered_header_detection(self):
        """Test numbered header detection."""
        strategy = SectionChunkingStrategy()

        text = """
1. Introduction

Intro content.

1.1 Background

Background content.

1.1.1 History

History content.
"""

        chunks = strategy.chunk(text)

        assert any(chunk.section_number == "1" for chunk in chunks)
        assert any(chunk.section_number == "1.1" for chunk in chunks)

    def test_large_section_splitting(self):
        """Test splitting of large sections."""
        strategy = SectionChunkingStrategy(target_chunk_size=100, max_chunk_size=150)

        # Create large section (500 words)
        text = f"# Large Section\n\n{'word ' * 500}"

        chunks = strategy.chunk(text)

        # Should split into multiple chunks
        assert len(chunks) > 1
        assert all(chunk.section_title == "Large Section" for chunk in chunks)
        assert all(chunk.token_count <= 150 for chunk in chunks)

class TestSemanticChunkingStrategy:
    """Test SemanticChunkingStrategy."""

    def test_paragraph_splitting(self):
        """Test splitting by paragraphs."""
        strategy = SemanticChunkingStrategy()

        text = """
First paragraph here.

Second paragraph here.

Third paragraph here.
"""

        chunks = strategy.chunk(text)

        assert len(chunks) >= 1
        assert all("\n\n" in chunk.text or len(chunks) == 1 for chunk in chunks)

    def test_list_detection(self):
        """Test list content type detection."""
        strategy = SemanticChunkingStrategy()

        text = """
- Item 1
- Item 2
- Item 3
"""

        chunks = strategy.chunk(text)

        assert chunks[0].content_type == "bullet_list"

    def test_no_split_within_paragraph(self):
        """Test that paragraphs are never split."""
        strategy = SemanticChunkingStrategy(target_chunk_size=50)

        text = """
This is a long paragraph that should not be split even though it exceeds the target chunk size because we want to preserve semantic boundaries.

This is another paragraph.
"""

        chunks = strategy.chunk(text)

        # Each chunk should contain complete paragraphs
        for chunk in chunks:
            # Shouldn't contain paragraph mid-split
            assert not chunk.text.startswith(" ")

class TestNoSplitChunkingStrategy:
    """Test NoSplitChunkingStrategy."""

    def test_short_document_single_chunk(self):
        """Test short document returns single chunk."""
        strategy = NoSplitChunkingStrategy()

        text = "Short template content here."
        chunks = strategy.chunk(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].content_type == "template"

    def test_large_document_fallback(self):
        """Test large document falls back to fixed chunking."""
        strategy = NoSplitChunkingStrategy(max_chunk_size=100)

        text = "word " * 500  # Large text
        chunks = strategy.chunk(text)

        # Should fallback to multiple chunks
        assert len(chunks) > 1
        assert all(chunk.metadata["chunking_strategy"] == "nosplit_fallback" for chunk in chunks)
```

### Tests d'intégration

**Fichier** : `backend/tests/test_rag_phase2_integration.py` (nouveau)

```python
import pytest
from app.services.rag_service import rag_service
from app.core.config import settings

@pytest.mark.asyncio
class TestRAGServicePhase2Integration:
    """Integration tests for PHASE 2 smart chunking."""

    async def test_ingest_past_proposal_with_sections(self, db_session):
        """Test ingesting past_proposal with section chunking."""

        content = """
# Mémoire Technique

## 1. Présentation entreprise

Notre entreprise spécialisée...

## 2. Méthodologie

### 2.1 Approche Agile

Nous utilisons Scrum...

### 2.2 Outils

GitLab, Jenkins, Docker...
"""

        chunk_count = await rag_service.ingest_document(
            db=db_session,
            document_id=uuid4(),
            content=content,
            document_type="past_proposal",
            metadata={"source": "test"}
        )

        assert chunk_count >= 3  # Sections detected

        # Verify embeddings created
        embeddings = await db_session.execute(
            select(DocumentEmbedding).where(
                DocumentEmbedding.document_type == "past_proposal"
            )
        )

        results = embeddings.scalars().all()

        # Verify section metadata
        assert any(e.metadata.get("section_title") == "Méthodologie" for e in results)
        assert any(e.metadata.get("section_level") == "H2" for e in results)

    async def test_semantic_search_with_section_filtering(self, db_session):
        """Test semantic search with section metadata filtering."""

        # 1. Ingest document
        content = """
# Documentation ITSM

## Sécurité

Processus gestion incidents sécurité...

## Infrastructure

Processus gestion serveurs...
"""

        await rag_service.ingest_document(
            db=db_session,
            document_id=uuid4(),
            content=content,
            document_type="documentation"
        )

        # 2. Search with section filter
        results = await rag_service.retrieve_relevant_content(
            db=db_session,
            query="gestion incidents",
            document_types=["documentation"],
            top_k=5
        )

        # 3. Verify results contain section metadata
        assert len(results) > 0
        assert any("section_title" in r["metadata"] for r in results)
```

---

## ❓ Questions critiques

Avant de passer à l'implémentation, voici les questions stratégiques à valider :

### 1. Taille de chunks

**Question** : Confirmer les tailles de chunks par type de document ?

| Document Type | Target Size | Max Size | Rationale |
|---------------|-------------|----------|-----------|
| `past_proposal` | 512 tokens | 1024 tokens | Sections moyennes |
| `certification` | 256 tokens | 512 tokens | Blocs courts |
| `case_study` | 512 tokens | 1024 tokens | Sections moyennes |
| `documentation` | 512 tokens | 1024 tokens | Procédures |
| `template` | N/A (unique) | 1024 tokens | Pas de split |

**Recommandation** : ✅ Valider ces tailles ou ajuster

---

### 2. Overlap

**Question** : Overlap uniforme (50 tokens) ou adaptatif par stratégie ?

**Options** :

- **A)** Overlap fixe : 50 tokens pour toutes stratégies
- **B)** Overlap adaptatif :
  - `section` : 100 tokens (contexte procédural important)
  - `semantic` : 0 token (paragraphes indépendants)
  - `fixed` : 50 tokens (fallback)

**Recommandation** : ✅ **Option B** (adaptatif)

---

### 3. Dépendances

**Question** : Ajouter `tiktoken` comme dépendance ?

**Impact** :

```bash
pip install tiktoken
```

**Alternative** : Continuer avec estimation (1 token ≈ 4 chars) - MOINS PRÉCIS

**Recommandation** : ✅ Ajouter `tiktoken` (précision critique)

---

### 4. Section detection

**Question** : Approche simple (regex) vs avancée (NLP) ?

**Options** :

- **A)** Regex uniquement (Markdown `#`, numérotation `1.`)
- **B)** + NLP (spaCy pour détecter titres par casse/position)

**Recommandation** : ✅ **Option A** pour PHASE 2 (simplicité)

- PHASE 2 : Regex
- Future : NLP si besoin (PHASE 7 optionnelle)

---

### 5. Métadonnées prioritaires

**Question** : Quels champs de métadonnées sont **critiques** pour la recherche ?

**Proposés** :

- ✅ `section_title` (filter par section)
- ✅ `section_level` (H1, H2, H3)
- ✅ `content_type` (text, list, table)
- ⚠️ `section_number` (optionnel)
- ⚠️ `parent_section` (optionnel)

**Recommandation** : Commencer avec les 3 critiques (✅), ajouter optionnels si besoin

---

### 6. Testing priority

**Question** : Quel type de document tester en priorité ?

**Recommandation** : ✅ **`past_proposal`** (use case #1, plus complexe)

Ordre de tests :

1. `past_proposal` (section chunking)
2. `certification` (semantic chunking)
3. `template` (nosplit chunking)

---

### 7. Backward compatibility

**Question** : Conserver l'ancienne méthode `chunk_text()` ?

**Recommandation** : ✅ OUI

- Marquer comme `@deprecated` avec warning
- Rediriger vers `FixedChunkingStrategy`
- Supprimer dans PHASE 3

```python
import warnings

def chunk_text(self, text: str) -> List[str]:
    """
    DEPRECATED: Use smart chunking strategies instead.

    This method will be removed in PHASE 3.
    """
    warnings.warn(
        "chunk_text() is deprecated. Use ingest_document() with smart chunking.",
        DeprecationWarning,
        stacklevel=2
    )

    # Fallback to FixedChunkingStrategy
    strategy = FixedChunkingStrategy(
        target_chunk_size=self.chunk_size,
        overlap=self.chunk_overlap
    )
    chunks = strategy.chunk(text)
    return [chunk.text for chunk in chunks]
```

---

## 📋 Récapitulatif : Prochaines étapes

### Tasks PHASE 2

| # | Task | Effort | Statut |
|---|------|--------|--------|
| 2.1 | Créer structure `chunking/` + base classes | 2h | ⏳ Pending |
| 2.2 | Implémenter `FixedChunkingStrategy` | 1h | ⏳ Pending |
| 2.3 | Implémenter `SectionChunkingStrategy` | 3h | ⏳ Pending |
| 2.4 | Implémenter `SemanticChunkingStrategy` | 2h | ⏳ Pending |
| 2.5 | Implémenter `NoSplitChunkingStrategy` | 1h | ⏳ Pending |
| 2.6 | Factory + intégration `RAGService` | 1h | ⏳ Pending |
| 2.7 | Tests unitaires + intégration | 3h | ⏳ Pending |
| **TOTAL** | | **13h** | |

---

*Dernière mise à jour: 2025-10-01*
*Version: 1.0 - Analyse approfondie PHASE 2*
