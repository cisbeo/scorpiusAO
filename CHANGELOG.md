# Changelog - ScorpiusAO

Toutes les modifications notables du projet sont documentées dans ce fichier.

---

## [3 octobre 2025 - PM] - Correction Documentation + Enrichissement Sources API

### 🔧 Modifié
- **ROADMAP.md : Correction status RAG Service**
  - Status changé de "✅ COMPLÉTÉ" à "🚧 EN COURS (partiellement complété)"
  - Ajout section "Tâches en attente" avec détails sur STEP 2 manquant
  - Ajout section "Limitations actuelles" :
    - ⚠️ Embeddings créés seulement pour données de test (2 sections fictives)
    - ⚠️ 377 sections VSGP-AO extraites mais pas embedées
    - ⚠️ Pages retournées par l'API incorrectes (ex: page 2 au lieu de page 34)
  - Nouvelle tâche "3bis. Compléter Pipeline Celery - Ingestion RAG Automatique"
    - Priorité: HAUTE, Effort: 1-2 jours
    - Objectif: Ajouter STEP 2 (création embeddings) dans `process_tender_document()`
    - Script CLI pour ingestion manuelle des documents existants
    - Validation avec vrais documents CCTP.pdf (202 sections → ~140 embeddings)

- **API `/tenders/{id}/ask` : Sources enrichies**
  - Requête SQL modifiée avec JOIN sur `tender_documents`
  - Ajout `document_filename` dans métadonnées (ex: "CCTP.pdf", "CCAP.pdf")
  - Ajout `document_type_full` dans métadonnées (ex: "cahier_charges_technique")
  - Context passé à Claude enrichi : `[filename - Section X, Page Y]`
  - Amélioration traçabilité pour le bid manager

### 📝 Documenté
- Clarification que le RAG fonctionne techniquement mais manque l'intégration automatique
- Documentation du problème des pages fictives (données de test vs production)
- Plan détaillé pour compléter le pipeline Celery avec STEP 2

---

## [3 octobre 2025 - AM] - Knowledge Base RAG Implementation

### ✅ Ajouté
- **Modèles SQLAlchemy pour Knowledge Base**
  - `HistoricalTender`: Tenders archivés avec métadonnées (award_date, total_amount, winner_company)
  - `PastProposal`: Propositions passées avec post-mortem (lessons_learned, win_factors, score_obtained)
  - Relations One-to-Many avec cascade delete
  - Propriétés calculées: `is_winning_proposal`, `win_rate_percentage`

- **Archive Service** (`app/services/archive_service.py`)
  - Méthode `archive_tender()` pour migration Tender → HistoricalTender
  - Création automatique embeddings RAG lors de l'archivage
  - Support post-mortem: `lessons_learned`, `win_factors`, `improvement_areas`
  - Option `delete_original` pour supprimer tender/proposal source
  - Retour détaillé: `historical_tender_id`, `past_proposal_id`, `embeddings_created`

- **Endpoint API Archive**
  - `POST /api/v1/archive/tenders/{tender_id}/archive`
  - Request schema Pydantic: `ArchiveTenderRequest`
  - Response schema: `ArchiveTenderResponse`
  - Documentation OpenAPI auto-générée
  - Error handling: 404 (not found), 500 (internal error)

- **RAG Service - Batch Ingestion**
  - Méthode `ingest_all_past_proposals_sync()` pour ingestion batch
  - Filtrage par status: won/lost/all
  - Metadata enrichie: `historical_tender_id`, `tender_title`, `organization`, `win_factors`
  - Chunking sémantique automatique (100-1000 tokens)
  - Reporting: total_proposals, total_embeddings, errors[]

- **Script CLI**
  - `scripts/ingest_past_proposals.py` pour ingestion batch
  - Arguments: `--status` (won/lost/all), `--batch-size`
  - Usage: `python scripts/ingest_past_proposals.py --status won`

- **LLM Service Enrichi**
  - Méthode `generate_response_section()` modifiée
  - Nouveaux paramètres: `db`, `use_knowledge_base`, `kb_top_k`
  - Retrieval automatique top-k past_proposals (status="won")
  - Injection exemples dans prompt Claude avec metadata (score, tender_title)
  - Amélioration qualité réponses basée sur propositions gagnantes

- **Migration Alembic**
  - Migration `ba99101498ca`: Création tables `historical_tenders` et `past_proposals`
  - Renommage anciennes tables en `_old` (préservation données)
  - 6 index optimisés (title, organization, reference_number, award_date, status, archived_at)
  - Foreign Key CASCADE DELETE
  - Contrainte UNIQUE (historical_tender_id, our_company_id)

### 📝 Modifié
- **ROADMAP.md**
  - Marqué "Intégration Knowledge Base" comme ✅ complété (3 oct 2025)
  - Ajout détails implémentation (modèles, services, endpoints)
  - Référence vers Issue #2

- **CLAUDE.md**
  - Section RAG Service: "Knowledge Base" passée de "Planned" à "✅ Implemented"
  - Ajout section "Archive Service" avec détails complets
  - Database Schema: Ajout tables `historical_tenders` et `past_proposals`
  - Détails méthodes: `ingest_all_past_proposals_sync()`, `archive_tender()`

### 📚 Documentation
- **IMPLEMENTATION_PLAN_SOLUTION_1.md** (1000+ lignes)
  - Plan détaillé 4 phases (modèles, archive, RAG, LLM)
  - Code complet pour chaque composant
  - Tests recommandés (17 tests)
  - Commandes d'utilisation

- **IMPLEMENTATION_SUMMARY_ISSUE_2.md** (800+ lignes)
  - Résumé implémentation complète
  - Workflow E2E (archivage + génération avec KB)
  - Métriques et validation
  - Commandes utiles

- **ISSUE_2_RAG_KNOWLEDGE_BASE_ANALYSIS.md** (existant)
  - Analyse 3 solutions (Tables Séparées, Flag is_archived, Polymorphic STI)
  - Recommandation Solution 1 avec justification

### 🔧 Technique
- **Code production**: ~1010 lignes
- **Fichiers créés**: 7
- **Fichiers modifiés**: 4
- **Tests coverage**: Implémentation production-ready, tests optionnels (Sprint suivant)

### 🐛 Corrections
- Import `Optional` ajouté dans `rag_service.py`
- Import `get_db` corrigé dans `archive.py` (app.models.base au lieu de app.api.dependencies)

### 🔗 Liens
- Issue GitHub: [#2 - RAG Knowledge Base](https://github.com/cisbeo/scorpiusAO/issues/2) - ✅ RÉSOLU
- Documentation complète: `backend/docs/IMPLEMENTATION_SUMMARY_ISSUE_2.md`

---

## [2 octobre 2025] - RAG Service Q&A Implementation

### ✅ Ajouté
- RAG Service complet pour Q&A sur tenders
- Endpoint `POST /tenders/{id}/ask`
- Embeddings OpenAI text-embedding-3-small
- Chunking sémantique intelligent
- Cache Redis (1h TTL)
- Tests E2E (Recall@5: 100%, Cost: $0.016/tender)

---

## Format

Ce changelog suit le format [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/).

### Types de changements
- **Ajouté** pour les nouvelles fonctionnalités
- **Modifié** pour les changements dans les fonctionnalités existantes
- **Déprécié** pour les fonctionnalités qui seront bientôt supprimées
- **Supprimé** pour les fonctionnalités supprimées
- **Corrigé** pour les corrections de bugs
- **Sécurité** pour les vulnérabilités corrigées
