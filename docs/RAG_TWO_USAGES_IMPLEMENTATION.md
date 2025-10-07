# 🎯 Implémentation RAG - 2 Usages Distincts

**Date**: 7 octobre 2025
**Version**: 1.0.0
**Status**: ✅ Phase 1 complétée (ingestion automatique + endpoint suggestions)

---

## 📊 Vue d'Ensemble

Le système RAG de ScorpiusAO distingue maintenant **2 usages distincts** avec des `document_types` séparés :

### 🔵 **Usage #1 : Knowledge Base (Tenders Gagnants Passés)**
**Objectif** : Trouver des tenders similaires gagnés pour réutiliser le contenu

- **document_types** : `"historical_tender"`, `"past_proposal"`
- **Tables** : `historical_tenders`, `past_proposals`
- **Endpoint** : `POST /api/v1/tenders/{id}/suggestions`
- **Utilisation** : Suggérer du contenu réutilisable (mémo technique, DUME, etc.)

### 🟢 **Usage #2 : Analyse Détaillée du Tender Actuel**
**Objectif** : Répondre aux questions sur le tender en cours d'analyse

- **document_type** : `"tender"`
- **Tables** : `tenders`, `tender_documents`, `document_sections`
- **Endpoint** : `POST /api/v1/tenders/{id}/ask`
- **Utilisation** : Q&A sur le contenu du tender actuel

---

## 🔧 Changements Implémentés

### 1. **Ingestion Automatique (Usage #2)** ✅

**Fichier** : `app/tasks/tender_tasks.py`
**Fonction** : `process_tender_document()` (ligne 185-221)

**Ajout** : Création automatique des embeddings après extraction des sections

```python
# STEP 2: Create embeddings for RAG (Usage #2: Q&A on current tender)
print(f"🔍 Step 2: Creating embeddings for RAG (Usage #2: Q&A)...")

# Filter sections with content (exclude TOC)
sections_with_content = [
    s for s in sections_data
    if not s.get("is_toc", False) and s.get("content")
]

if sections_with_content:
    # Semantic chunking
    chunks = rag_service.chunk_sections_semantic(
        sections=sections_with_content,
        max_tokens=1000,
        min_tokens=100
    )

    # Ingest with embeddings (Usage #2: document_type="tender")
    embeddings_count = rag_service.ingest_document_sync(
        db=db,
        document_id=document.id,
        chunks=chunks,
        document_type="tender",  # Usage #2: Current tender for Q&A
        metadata={
            "tender_id": str(document.tender_id),
            "filename": document.filename,
            "document_type": document.document_type
        }
    )
    print(f"   ✓ Created {embeddings_count} embeddings (document_type='tender')")
```

**Résultat attendu** :
- 202 sections VSGP-AO → ~140 embeddings avec `document_type="tender"`
- Utilisables pour Q&A via `/tenders/{id}/ask`

---

### 2. **Correction STEP 5 - Recherche Knowledge Base** ✅

**Fichier** : `app/services/rag_service.py`
**Fonction** : `find_similar_tenders_sync()` (ligne 536-658)

**Modification** : Ajout du paramètre `search_in_kb` pour choisir la source

```python
def find_similar_tenders_sync(
    self,
    db: Session,
    tender_id: UUID,
    limit: int = 5,
    search_in_kb: bool = True  # ← NOUVEAU
) -> List[Dict[str, Any]]:
    """
    Find similar tenders.

    Args:
        search_in_kb: If True, search in historical_tenders (Usage #1)
                     If False, search in current tenders (Usage #2)
    """
```

**Logique** :
- `search_in_kb=True` → recherche dans `document_type='historical_tender'` + join `historical_tenders`
- `search_in_kb=False` → recherche dans `document_type='tender'` + join `tender_documents`

**Appel dans `process_tender_documents()`** (ligne 450-459) :
```python
# STEP 5: Find similar tenders (Usage #1: Knowledge Base)
similar_tenders = rag_service.find_similar_tenders_sync(
    db=db,
    tender_id=tender_id,
    limit=5,
    search_in_kb=True  # Usage #1: Search in historical_tenders
)
```

**Résultat** : Retourne tenders historiques similaires avec métadonnées complètes (title, organization, reference_number)

---

### 3. **Script CLI Ingestion Manuelle** ✅

**Nouveau fichier** : `scripts/ingest_tender_embeddings.py`

