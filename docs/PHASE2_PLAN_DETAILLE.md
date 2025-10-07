# Phase 2 - Plan Détaillé de Développement

**Date**: 7 octobre 2025
**Version**: 2.1.0 (Mise à jour avec gestion timeouts)
**Durée estimée**: 6-7 semaines
**Status**: 📋 Planifié

**🆕 Nouveautés Version 2.1**:
- ✅ Système de gestion des timeouts avec rollback automatique
- ✅ Notifications utilisateur temps réel (WebSocket + Email)
- ✅ Monitoring préventif des quotas API (alertes à 80%)
- ✅ Endpoint retry intelligent avec recommandations
- ✅ Architecture complète documentée dans [ARCHITECTURE_TIMEOUT_MANAGEMENT.md](ARCHITECTURE_TIMEOUT_MANAGEMENT.md)

---

## 📋 Executive Summary

La Phase 2 vise à **optimiser, compléter et stabiliser** le système ScorpiusAO sur la base des résultats validés de la Phase 1. Focus sur:

1. **Performance** - Réduire temps d'ingestion de 6 min à < 30s
2. **Complétude** - Activer Usage #1 (Knowledge Base)
3. **Qualité** - Mesurer et améliorer Recall@5, MRR, NDCG
4. **Stabilité** - Tests automatisés et monitoring
5. **🆕 Robustesse** - Gestion timeouts avec rollback et retry intelligent

### Résultats Phase 1 à Améliorer

| Métrique | Phase 1 (Actuel) | Phase 2 (Objectif) | Gain |
|----------|------------------|-------------------|------|
| **Temps ingestion** | 6 min (92 embeddings) | < 30s | **92%** |
| **Documents ingérés** | 1/4 (CCTP.pdf seulement) | 4/4 (tous) | **300%** |
| **Confidence Q&A** | 50-65% | 75-85% | **+15-20pts** |
| **Recall@5** | Non mesuré | > 80% | **Baseline** |
| **Coverage tests** | ~20% | > 80% | **+60pts** |

---

## 🎯 Objectifs Stratégiques Phase 2

### 1. **Performance & Scalabilité** (Priorité 1)

**Problème identifié**:
- Ingestion 92 embeddings prend 6 minutes (92 appels API séquentiels)
- Seul CCTP.pdf ingéré, CCAP.pdf et RC.pdf skipped (timeout)

**Objectifs**:
- ✅ Batch processing OpenAI (100 chunks/requête)
- ✅ Ingestion complète de tous les documents
- ✅ Temps total < 2 minutes pour 3 documents

**Métriques de succès**:
- Temps ingestion: **< 30 secondes** (vs 6 min actuellement)
- Documents ingérés: **100%** (vs 25% actuellement)
- Coût/tender: **< $0.05** (vs $0.14 actuellement)

---

### 2. **Knowledge Base - Usage #1** (Priorité 2)

**Problème identifié**:
- Endpoint `/suggestions` implémenté mais non testé
- Manque historical_tenders dans la base
- Pas de données pour valider la recherche KB

**Objectifs**:
- ✅ Ingérer 5+ tenders historiques gagnants
- ✅ Tester endpoint `/suggestions` avec données réelles
- ✅ Valider qualité des suggestions (pertinence, diversité)

**Métriques de succès**:
- Historical tenders: **≥ 5 tenders gagnants** ingérés
- Recall@10 (KB): **> 80%**
- Diversité suggestions: **≥ 3 tenders sources différents**

---

### 3. **Qualité & Tests** (Priorité 3)

**Problème identifié**:
- Recall@5, MRR, NDCG non mesurés
- Pas de jeu de données test (golden dataset)
- Coverage tests ~20%

**Objectifs**:
- ✅ Créer golden dataset (50 Q&A avec réponses attendues)
- ✅ Mesurer Recall@5, MRR, NDCG sur benchmark
- ✅ Tests unitaires + intégration (coverage > 80%)

**Métriques de succès**:
- Recall@5: **> 80%**
- MRR: **> 0.7**
- Test coverage: **> 80%**
- CI/CD: Tests auto sur PRs

---

### 4. **Parsing Tableaux** (Priorité 4)

**Problème identifié**:
- Tableaux complexes mal extraits (critères, SLA, pénalités)
- 3 solutions documentées mais non implémentées

**Objectifs**:
- ✅ Solution 1 (Enrichissement prompt) - Quick win
- ⏳ Solution 2 (Post-processing spatial) - Si temps
- ⏳ Solution 3 (Camelot) - Phase 3

**Métriques de succès**:
- Qualité extraction tableaux: **> 85%** (vs ~60% actuellement)
- Critères d'évaluation détectés: **100%**

---

### 5. **🆕 Gestion Timeouts & Retry** (Priorité 1 - CRITIQUE)

**Problème identifié**:
- Aucune gestion des timeouts API (OpenAI, Claude, PostgreSQL)
- Données partielles restent en base après échec
- Utilisateur non notifié des causes d'échec
- Pas de système de retry intelligent

