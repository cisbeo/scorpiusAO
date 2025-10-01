# 🎯 Plan détaillé d'implémentation - RAG Service (CORRIGÉ)

## 📋 Contexte et état actuel

### ✅ Ce qui existe déjà
- **Structure RAGService** avec méthodes async définies
- **Table `document_embeddings`** avec pgvector (Vector 1536 dimensions)
- **Chunking basique** (split par mots avec overlap)
- **Requêtes pgvector** écrites (cosine similarity)
- **API endpoints placeholders** (/search/semantic)
- **Table `criterion_suggestions`** pour stocker suggestions

### ⚠️ Ce qui manque (placeholders)
- **Appels OpenAI Embeddings** réels (actuellement non fonctionnels)
- **Version synchrone** pour Celery (comme LLMService)
- **Intégration dans pipeline** Celery (étape 6 uniquement)
- **Cache embeddings** (éviter régénération)
- **Chunking intelligent** (sections, sémantique vs. mots)
- **Reranking** (amélioration pertinence)
- **Endpoints implémentés** (search, suggestions)

---

## 🎯 Clarification : Rôle du RAG Service

### ✅ Ce que le RAG FAIT (Knowledge Base Core)

**Le RAG sert principalement à aider le bid manager à RÉDIGER sa réponse**

Le RAG recherche du contenu réutilisable dans la **Knowledge Base** :

1. **Réponses gagnantes passées** (`past_proposal`)
   - Mémoires techniques ayant remporté des marchés
   - Uploadées manuellement après gain

2. **Certifications** (`certification`)
   - ISO 27001, ISO 9001, HDS, Qualiopi
   - PDF certificats + processus associés

3. **Références clients** (`case_study`)
   - Études de cas détaillées
   - Success stories, témoignages

4. **Documentation interne** (`documentation`)
   - Processus ITSM, ITIL, DevOps
   - Méthodologies Agile, Scrum, PRINCE2
   - Fiches compétences équipes

5. **Templates pré-rédigés** (`template`)
   - Présentation entreprise
   - Description méthodologie type
   - Sections réutilisables

---

### 🔮 PHASE 6 : Extension Tender Embeddings (OPTIONNEL)

**Statut** : Planifié pour après PHASE 5

**Objectif** : Ingérer les tenders dans la KB pour intelligence compétitive

**Use Cases** :
- 🔍 Recherche de tenders similaires passés
- 📊 Analyse comparative multi-tenders par client
- 🎯 Détection de patterns de critères récurrents
- ⚠️ Alertes sur clauses contractuelles inhabituelles
- 📈 Intelligence métier (benchmarking, probabilité de gain)

**Types de documents ajoutés** :
- `past_tender_won` : Tenders gagnés (archivés)
- `past_tender_strategic` : Tenders stratégiques (archivés)

**Politique de rétention** :
```python
TENDER_RETENTION = {
    "active": 45 days,      # En cours de réponse
    "won": 2 years,         # Archivé si gagné
    "strategic": 2 years,   # Archivé si stratégique
    "lost": delete          # Supprimé si perdu
}
```

**Effort estimé** : 16h
- Task 6.1 : Type `past_tender` + métadonnées (4h)
- Task 6.2 : Politique de rétention automatique (6h)
- Task 6.3 : Endpoint `/tenders/similar` (6h)

**ROI estimé** :
- Coût : $0.12/an pour 100 tenders
- Gain : 2-3h/tender économisées
- Bénéfice : +10% taux de réussite

**Feature Flag** : `ENABLE_TENDER_EMBEDDINGS` (défaut: False)

---

## 📊 Récapitulatif effort (MISE À JOUR)

| Phase | Tâches | Effort (h) | Priorité | Statut |
|-------|--------|------------|----------|--------|
| **PHASE 1: Embedding Engine** | 4 | 12h | CRITIQUE | ✅ **COMPLÉTÉ** |
| **PHASE 2: Smart Chunking** | 7 | 13h | HAUTE | ✅ **COMPLÉTÉ** |
| **PHASE 3: Intégration Pipeline** | 2 | 12h | CRITIQUE | ⏳ Pending |
| **PHASE 4: API Endpoints** | 2 | 12h | HAUTE | ⏳ Pending |
| **PHASE 5: Reranking** | 2 | 10h | MOYENNE | ⏳ Pending |
| **PHASE 6: Tender Embeddings** | 3 | 16h | OPTIONNEL | 📋 Planifié |
| **TOTAL (Core)** | **17 tâches** | **59h** | **7 jours** | **42% complété** |
| **TOTAL (avec PHASE 6)** | **20 tâches** | **75h** | **9 jours** | - |