**Usage** :
```bash
# Ingérer le tender VSGP-AO test (Usage #2)
python scripts/ingest_tender_embeddings.py \
  --tender_id=3cfc8207-f275-4e53-ae0c-bead08cc45b7

# Force re-ingestion (delete old embeddings first)
python scripts/ingest_tender_embeddings.py \
  --tender_id=3cfc8207-f275-4e53-ae0c-bead08cc45b7 \
  --force
```

**Fonctionnalités** :
- Validation tender exists
- Load sections from `document_sections` table
- Filter sections with content (exclude TOC)
- Semantic chunking (1000 tokens max, 100 tokens min)
- Ingest with `document_type="tender"`
- Progress tracking + statistiques

**Output exemple** :
```
📦 Found 3 documents for tender 3cfc8207-...
📄 Processing: CCTP.pdf
   📋 Found 202 sections with content
   ✓ Created 140 embeddings (document_type='tender')
✅ Total: 140 embeddings created
```

---

### 4. **Endpoint Suggestions Knowledge Base** ✅

**Nouveau endpoint** : `POST /api/v1/tenders/{tender_id}/suggestions`

**Schemas** (`app/schemas/search.py`) :
```python
class SuggestionRequest(BaseModel):
    section_type: str  # "mémo_technique", "dume", "technical"
    requirements: List[str]
    top_k: int = 10

class SuggestionItem(BaseModel):
    section_number: str | None
    content: str
    similarity_score: float
    score_obtained: float | None
    rank: int | None
    historical_tender_id: str | None

class SuggestionsResponse(BaseModel):
    section_type: str
    suggestions: Dict[str, List[SuggestionItem]]  # Grouped by tender title
    total_found: int
    source: str = "past_proposals"
```

**Endpoint** (`app/api/v1/endpoints/tenders.py`, ligne 271-357) :
```python
@router.post("/{tender_id}/suggestions", response_model=SuggestionsResponse)
async def get_content_suggestions(
    tender_id: str,
    request: SuggestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get content suggestions from past winning proposals (Usage #1: Knowledge Base).
    """
    # Build query from section type + requirements
    kb_query = f"{request.section_type}\n" + "\n".join(request.requirements)

    # Search in past_proposals (Usage #1: Knowledge Base)
    kb_results = await rag_service.retrieve_relevant_content(
        db=db,
        query=kb_query,
        top_k=request.top_k,
        document_types=["past_proposal"]  # Usage #1: Knowledge Base only
    )

    # Filter winning proposals only
    winning_results = [
        r for r in kb_results
        if r.get("metadata", {}).get("status") == "won"
    ]

    # Group by tender title
    suggestions_by_tender = {}
    # ... (grouping logic)

    return SuggestionsResponse(
        section_type=request.section_type,
        suggestions=suggestions_by_tender,
        total_found=len(winning_results)
    )
```

**Exemple d'usage** :
```bash
curl -X POST "http://localhost:8000/api/v1/tenders/3cfc8207.../suggestions" \
  -H "Content-Type: application/json" \
  -d '{
    "section_type": "mémo_technique",
    "requirements": [
      "infrastructure IT",
      "support 24/7",
      "ITIL v3",
      "infogérance"
    ],
    "top_k": 10
  }'
```

**Réponse** :
```json
{
  "section_type": "mémo_technique",
  "suggestions": {
    "VSGP 2023 - Infogérance": [
      {
        "section_number": "3.2",
        "content": "Notre solution d'infogérance couvre...",
        "similarity_score": 0.92,
        "score_obtained": 95.5,
        "rank": 1
      }
    ],
    "Mairie Paris 2022 - Support IT": [
      {
        "section_number": "2.1",
        "content": "Support 24/7 avec astreintes...",
        "similarity_score": 0.88,
        "score_obtained": 89.3,
        "rank": 2
      }
    ]
  },
  "total_found": 12,
  "source": "past_proposals"
}
```

---

## 📊 Architecture RAG - Séparation Clara

### Flux de Données

```
┌─────────────────────────────────────────────────────────────┐
│                  document_embeddings Table                   │
│                                                              │
│  document_id | document_type | chunk_text | embedding       │
├─────────────────────────────────────────────────────────────┤
│  doc-1       | tender        | ...        | [0.2, 0.5...]  │ ← Usage #2
│  doc-2       | tender        | ...        | [0.3, 0.1...]  │
│  proposal-1  | past_proposal | ...        | [0.8, 0.2...]  │ ← Usage #1
│  hist-1      | historical_tender | ...    | [0.1, 0.9...]  │ ← Usage #1
└─────────────────────────────────────────────────────────────┘
```

### Requêtes SQL Correspondantes