**Objectifs**:
- ✅ Rollback automatique avec savepoints SQLAlchemy
- ✅ Notifications temps réel (WebSocket + Email)
- ✅ Monitoring préventif quotas (alertes 80%)
- ✅ Endpoint retry avec recommandations actionnables
- ✅ Diagnostics précis (quota, timeout, erreur réseau)

**Métriques de succès**:
- Rollback: **100%** des données après timeout
- Notifications: **< 5 secondes** après échec
- Warnings préventifs: **Alertes à 80%** quota
- Retry success rate: **> 90%** après correction
- Zéro corruption données

**Documentation**: Voir [ARCHITECTURE_TIMEOUT_MANAGEMENT.md](ARCHITECTURE_TIMEOUT_MANAGEMENT.md)

---

## 📅 Planning Détaillé (7 Semaines)

**🆕 Version 2.1**: Ajout de 1 semaine pour gestion timeouts & retry (Sprint 1 étendu à 3 semaines)

### Sprint 1: Performance, Ingestion & Gestion Timeouts (3 semaines)

**🆕 Changement majeur**: Sprint 1 passe de 2 à 3 semaines pour intégrer le système de gestion des timeouts, rollback et retry.

**Semaine 1: Batch Processing OpenAI**

**Objectif**: Réduire temps ingestion de 6 min à < 30s

**Tâches**:
1. **Refactoriser `RAGService.ingest_document_sync()`** (2 jours)
   - Remplacer appels séquentiels par batch processing
   - Grouper chunks par batch de 100 (limite OpenAI: 2048 inputs)
   - Gérer erreurs par batch avec retry
   ```python
   # Avant: 92 appels × ~4s = 6 minutes
   for chunk in chunks:
       embedding = openai.Embedding.create(input=chunk)

   # Après: 1 appel × 10s = 10 secondes
   batch_size = 100
   for i in range(0, len(chunks), batch_size):
       batch = chunks[i:i+batch_size]
       embeddings = openai.Embedding.create(input=batch)
   ```

2. **Implémenter connexion pool PostgreSQL** (1 jour)
   - SQLAlchemy pool avec pool_size=10, max_overflow=20
   - Réduire latence INSERT embeddings (bulk insert)

3. **Tests de performance** (1 jour)
   - Benchmark ingestion sur VSGP-AO (377 sections)
   - Mesurer temps par document (CCTP, CCAP, RC)
   - Valider coût total < $0.05

**Livrables**:
- ✅ Ingestion CCTP.pdf: < 10 secondes
- ✅ Temps total 3 documents: < 30 secondes
- ✅ Tests automatisés de performance

**Semaine 2: Ingestion Multi-Documents**

**Objectif**: Ingérer 100% des documents (vs 25% actuellement)

**Tâches**:
1. **Fixer logique ingestion `process_tender_documents()`** (1 jour)
   - Assurer que STEP 2 traite TOUS les documents
   - Ne pas skip CCAP.pdf, RC.pdf après CCTP.pdf
   - Logging détaillé par document

2. **Parallélisation documents** (2 jours)
   ```python
   from concurrent.futures import ThreadPoolExecutor

   with ThreadPoolExecutor(max_workers=3) as executor:
       futures = {
           executor.submit(ingest_doc, cctp): "CCTP",
           executor.submit(ingest_doc, ccap): "CCAP",
           executor.submit(ingest_doc, rc): "RC"
       }
       for future in as_completed(futures):
           doc_name = futures[future]
           print(f"✅ {doc_name} ingéré")
   ```

3. **Validation E2E complète** (1 jour)
   - Ré-ingérer tender VSGP-AO avec nouveau code
   - Vérifier 350+ embeddings créés (vs 92 actuellement)
   - Tester Q&A sur CCAP.pdf et RC.pdf

**Livrables**:
- ✅ 4/4 documents ingérés (100% vs 25%)
- ✅ 350+ embeddings créés
- ✅ Q&A fonctionne sur tous les documents

**🆕 Semaine 3: Gestion Timeouts, Rollback & Retry**

**Objectif**: Assurer robustesse du pipeline avec gestion erreurs et retry intelligent

**Tâches**:
1. **Créer exceptions custom** (0.5 jour)
   - Fichier: `backend/app/core/exceptions.py`
   - Classes: `OpenAITimeoutError`, `ClaudeTimeoutError`, `QuotaExceededError`, etc.
   - Attributs: message, error_code, details, recommendations
   - Méthode `to_dict()` pour sérialisation API

2. **Implémenter Transaction Service** (1.5 jours)
   - Fichier: `backend/app/services/transaction_service.py`
   - Méthode `savepoint()` context manager avec SQLAlchemy nested transactions
   - Méthode `track_progress()` pour observabilité pipeline
   - Méthode `clear_partial_data()` pour cleanup après timeout
   - Tests rollback sur exceptions simulées

3. **Créer Notification Service** (1 jour)
   - Fichier: `backend/app/services/notification_service.py`
   - Méthode `notify_timeout()` avec WebSocket + Email
   - Méthode `notify_quota_warning()` pour alertes préventives
   - Méthode `notify_retry_success()` après retry réussi
   - Templates email avec diagnostics et recommandations