**Progrès actuel** : PHASE 1 + PHASE 2 complétées (25h/59h = 42%)

---

## 🔄 Workflow complet (corrigé)

```
┌─────────────────────────────────────────────────────────┐
│              PHASE 1: TENDER ANALYSIS                    │
│            (Claude API - PAS de RAG)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 1. Upload documents tender (CCTP, RC, AE, BPU)         │
│ 2. Extract text (ParserService)                         │
│ 3. ✅ Analyse Claude API (résumé, risques, etc.)        │
│ 4. ✅ Extract criteria (critères d'évaluation)          │
│ 5. Find similar tenders (SQL métadonnées, PAS RAG)     │
│                                                          │
│ ❌ PAS d'embeddings des documents tender                │
│                                                          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│           PHASE 2: PROPOSAL GENERATION                   │
│          (RAG Service - Knowledge Base)                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 6. ✅ Pour chaque critère:                              │
│    → Recherche RAG dans KNOWLEDGE BASE                  │
│      • past_proposals (réponses gagnantes)              │
│      • certifications (ISO 27001, HDS, etc.)            │
│      • case_studies (références clients)                │
│      • documentation (processus internes)               │
│    → Suggérer 3 paragraphes pertinents                  │
│    → Bid manager insère/adapte dans sa réponse          │
│                                                          │
│ 7. ✅ Recherche manuelle via UI:                        │
│    → Bid manager cherche "processus ITSM"               │
│    → RAG retourne chunks de la KB                       │
│    → Copier-coller dans éditeur                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Plan détaillé (les 56 heures sont décrites dans le document complet)

_[Le plan complet avec tout le code est disponible dans ce fichier]_

Pour la version complète avec le code détaillé de chaque phase, voir le fichier intégral.

## 🎯 Différences clés avec plan initial

### ❌ Ce qui a été SUPPRIMÉ

1. **Étape 2 du pipeline** : Création embeddings des documents tender
   - **Raison** : Documents tender analysés par Claude, pas besoin d'embeddings
   - **Économie** : ~$10-20 par tender en coûts embeddings

2. **Méthode `find_similar_tenders()` RAG-based**
   - **Raison** : Recherche métadonnées suffisante et plus rapide
   - **Simplification** : SQL simple vs. recherche vectorielle

### ✅ Ce qui a été CLARIFIÉ

1. **KB = Knowledge Base UNIQUEMENT**
   - past_proposal, certification, case_study, documentation, template
   - ❌ PAS de documents tender (CCTP, RC, AE, BPU)

2. **RAG pour rédaction réponse, PAS pour analyse**
   - Analyse = Claude API (LLMService)
   - Rédaction = RAG (suggest content from KB)

3. **Pipeline Celery**
   - Étapes 1-5 : Analyse tender (Claude)
   - Étape 6 : Suggestions contenu (RAG sur KB)

---

---

## 📋 Détail PHASE 6 : Tender Embeddings (Extension)

### Task 6.1 : Nouveau type `past_tender` + métadonnées (4h)

**Objectif** : Permettre l'ingestion de tenders archivés dans la KB

**Modifications** :

1. **Étendre les types de documents** (`backend/app/core/config.py`)
```python
KNOWLEDGE_BASE_TYPES = [
    "past_proposal",
    "certification",
    "case_study",
    "documentation",
    "template"
]

TENDER_ARCHIVE_TYPES = [
    "past_tender_won",        # Tender gagné
    "past_tender_strategic"   # Tender stratégique (même si perdu)
]