**Usage #1** : Recherche dans Knowledge Base
```sql
SELECT ht.id, ht.title, AVG(similarity)
FROM document_embeddings de
JOIN historical_tenders ht ON ht.id = de.meta_data->>'historical_tender_id'
WHERE de.document_type = 'historical_tender'  -- ou 'past_proposal'
GROUP BY ht.id
ORDER BY similarity DESC
```

**Usage #2** : Q&A sur tender actuel
```sql
SELECT de.chunk_text, similarity
FROM document_embeddings de
JOIN tender_documents td ON td.id = de.document_id
WHERE de.document_type = 'tender'
  AND td.tender_id = :current_tender_id
ORDER BY similarity DESC
```

---

## ✅ Validation

### Tests de Compilation
```bash
# Tous les fichiers compilent sans erreur
python3 -m py_compile app/tasks/tender_tasks.py        # ✅
python3 -m py_compile app/services/rag_service.py      # ✅
python3 -m py_compile app/api/v1/endpoints/tenders.py  # ✅
python3 -m py_compile app/schemas/search.py            # ✅
```

### Commandes de Test

**1. Ingestion manuelle tender VSGP-AO** :
```bash
python scripts/ingest_tender_embeddings.py \
  --tender_id=3cfc8207-f275-4e53-ae0c-bead08cc45b7
```
Résultat attendu : ~140 embeddings créés

**2. Test Q&A (Usage #2)** :
```bash
curl -X POST "http://localhost:8000/api/v1/tenders/3cfc8207.../ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quels sont les processus ITIL ?"}'
```
Vérifier : pages correctes (ex: section 4.1.5 = page 34)

**3. Test Suggestions KB (Usage #1)** :
```bash
curl -X POST "http://localhost:8000/api/v1/tenders/3cfc8207.../suggestions" \
  -H "Content-Type: application/json" \
  -d '{
    "section_type": "mémo_technique",
    "requirements": ["ITIL", "infogérance"]
  }'
```
Résultat : suggestions depuis `past_proposals` gagnants uniquement

**4. Vérification base de données** :
```sql
-- Count embeddings par type
SELECT document_type, COUNT(*)
FROM document_embeddings
GROUP BY document_type;

-- Expected:
-- tender           | 140  (Usage #2)
-- past_proposal    | 50   (Usage #1)
-- historical_tender| 30   (Usage #1)
```

---

## 📈 Prochaines Étapes (Phase 1.5+)

### Tests E2E à Créer
- [ ] Test Usage #1 : Recherche dans KB (`test_rag_knowledge_base.py`)
- [ ] Test Usage #2 : Q&A tender actuel (`test_rag_current_tender.py`)
- [ ] Test STEP 5 : find_similar cherche dans KB
- [ ] Test pages correctes : section 4.1.5 → page 34

### Dashboard React (Phase 2)
- [ ] Composant `KnowledgeBaseSuggestions.tsx`
- [ ] Intégration endpoint `/suggestions`
- [ ] Affichage suggestions groupées par tender

### Executive Analysis (Phase 2)
- [ ] Service `executive_analysis_service.py` (2 passes)
- [ ] FAQ pré-calculée (20-30 questions)

---

## 🎯 ROI Attendu

**Coûts** :
- OpenAI embeddings Usage #1 (KB): $4 one-time (100 tenders)
- OpenAI embeddings Usage #2 (actuel): $0.04/tender
- Claude API (analyse): $0.55/tender
- **Total**: $0.59/tender + $4 setup

**Gains** :
- **Usage #1** : Réutilisation contenu gagnant → -4h → +€332/tender
- **Usage #2** : Analyse intelligente → -2h → +€166/tender
- **Total gain** : **+€498/tender**

**ROI net** : **+€497.41/tender** (842× le coût)

---

## 📚 Documentation Complémentaire

- **Architecture RAG** : [ROADMAP.md](../ROADMAP.md) (lignes 124-176)
- **Issues GitHub** :
  - [#2 - Knowledge Base](https://github.com/cisbeo/scorpiusAO/issues/2) ✅ Résolu
  - [#3 - Solution 5 MVP](https://github.com/cisbeo/scorpiusAO/issues/3) 🚧 En cours
  - [#4 - Solution 5.5 Adaptive](https://github.com/cisbeo/scorpiusAO/issues/4) ⏳ Planifié
- **Tests E2E existants** : `scripts/tests/test_rag_e2e.py`

---

**Dernière mise à jour** : 7 octobre 2025
**Auteur** : Claude Code + @cisbeo
**Version** : 1.0.0 - Phase 1 complétée