4. **Implémenter Quota Monitor** (1.5 jours)
   - Fichier: `backend/app/services/quota_monitor.py`
   - Méthode `track_api_call()` avec Redis
   - Méthode `check_quota()` avant opérations coûteuses
   - Méthode `get_usage_report()` pour dashboard
   - Alertes automatiques à 80% usage

5. **Créer Endpoint Retry** (0.5 jour)
   - Fichier: `backend/app/api/v1/endpoints/retry.py`
   - POST `/tenders/{id}/retry` avec pre-checks
   - Analyse erreur précédente + recommandations
   - Validation quotas avant relance
   - Historique tentatives

6. **Intégrer au Pipeline Celery** (1 jour)
   - Wrapper `process_tender_documents()` avec savepoints
   - Ajout try/except avec gestion exceptions custom
   - Logs détaillés progrès (STEP X/6)
   - Tests E2E timeout → rollback → notification → retry

**Livrables**:
- ✅ Rollback automatique fonctionne (100% cas)
- ✅ Notifications < 5s après échec
- ✅ Endpoint retry avec diagnostics
- ✅ Tests coverage > 80% pour nouveau code
- ✅ Documentation [ARCHITECTURE_TIMEOUT_MANAGEMENT.md](ARCHITECTURE_TIMEOUT_MANAGEMENT.md)

---

### Sprint 2: Knowledge Base - Usage #1 (2 semaines)

**Semaine 4: Ingestion Historical Tenders**

**Objectif**: Créer la base de connaissances avec 5+ tenders gagnants

**Tâches**:
1. **Préparer 5 tenders historiques** (1 jour)
   - Sélectionner 5 tenders gagnés (secteur public IT)
   - Collecter documents: CCTP, CCAP, Mémo Technique
   - Anonymiser données sensibles (montants, dates)

2. **Script ingestion KB** (2 jours)
   ```bash
   python scripts/ingest_historical_tender.py \
     --tender_id=<uuid> \
     --status=won \
     --documents=CCTP.pdf,CCAP.pdf,MEMO.pdf \
     --metadata='{"score_obtained": 85.2, "rank": 1}'
   ```

   - Créer entrée `historical_tenders` avec métadonnées
   - Ingérer embeddings avec `document_type="historical_tender"`
   - Lier à `past_proposals` si mémo technique fourni

3. **Validation données KB** (1 jour)
   - Vérifier 5 tenders dans `historical_tenders`
   - Compter embeddings par tender (~300 chacun)
   - Tester recherche vectorielle sur KB

**Livrables**:
- ✅ 5 historical_tenders en base
- ✅ ~1500 embeddings KB créés
- ✅ Script CLI réutilisable

**Semaine 5: Endpoint Suggestions & Tests**

**Objectif**: Valider la qualité des suggestions KB

**Tâches**:
1. **Tests endpoint `/suggestions`** (2 jours)
   ```bash
   curl -X POST "/tenders/{id}/suggestions" -d '{
     "section_type": "memo_technique",
     "requirements": [
       "Gestion des changements selon ITIL",
       "CMDB et gestion des configurations",
       "Support niveau 1 et 2"
     ],
     "top_k": 10
   }'
   ```

   - Tester avec 10 requêtes types (méthodologie, processus, SLA)
   - Vérifier groupement par tender source
   - Valider filtrage `status="won"`

2. **Mesurer qualité suggestions** (2 jours)
   - **Recall@10**: % réponses pertinentes dans top-10
   - **Diversité**: Nombre de tenders sources distincts
   - **Pertinence**: Score similarité moyen

   Créer jeu de test:
   ```python
   test_cases = [
       {
           "query": "Processus ITIL requis",
           "expected_sections": ["4.1.5", "7.1"],  # Sections attendues
           "min_similarity": 0.7
       },
       # ... 20 test cases
   ]
   ```

3. **Documentation usage KB** (1 jour)
   - Guide utilisateur: Comment formuler requêtes
   - Exemples de suggestions obtenues
   - Best practices (nombre de requirements, formulation)

**Livrables**:
- ✅ Endpoint `/suggestions` validé
- ✅ Recall@10: > 80%
- ✅ Documentation utilisateur KB

---

### Sprint 3: Qualité & Tests Avancés (2 semaines)

**Semaine 6: Golden Dataset & Métriques**

**Objectif**: Mesurer objectivement la qualité du système Q&A

**Tâches**:
1. **Créer golden dataset** (2 jours)
   - 50 questions sur VSGP-AO avec réponses attendues
   - 10 questions par catégorie:
     - Processus techniques (ITIL, normes)
     - Critères d'évaluation
     - Pénalités et risques
     - Délais et planning
     - Exclusions et conditions

   Format:
   ```json
   {
     "question": "Quels sont les processus ITIL couverts ?",
     "expected_answer": {
       "sections": ["4.1.5", "7.1"],
       "keywords": ["Change Management", "CMDB", "Release Management"],
       "min_confidence": 0.6
     },
     "category": "processus_techniques"
   }
   ```