ALL_DOCUMENT_TYPES = KNOWLEDGE_BASE_TYPES + TENDER_ARCHIVE_TYPES
```

2. **Métadonnées étendues pour tenders**
```python
{
    'document_id': tender_id,
    'document_type': 'past_tender_won',
    'client_name': 'Ministère de la Défense',
    'client_type': 'administration_centrale',
    'tender_value': 2_000_000,  # EUR
    'tender_duration': 24,      # mois
    'won': True,
    'win_date': '2024-06-15',
    'strategic': True,
    'sector': 'defense',
    'criteria_count': 45,
    'archived_at': datetime.now()
}
```

**Acceptance Criteria** :
- [ ] Types `past_tender_*` ajoutés
- [ ] Métadonnées étendues implémentées
- [ ] Filtrage par métadonnées fonctionne

---

### Task 6.2 : Politique de rétention automatique (6h)

**Objectif** : Gérer le cycle de vie des embeddings de tenders

**Implémentation** :

```python
# backend/app/services/tender_retention_service.py

from datetime import datetime, timedelta
from typing import Dict

class TenderRetentionService:
    """Gestion cycle de vie des tender embeddings."""

    RETENTION_POLICY = {
        'active': timedelta(days=45),
        'won': timedelta(days=730),        # 2 ans
        'strategic': timedelta(days=730),
        'lost': timedelta(days=0)          # Suppression immédiate
    }

    async def archive_tender(
        self,
        tender_id: str,
        won: bool,
        strategic: bool = False
    ):
        """Archive ou supprime tender selon policy."""

        if won or strategic:
            # Ingérer dans KB
            tender_type = 'past_tender_won' if won else 'past_tender_strategic'
            await rag_service.ingest_document(
                document_id=tender_id,
                content=tender.full_text,
                document_type=tender_type,
                metadata=self._build_metadata(tender)
            )
        else:
            # Supprimer (tender perdu, non stratégique)
            await self._delete_tender_embeddings(tender_id)

    async def cleanup_expired(self):
        """Cron job: supprimer tenders expirés."""
        expired = await db.execute(
            """
            SELECT document_id FROM document_embeddings
            WHERE document_type LIKE 'past_tender_%'
            AND archived_at < NOW() - INTERVAL '730 days'
            """
        )

        for row in expired:
            await self._delete_tender_embeddings(row.document_id)
```

**Cron Job** :
```python
# backend/app/tasks/cleanup_tasks.py

@celery_app.task
def cleanup_expired_tenders():
    """Exécuté chaque nuit à 2h."""
    retention_service.cleanup_expired()
```

**Acceptance Criteria** :
- [ ] Policy de rétention implémentée
- [ ] Archive automatique post-deadline
- [ ] Cleanup job fonctionne
- [ ] Logs des suppressions

---

### Task 6.3 : Endpoint `/tenders/similar` (6h)

**Objectif** : API pour rechercher tenders similaires

**Endpoint** :

```python
# backend/app/api/v1/endpoints/tenders.py