2. **Implémenter suite d'évaluation** (2 jours)
   ```python
   # scripts/evaluate_rag_quality.py
   def evaluate_recall_at_k(dataset, k=5):
       """Mesure % réponses correctes dans top-k"""

   def evaluate_mrr(dataset):
       """Mean Reciprocal Rank: 1/rang première bonne réponse"""

   def evaluate_ndcg(dataset):
       """Normalized Discounted Cumulative Gain: qualité classement"""
   ```

3. **Benchmarking** (1 jour)
   - Exécuter sur 50 questions
   - Générer rapport avec:
     - Recall@5, Recall@10
     - MRR
     - NDCG@5, NDCG@10
     - Temps moyen par question
     - Coût par question

**Livrables**:
- ✅ Golden dataset (50 Q&A)
- ✅ Rapport benchmark complet
- ✅ Métriques baseline établies

**Semaine 7: Tests Unitaires & CI/CD**

**Objectif**: Coverage > 80%, CI/CD automatisé

**Tâches**:
1. **Tests unitaires services** (2 jours)
   - `test_rag_service.py`: chunking, embeddings, recherche
   - `test_parser_service.py`: extraction PDF, structure
   - `test_llm_service.py`: prompts, cache, parsing réponses
   - Target: 80% coverage chaque service

2. **Tests intégration** (1 jour)
   - Pipeline E2E complet (upload → analyse → Q&A)
   - Tests avec mocks OpenAI/Anthropic (pas de coût)
   - Fixtures PostgreSQL avec données test

3. **CI/CD GitHub Actions** (1 jour)
   ```yaml
   # .github/workflows/tests.yml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       services:
         postgres:
           image: pgvector/pgvector:pg15
       steps:
         - uses: actions/checkout@v3
         - name: Run tests
           run: pytest --cov=app --cov-report=xml
         - name: Upload coverage
           uses: codecov/codecov-action@v3
         - name: Fail if coverage < 80%
           run: |
             coverage report --fail-under=80
   ```

**Livrables**:
- ✅ Coverage > 80%
- ✅ CI/CD GitHub Actions
- ✅ Tests automatiques sur PRs

---

## 🔧 Tâches Techniques Détaillées

### Task 1: Batch Processing OpenAI (Priorité 1)

**Fichier**: `app/services/rag_service.py`
**Méthode**: `ingest_document_sync()`
**Effort**: 2 jours

**Avant (Séquentiel)**:
```python
def ingest_document_sync(self, db, document_id, chunks, document_type, metadata):
    embeddings_created = 0

    for chunk in chunks:
        # 1 appel API par chunk → 92 appels = 6 minutes
        embedding_response = self.client.embeddings.create(
            input=chunk["text"],
            model="text-embedding-3-small"
        )
        embedding_vector = embedding_response.data[0].embedding

        # INSERT dans PostgreSQL
        db_embedding = DocumentEmbedding(
            document_id=document_id,
            chunk_text=chunk["text"],
            embedding=embedding_vector,
            document_type=document_type,
            meta_data=metadata
        )
        db.add(db_embedding)
        embeddings_created += 1

    db.commit()
    return embeddings_created
```

**Après (Batch)**:
```python
def ingest_document_sync(self, db, document_id, chunks, document_type, metadata):
    BATCH_SIZE = 100  # Limite OpenAI: 2048 inputs max
    embeddings_created = 0

    # Grouper chunks par batch
    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[i:i+BATCH_SIZE]
        batch_texts = [c["text"] for c in batch_chunks]

        try:
            # 1 appel API pour 100 chunks → 1 appel vs 100
            embedding_response = self.client.embeddings.create(
                input=batch_texts,  # Liste de textes
                model="text-embedding-3-small"
            )

            # Bulk insert dans PostgreSQL
            db_embeddings = []
            for j, chunk in enumerate(batch_chunks):
                embedding_vector = embedding_response.data[j].embedding

                db_embedding = DocumentEmbedding(
                    document_id=document_id,
                    chunk_text=chunk["text"],
                    embedding=embedding_vector,
                    document_type=document_type,
                    meta_data={**metadata, "chunk_index": i + j}
                )
                db_embeddings.append(db_embedding)

            db.bulk_save_objects(db_embeddings)
            embeddings_created += len(db_embeddings)

        except Exception as e:
            print(f"⚠️ Batch {i//BATCH_SIZE + 1} failed: {e}")
            # Retry batch individuellement en cas d'erreur
            for chunk in batch_chunks:
                # Fallback séquentiel pour ce batch
                pass

    db.commit()
    return embeddings_created
```

**Gains**:
- Temps: 6 min → 10-15 secondes (**-95%**)
- Appels API: 92 → 1 (**-99%**)
- Coût réseau: Réduit latence cumulée

---

### Task 2: Parallélisation Documents (Priorité 1)

**Fichier**: `app/tasks/tender_tasks.py`
**Méthode**: `process_tender_documents()`
**Effort**: 2 jours

**Avant (Séquentiel)**:
```python
def process_tender_documents(tender_id: UUID):
    # STEP 2: Créer embeddings pour CHAQUE document séquentiellement
    for document in documents:
        print(f"Processing {document.filename}...")

        # Extraction sections
        sections = extract_sections(document)

        # Chunking
        chunks = chunk_sections(sections)

        # Ingestion (6 minutes pour CCTP.pdf)
        embeddings_count = rag_service.ingest_document_sync(
            db, document.id, chunks, "tender", metadata
        )

        # Après CCTP.pdf (6 min), reste 0 min → timeout
        # CCAP.pdf et RC.pdf skipped
```

**Après (Parallèle)**:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_tender_documents(tender_id: UUID):
    # STEP 2: Créer embeddings pour TOUS documents en parallèle

    def ingest_single_document(document):
        """Ingérer un document (thread-safe)"""
        # Créer session DB par thread
        db = SessionLocal()
        try:
            sections = extract_sections(document)
            chunks = chunk_sections(sections)

            count = rag_service.ingest_document_sync(
                db, document.id, chunks, "tender", metadata
            )

            return {
                "filename": document.filename,
                "embeddings": count,
                "status": "success"
            }
        except Exception as e:
            return {
                "filename": document.filename,
                "error": str(e),
                "status": "failed"
            }
        finally:
            db.close()

    # Exécuter 3 documents en parallèle
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(ingest_single_document, doc): doc.filename
            for doc in documents
        }

        results = []
        for future in as_completed(futures):
            filename = futures[future]
            result = future.result()
            results.append(result)
            print(f"✅ {filename}: {result}")

    # Logs récapitulatifs
    total_embeddings = sum(r.get("embeddings", 0) for r in results)
    print(f"🎯 Total: {total_embeddings} embeddings pour {len(documents)} documents")
```

**Gains**:
- Temps: 3 × 10s = 30s en parallèle (vs 18s séquentiel théorique, mais pratique 6+ min avec timeouts)
- Fiabilité: Tous les documents ingérés
- Observabilité: Logs par document

---

### Task 3: Endpoint Suggestions Validation (Priorité 2)

**Fichier**: `app/api/v1/endpoints/tenders.py`
**Méthode**: `get_content_suggestions()`
**Effort**: 2 jours

**Tests à implémenter**:

```python
# tests/api/test_suggestions.py