@router.get("/{tender_id}/similar", response_model=List[SimilarTenderResponse])
async def find_similar_tenders(
    tender_id: str,
    top_k: int = 5,
    filters: TenderFilters = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Recherche tenders similaires archivés.

    Use case: "Montrez-moi des tenders similaires qu'on a gagnés"
    """

    # 1. Récupérer tender actuel
    tender = await db.get(Tender, tender_id)

    # 2. Recherche sémantique dans tenders archivés
    similar = await rag_service.retrieve_relevant_content(
        db=db,
        query=tender.summary,
        document_types=['past_tender_won', 'past_tender_strategic'],
        top_k=top_k,
        filters={
            'client_name': filters.client,
            'sector': filters.sector,
            'won': True
        }
    )

    # 3. Enrichir avec nos proposals gagnantes
    results = []
    for tender_chunk in similar:
        archived_tender = await get_tender_by_id(tender_chunk['document_id'])
        our_proposal = await get_winning_proposal(archived_tender.id)

        results.append({
            'tender': archived_tender,
            'similarity_score': tender_chunk['similarity_score'],
            'our_winning_proposal': our_proposal,
            'reusable_sections': extract_reusable_sections(our_proposal)
        })

    return results
```

**Schémas** :

```python
# backend/app/schemas/tender.py

class SimilarTenderResponse(BaseModel):
    tender_id: UUID
    client_name: str
    tender_title: str
    similarity_score: float
    won: bool
    win_date: Optional[date]
    our_proposal_id: Optional[UUID]
    reusable_sections: List[ProposalSection]
```

**Acceptance Criteria** :
- [ ] Endpoint fonctionne
- [ ] Filtres par client/secteur opérationnels
- [ ] Retourne proposals gagnantes associées
- [ ] Tests API validés

---

## 🎯 Activation PHASE 6

**Feature Flag** :

```python
# backend/app/core/config.py

class Settings(BaseSettings):
    # ...

    # PHASE 6: Tender Embeddings
    enable_tender_embeddings: bool = Field(
        default=False,
        description="Enable tender archival in Knowledge Base"
    )
    tender_retention_days_won: int = 730
    tender_retention_days_strategic: int = 730
```

**Activation** :

```bash
# .env
ENABLE_TENDER_EMBEDDINGS=true
TENDER_RETENTION_DAYS_WON=730
TENDER_RETENTION_DAYS_STRATEGIC=730
```

**Tests d'intégration** :

```python
# backend/tests/test_tender_embeddings.py

async def test_tender_archival_workflow():
    """Test workflow complet archivage tender."""

    # 1. Créer tender
    tender = create_test_tender(client="Ministère X")

    # 2. Marquer comme gagné
    await retention_service.archive_tender(
        tender_id=tender.id,
        won=True,
        strategic=False
    )

    # 3. Vérifier embeddings créés
    embeddings = await get_embeddings(tender.id)
    assert len(embeddings) > 0
    assert embeddings[0].document_type == 'past_tender_won'

    # 4. Recherche similaires
    similar = await find_similar_tenders(
        tender_id=new_tender.id,
        filters={'client_name': 'Ministère X'}
    )

    assert tender.id in [s.tender_id for s in similar]
```

---

## 🎉 Changelog

### 2025-10-01 - Version 3.0 - PHASE 2 COMPLÉTÉE ✅

**PHASE 2: Smart Chunking - COMPLÉTÉ**

Implémentation complète des stratégies de chunking intelligent :

1. ✅ **Module `chunking/`** créé avec architecture modulaire
   - `base.py` : Classes abstraites `Chunk` et `ChunkingStrategy`
   - `fixed.py` : FixedChunkingStrategy (fallback)
   - `section.py` : SectionChunkingStrategy (H1-H3 regex detection)
   - `semantic.py` : SemanticChunkingStrategy (paragraphes)
   - `nosplit.py` : NoSplitChunkingStrategy (templates)
   - `factory.py` : Factory pattern avec mapping par document_type

2. ✅ **Dépendance tiktoken ajoutée** (Q3) : Token counting exact OpenAI

3. ✅ **Configuration validée** (Q1, Q2) :
   - `past_proposal`: 512/1024 tokens, overlap 100
   - `certification`: 256/512 tokens, overlap 0
   - `case_study`: 512/1024 tokens, overlap 100
   - `documentation`: 512/1024 tokens, overlap 100
   - `template`: N/A/1024 tokens, overlap 0

4. ✅ **Métadonnées enrichies** (Q5 - tous les 5 champs) :
   - `section_title`, `section_level`, `section_number`, `parent_section`, `content_type`

5. ✅ **Détection regex** (Q4) : Markdown (#, ##, ###) + numérotation (1., 1.1, 1.1.1)
   - 📝 **Note future (PHASE 7)** : Ajouter NLP (spaCy) pour détection avancée

6. ✅ **RAGService intégré** :
   - `ingest_document()` utilise smart chunking automatique
   - `chunk_text()` deprecated avec backward compatibility (Q7)

7. ✅ **Tests complets** :
   - 30+ tests unitaires (`test_chunking_strategies.py`)
   - 8 tests d'intégration (`test_rag_phase2_integration.py`)
   - Priorité Q6 : past_proposal > certification > template

**Effort réel** : 13h (7 tâches)
**Progrès global** : 42% (25h/59h core)

---

*Dernière mise à jour: 2025-10-01*
*Version 3.0 - PHASE 2: Smart Chunking complétée ✅*
*PHASE 1 ✅ | PHASE 2 ✅ | PHASE 3-5 ⏳ | PHASE 6 📋*