def test_suggestions_basic(client, historical_tenders_fixture):
    """Test basique endpoint /suggestions"""
    response = client.post(
        f"/api/v1/tenders/{tender_id}/suggestions",
        json={
            "section_type": "memo_technique",
            "requirements": [
                "Gestion des changements selon ITIL",
                "CMDB et gestion des configurations"
            ],
            "top_k": 10
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Vérifications
    assert data["section_type"] == "memo_technique"
    assert len(data["suggestions"]) > 0
    assert data["total_found"] >= 3
    assert data["source"] == "past_proposals"

    # Vérifier groupement par tender
    for tender_title, items in data["suggestions"].items():
        assert len(items) > 0
        for item in items:
            assert item["similarity_score"] > 0.5
            assert "content" in item
            assert "historical_tender_id" in item


def test_suggestions_filtering_won_only(client, db_session):
    """Vérifier que seuls tenders gagnés sont retournés"""
    # Créer 2 tenders: 1 gagné, 1 perdu
    won_tender = HistoricalTender(status="won", ...)
    lost_tender = HistoricalTender(status="lost", ...)
    db_session.add_all([won_tender, lost_tender])
    db_session.commit()

    response = client.post(f"/api/v1/tenders/{tender_id}/suggestions", json={...})
    data = response.json()

    # Vérifier que seul won_tender apparaît
    historical_ids = [
        item["historical_tender_id"]
        for items in data["suggestions"].values()
        for item in items
    ]
    assert str(won_tender.id) in historical_ids
    assert str(lost_tender.id) not in historical_ids


def test_suggestions_diversity(client):
    """Vérifier diversité des sources"""
    response = client.post(f"/api/v1/tenders/{tender_id}/suggestions", json={
        "requirements": ["Support infrastructure IT"],
        "top_k": 10
    })
    data = response.json()

    # Nombre de tenders sources distincts
    tender_titles = list(data["suggestions"].keys())
    assert len(tender_titles) >= 3, "Au moins 3 tenders sources différents"


def test_suggestions_recall_at_10(client, golden_dataset):
    """Mesurer Recall@10"""
    correct_retrievals = 0
    total_queries = len(golden_dataset)

    for test_case in golden_dataset:
        response = client.post(f"/api/v1/tenders/{tender_id}/suggestions", json={
            "requirements": test_case["requirements"],
            "top_k": 10
        })
        data = response.json()

        # Vérifier si sections attendues présentes dans top-10
        all_sections = [
            item.get("section_number")
            for items in data["suggestions"].values()
            for item in items
        ]

        expected_sections = test_case["expected_sections"]
        if any(sec in all_sections for sec in expected_sections):
            correct_retrievals += 1

    recall_at_10 = correct_retrievals / total_queries
    assert recall_at_10 > 0.8, f"Recall@10 = {recall_at_10:.2%} (objectif: >80%)"
```

---

### Task 4: Golden Dataset Creation (Priorité 3)

**Fichier**: `tests/fixtures/golden_dataset.json`
**Effort**: 2 jours

**Structure**:
```json
{
  "dataset_version": "1.0",
  "tender_id": "3cfc8207-f275-4e53-ae0c-bead08cc45b7",
  "tender_title": "VSGP - Infogérance Infrastructure IT",
  "created_at": "2025-10-07",
  "questions": [
    {
      "id": "q001",
      "category": "processus_techniques",
      "question": "Quels sont les processus ITIL couverts dans le CCTP ?",
      "expected_answer": {
        "sections": ["4.1.5", "7.1", "4.1.5.9", "4.1.5.10"],
        "keywords": [
          "Change Management",
          "Configuration Management",
          "Release Management",
          "CMDB"
        ],
        "documents": ["CCTP.pdf"],
        "min_confidence": 0.6,
        "min_similarity": 0.65
      },
      "difficulty": "medium",
      "importance": "high"
    },
    {
      "id": "q002",
      "category": "criteres_evaluation",
      "question": "Quels sont les critères d'évaluation et leurs pondérations ?",
      "expected_answer": {
        "sections": ["6.1", "6.2"],
        "keywords": [
          "Prix",
          "Valeur technique",
          "Pondération",
          "Notation"
        ],
        "documents": ["RC.pdf"],
        "min_confidence": 0.5,
        "acceptable_not_found": true  # Info peut être absente
      },
      "difficulty": "hard",
      "importance": "critical"
    },
    {
      "id": "q003",
      "category": "penalites_risques",
      "question": "Quelles sont les pénalités financières en cas de non-respect des SLA ?",
      "expected_answer": {
        "sections": ["18.3", "18.1", "18.2"],
        "keywords": [
          "Pénalités",
          "SLA",
          "Niveau de service",
          "Palier"
        ],
        "documents": ["CCAP.pdf"],
        "min_confidence": 0.65,
        "expected_data_format": "table"  # Données structurées attendues
      },
      "difficulty": "medium",
      "importance": "high"
    }
    // ... 47 autres questions
  ]
}
```

**Catégories (10 questions chacune)**:
1. **processus_techniques**: ITIL, normes ISO, méthodologies
2. **criteres_evaluation**: Pondérations, notation, barèmes
3. **penalites_risques**: Pénalités, SLA, risques financiers
4. **delais_planning**: Dates limites, jalons, durées
5. **exclusions_conditions**: Motifs exclusion, conditions obligatoires

**Méthodologie de création**:
1. Lire manuellement VSGP-AO (3 documents)
2. Identifier 50 questions pertinentes pour bid manager
3. Noter sections sources et réponses attendues
4. Varier difficulté (easy 20%, medium 50%, hard 30%)
5. Valider avec expert métier (bid manager)

---

### Task 5: CI/CD Setup (Priorité 3)

**Fichiers**: `.github/workflows/*.yml`
**Effort**: 1 jour

**Workflow 1: Tests** (`.github/workflows/tests.yml`):
```yaml
name: Tests & Coverage

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s

      rabbitmq:
        image: rabbitmq:3-management-alpine
        options: >-
          --health-cmd "rabbitmq-diagnostics ping"
          --health-interval 10s

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run migrations
        run: |
          cd backend
          alembic upgrade head
        env:
          DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db

      - name: Run tests with coverage
        run: |
          cd backend
          pytest --cov=app --cov-report=xml --cov-report=term
        env:
          DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          RABBITMQ_URL: amqp://guest:guest@localhost:5672/
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          flags: backend

      - name: Fail if coverage < 80%
        run: |
          cd backend
          coverage report --fail-under=80
```

**Workflow 2: Linting** (`.github/workflows/lint.yml`):
```yaml
name: Linting

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install linters
        run: |
          pip install ruff black mypy

      - name: Run ruff
        run: |
          cd backend
          ruff check app/ --select=E,F,I

      - name: Run black
        run: |
          cd backend
          black --check app/

      - name: Run mypy
        run: |
          cd backend
          mypy app/ --ignore-missing-imports
```

**Workflow 3: E2E Tests** (`.github/workflows/e2e.yml`):
```yaml
name: E2E Tests

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  e2e:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: |
          docker compose up -d
          sleep 30  # Wait for services

      - name: Run E2E tests
        run: |
          cd backend
          python scripts/tests/run_full_suite.py

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-results
          path: backend/test_results/
```

---

## 📊 Métriques de Suivi Phase 2

### Dashboard Hebdomadaire

| Métrique | Baseline (Phase 1) | Semaine 1 | Semaine 2 | Semaine 3 | Semaine 4 | Semaine 5 | Semaine 6 | Objectif |
|----------|-------------------|-----------|-----------|-----------|-----------|-----------|-----------|----------|
| **Temps ingestion** | 6 min | | | | | | | < 30s |
| **Documents ingérés (%)** | 25% | | | | | | | 100% |
| **Embeddings créés** | 92 | | | | | | | 350+ |
| **Confidence Q&A moyenne** | 58% | | | | | | | 75%+ |
| **Recall@5** | N/A | | | | | | | > 80% |
| **MRR** | N/A | | | | | | | > 0.7 |
| **Historical tenders** | 0 | | | | | | | 5+ |
| **Test coverage** | ~20% | | | | | | | > 80% |

### KPIs de Succès

**Performance** (Sprint 1):
- ✅ Temps ingestion < 30s pour 3 documents
- ✅ 100% documents ingérés (vs 25%)
- ✅ Coût ingestion < $0.05/tender

**Fonctionnalité** (Sprint 2):
- ✅ 5+ historical_tenders ingérés
- ✅ Endpoint `/suggestions` opérationnel
- ✅ Recall@10 (KB) > 80%

**Qualité** (Sprint 3):
- ✅ Golden dataset (50 Q&A) créé
- ✅ Recall@5 > 80%
- ✅ MRR > 0.7
- ✅ Test coverage > 80%

---

## 💰 Budget Phase 2

### Coûts de Développement

| Poste | Effort | Coût Unitaire | Total |
|-------|--------|---------------|-------|
| **Dev Backend** | 7 semaines (+1) | $5,000/semaine | $35,000 |
| **🆕 Gestion Timeouts/Retry** | Inclus Sprint 1, Sem 3 | - | (Inclus ci-dessus) |
| **QA/Testing** | 1 semaine | $4,000/semaine | $4,000 |
| **DevOps** | 0.5 semaine | $5,000/semaine | $2,500 |
| **Total Dev** | | | **$41,500** |

**🆕 Détail ajout Semaine 3**:
- Exceptions custom + Transaction Service: 2 jours ($1,600)
- Notification Service + Quota Monitor: 2.5 jours ($2,000)
- Endpoint Retry + Integration: 1.5 jours ($1,200)
- Tests gestion timeouts: 1 jour ($800)
- **Sous-total Sem 3**: 7 jours = **$5,600** (inclus dans $35k ci-dessus)

### Coûts Opérationnels (Dev/Test)

| Service | Usage | Coût/Mois | Total 1.75 mois |
|---------|-------|-----------|-----------------|
| **OpenAI Embeddings** | Tests ingestion | $50 | $88 |
| **Anthropic Claude** | Tests Q&A | $100 | $175 |
| **Infrastructure AWS** | Dev/staging | $200 | $350 |
| **GitHub Actions** | CI/CD minutes | $50 | $88 |
| **🆕 Redis** | Quota tracking | $10 | $18 |
| **🆕 Email Service** | SendGrid/SES | $15 | $26 |
| **🆕 WebSocket** | Notifications | $25 | $44 |
| **Total Ops** | | | **$789** |

**Budget Total Phase 2**: **~$42,289** (vs $37,100 initial)

**Augmentation**: +$5,189 (+14%) pour système gestion timeouts

### ROI Attendu

**Gains Phase 2**:
- Performance: -95% temps ingestion → Support 10x plus de tenders
- Qualité: +15-20pts confidence → Moins de vérifications manuelles
- Complétude: Usage #1 KB → Suggestions automatiques (gain 30-50% temps rédaction)

**Estimation ROI**:
- Gain temps bid manager: 50 tenders/mois × 2h économisées × $50/h = **$5,000/mois**
- 🆕 Gain réduction erreurs: Moins de tenders perdus = **+$500/mois**
- ROI net: $5,500/mois - $1,100/mois (ops) = **$4,400/mois**
- **Retour sur investissement**: 10 mois (vs dev $42k)

**Justification coût additionnel gestion timeouts**:
- ✅ Évite perte de données (corruption base = €50k+ dommages)
- ✅ Améliore confiance utilisateur (+20% adoption)
- ✅ Réduit support technique (-2h/semaine = $400/mois)
- ✅ Permet scale (support 100+ tenders/mois vs 20 actuellement)

---

## 🚧 Risques & Mitigation

### Risque 1: Performance Batch Processing

**Risque**: Batch processing ne réduit pas suffisamment le temps

**Impact**: Moyen (objectif < 30s non atteint)

**Probabilité**: Faible (20%)

**Mitigation**:
- Tester batch size optimal (50, 100, 200)
- Monitoring temps par batch
- Fallback: Réduire chunk size (1000 → 500 tokens)

---

### Risque 2: Qualité Données Historical Tenders

**Risque**: Manque de tenders historiques de qualité

**Impact**: Élevé (Usage #1 KB non validé)

**Probabilité**: Moyenne (40%)

**Mitigation**:
- Identifier sources dès Sprint 1
- Contacter bid managers pour archives
- Fallback: Utiliser tenders publics BOAMP

---

### Risque 3: Recall@5 < 80%

**Risque**: Métriques qualité en-dessous objectif

**Impact**: Moyen (acceptance utilisateur réduite)

**Probabilité**: Moyenne (30%)

**Mitigation**:
- Fine-tuning embeddings sur domaine (appels d'offres IT)
- Améliorer chunking strategy
- Implémenter re-ranking (Cohere/Voyage)
- Enrichir prompt LLM Q&A

---

### Risque 4: Coverage Tests < 80%

**Risque**: Difficulté à atteindre coverage

**Impact**: Faible (report Sprint suivant)

**Probabilité**: Moyenne (40%)

**Mitigation**:
- Prioriser tests critiques (RAG, Parser, LLM)
- Accepter 70% si tests E2E solides
- Exclure du coverage: migrations, fixtures

---

## 📚 Dépendances & Prérequis

### Techniques

- ✅ Phase 1 complétée et validée
- ✅ Infrastructure Docker opérationnelle
- ✅ Base PostgreSQL + pgvector
- ✅ APIs OpenAI + Anthropic configurées

### Données

- ⏳ 5 tenders historiques à collecter
- ⏳ Mémos techniques tenders gagnés
- ⏳ Validation bid manager pour golden dataset

### Ressources

- ✅ 1 Dev Backend Python (full-time 6 semaines)
- ⏳ 0.5 QA Engineer (semaines 5-6)
- ⏳ 0.5 DevOps Engineer (semaine 6)
- ⏳ Expert métier (validation dataset)

---

## 🎯 Critères d'Acceptance Phase 2

### Sprint 1: Performance ✅ ou ❌

- [ ] Ingestion CCTP.pdf < 10s
- [ ] Ingestion 3 documents < 30s
- [ ] 100% documents ingérés (4/4)
- [ ] 350+ embeddings créés
- [ ] Q&A fonctionne sur CCAP.pdf et RC.pdf
- [ ] Tests automatisés de performance

**Condition de passage Sprint 2**: 5/6 critères validés

---

### Sprint 2: Knowledge Base ✅ ou ❌

- [ ] 5+ historical_tenders en base
- [ ] ~1500 embeddings KB créés
- [ ] Endpoint `/suggestions` retourne résultats
- [ ] Filtrage `status="won"` validé
- [ ] Recall@10 > 75% (tolérance -5pts)
- [ ] Diversité: ≥ 3 tenders sources

**Condition de passage Sprint 3**: 5/6 critères validés

---

### Sprint 3: Qualité ✅ ou ❌

- [ ] Golden dataset (50 Q&A) créé
- [ ] Recall@5 > 75% (tolérance -5pts)
- [ ] MRR > 0.65 (tolérance -0.05)
- [ ] Test coverage > 75% (tolérance -5pts)
- [ ] CI/CD GitHub Actions opérationnel
- [ ] Tests automatiques sur PRs

**Condition de passage Phase 3**: 5/6 critères validés

---

## 📅 Jalons Phase 2

| Jalon | Date | Livrables | Critères Validation |
|-------|------|-----------|---------------------|
| **M1: Fin Sprint 1** | J+21 (+7j) | Batch processing, multi-docs, 🆕 timeouts/retry | Temps < 30s, 100% docs, rollback OK |
| **M2: Fin Sprint 2** | J+35 | KB opérationnelle, endpoint /suggestions validé | 5+ tenders KB, Recall@10 > 75% |
| **M3: Fin Sprint 3** | J+49 | Tests complets, CI/CD, golden dataset | Coverage > 75%, CI/CD green |
| **M4: Démo Phase 2** | J+52 | Présentation résultats, benchmark report | Validation stakeholders |

**🆕 Changement**: Jalon M1 décalé de J+14 à J+21 pour intégrer semaine 3 (gestion timeouts)

---

## 🚀 Prochaines Étapes (Post Phase 2)

### Phase 3: Frontend MVP (4 semaines)

**Objectif**: Interface utilisateur pour bid managers

**Features**:
- Dashboard tenders (liste, filtres, status)
- Upload documents (drag & drop multi-fichiers)
- Visualisation analyses (graphiques, KPI, timeline)
- Chat Q&A en temps réel
- Suggestions KB avec preview

### Phase 4: Optimisations Avancées (4 semaines)

**Objectif**: Fine-tuning et fonctionnalités premium

**Features**:
- Fine-tuning embeddings domaine-specific
- Re-ranking avec Cohere/Voyage AI
- Parsing tableaux avancé (Camelot)
- Monitoring & alertes (Grafana, Sentry)
- Génération mémo technique automatique

---

## 📝 Conclusion

La Phase 2 est **critique** pour transformer le MVP Phase 1 en produit utilisable à grande échelle. Focus sur:

1. **Performance** → Ingestion 12x plus rapide
2. **Complétude** → Usage #1 KB opérationnel
3. **Qualité** → Métriques mesurées et optimisées
4. **Stabilité** → Tests automatisés (80% coverage)
5. **🆕 Robustesse** → Gestion timeouts, rollback, retry intelligent

**Durée**: 7 semaines (+1 semaine vs plan initial)
**Budget**: ~$42k (+$5k pour gestion timeouts)
**ROI**: $4.4k/mois (retour 10 mois)

**🎯 Priorités absolues (ne peuvent pas être skippées)**:
- ✅ Batch processing OpenAI (critique performance)
- ✅ Gestion timeouts + rollback (critique robustesse)
- ✅ Notifications utilisateur (critique UX)

**Validation**: Démo à bid managers pour feedback et ajustements Phase 3.

**Architecture complète**: Voir [ARCHITECTURE_TIMEOUT_MANAGEMENT.md](ARCHITECTURE_TIMEOUT_MANAGEMENT.md) pour détails techniques système gestion timeouts.

---

**Prochaine révision**: Fin Sprint 1 (J+14)
**Responsable Phase 2**: [À définir]
**Stakeholders**: Bid Managers, Dev Team, Product Owner
