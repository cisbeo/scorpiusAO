# 🎯 Roadmap ScorpiusAO

**Dernière mise à jour**: 2 octobre 2025
**Version actuelle**: 0.2.0 (MVP Backend)

---

## 📊 État Actuel du Projet

### ✅ Phase 1 - Backend MVP (COMPLÉTÉ - Oct 2025)

**Infrastructure & Services**

- ✅ Docker Compose orchestration (PostgreSQL, Redis, RabbitMQ, MinIO)
- ✅ Base de données complète (9 tables + pgvector)
- ✅ API REST FastAPI (8 endpoints)
- ✅ Storage service (MinIO S3)
- ✅ LLM service (Claude Sonnet 4.5 + cache Redis)
- ✅ Parser service (PyPDF2, pdfplumber, OCR Tesseract)
- ✅ Pipeline async Celery robuste

**Fonctionnalités Clés Implémentées**

- ✅ Extraction structure hiérarchique (sections, TOC, numérotation)
- ✅ Détection automatique sections clés (18/18 processus ITIL, critères, exclusions)
- ✅ Optimisation hiérarchique LLM (-20% tokens)
- ✅ Analyse IA complète (résumé, exigences, risques, délais)
- ✅ Extraction critères structurés avec poids

**Tests & Documentation**

- ✅ Suite tests E2E complète
- ✅ Procédure validation documentée
- ✅ Résultats validés sur tender VSGP-AO réel (377 sections, $0.12/analyse)

**Métriques de Performances Validées**

- Extraction: 45s pour 3 documents (objectif: <2 min) ✅
- Analyse LLM: 8s (objectif: <15s) ✅
- Coût: $0.12/tender (objectif: <$0.20) ✅
- Détection ITIL: 100% recall (objectif: >90%) ✅

---

## 🚀 Prochaines Étapes

### 📅 Priorité Immédiate (2-3 semaines) - Solution 5.5 Adaptive Analysis

#### 1. Analyse LLM Améliorée - Solution 5.5 (Adaptive)

**Priorité**: CRITIQUE | **Effort**: 12 semaines (6 sprints) | **Status**: 📋 Planifié
**Issues**: [#3](https://github.com/cisbeo/scorpiusAO/issues/3), [#4](https://github.com/cisbeo/scorpiusAO/issues/4)

**Architecture recommandée**: Analyse adaptative selon complexité de l'AO

**Phase 1 - Sprint 1-2 (MVP - Solution 5 Hybrid)**: 2 semaines

- [ ] Executive analysis (2 passes: classification + synthèse thématique)
- ✅ Intégration RAG (embeddings + Q&A endpoint) - **COMPLÉTÉ 3 oct 2025**
  - ✅ Endpoint `/tenders/{id}/ask` opérationnel
  - ✅ Cache Redis 1h TTL
  - ✅ Recall@5: 100%, Coût: $0.016/tender
  - ✅ Tests E2E validés
- [ ] Dashboard React avec risk scoring, KPI, timeline
- [ ] Composant chat Q&A avec références sources
- **Coût**: $0.55/AO + $0.01/question
- **Temps**: 45 secondes
- **Précision**: 85-90%

**Phase 2 - Sprint 3-4 (Premium - Solution 6 Multi-Passes)**: 2 semaines

- [ ] Pass 1: Analyse détaillée de TOUTES les sections (377 sections)
- [ ] Pass 2: Synthèse thématique enrichie
- [ ] Pass 3: Cross-analysis (contradictions, dépendances, FAQ pré-calculée)
- [ ] Feature flag "Deep Analysis" (opt-in)
- [ ] A/B testing (50% users avec Sol 5, 50% avec Sol 6)
- **Coût**: $3.76/AO + $0.01/question
- **Temps**: 3-4 minutes
- **Précision**: 95-98%

**Phase 3 - Sprint 5-6 (Adaptive - Solution 5.5)**: 2 semaines

- [ ] Implémentation scoring automatique de complexité (0-100)
- [ ] Sélection automatique du mode d'analyse:
  - Complexité < 50: Fast mode (Solution 5) → $0.55
  - Complexité 50-75: Selective mode (50 sections clés) → $1.50
  - Complexité > 75: Deep mode (Solution 6) → $3.76
- [ ] Machine learning: affiner scoring selon feedback utilisateurs
- [ ] Mode adaptatif par défaut pour tous
- **Coût moyen**: $1.67/AO (pondéré)
- **ROI**: +€47 gain marginal vs Solution 5, +81% gain vs manuel

**Critères de complexité détectés**:

- Nombre de sections (max 30 points)
- Présence de tableaux (max 20 points)
- Mots-clés complexité (max 20 points): pénalités, coefficient multiplicateur, exclusion, réversibilité
- Montant estimé (max 15 points)
- Durée contrat (max 15 points)

**Valeur ajoutée**:

- ✅ Détection automatique contradictions entre sections
- ✅ Graphe de dépendances entre sections
- ✅ FAQ pré-calculée (20-30 questions)
- ✅ Confidence scoring par section
- ✅ 5 niveaux de navigation front (executive → thème → section → Q&A → advanced)
- ✅ Réutilisation analyses pour futurs AO similaires

---

#### 2. Amélioration Parsing Tableaux

**Priorité**: HAUTE | **Effort**: 1-2 semaines | **Status**: 📋 Documenté

**3 Solutions Complémentaires**:

- **Phase 1**: Enrichissement Prompt (2-4h) → +20% qualité
- **Phase 2**: Post-Processing (8-16h) → +50% qualité totale
- **Phase 3**: Intégration Camelot (4-8h) → 90-98% qualité finale

---

#### 3. Compléter RAG Service (Intégré dans Solution 5.5)

**Priorité**: CRITIQUE | **Effort**: 2-3 jours | **Status**: 🚧 EN COURS (partiellement complété - 3 oct 2025)

**Tâches complétées**:

- ✅ Implémenter embeddings OpenAI réels (text-embedding-3-small)
- ✅ Tester recherche vectorielle pgvector (cosine similarity)
- ✅ Valider chunking strategy (recall@5 = 100%, objectif: >80%)
- ✅ API endpoint `/tenders/{id}/ask` avec RAG
- ✅ Cache questions fréquentes (Redis 1h TTL)
- ✅ Méthodes synchrones pour Celery (5 méthodes)
- ✅ Tests E2E complets avec données de test (recall@5=100%, coût=$0.016/tender)
- ✅ Sources enrichies avec `document_filename` et métadonnées complètes

**Tâches en attente**:

- [ ] **Pipeline Celery STEP 2 : Ingestion RAG automatique après extraction**
  - Attention : l'ingestion automatique doit bien taggué les tenders ingérés comme des tenders en cours et pas des tenders historical_tenders
  - Code existant: `rag_service.ingest_document_sync()` ✅
  - Intégration dans `process_tender_document()` ❌ NON FAIT
  - Les 377 sections du VSGP-AO sont extraites mais **pas embedées**
  - Seules les données de test (2 sections) ont des embeddings
- [ ] Pipeline STEP 5: Find similar tenders (recherche dans historical_tenders)
- [ ] Ingestion manuelle des documents existants (CCTP.pdf, CCAP.pdf, RC.pdf)

**Résultats validés** (sur données de test uniquement):

- Recall@5: 100% (objectif: >80%) ✅
- Answer Quality: 80% (objectif: >80%) ✅
- Coût: $0.016/tender (objectif: <$0.02) ✅
- Temps réponse Q&A: <100ms (cache hit), 3-4s (cache miss)

**Limitations actuelles**:

- ⚠️ Les embeddings ne sont créés QUE dans les tests E2E (données fictives)
- ⚠️ Les vrais documents (377 sections VSGP-AO) n'ont PAS d'embeddings
- ⚠️ L'API `/tenders/{id}/ask` utilise les données de test (pages incorrectes)
- ⚠️ Les pages retournées ne correspondent pas aux vrais documents (ex: page 2 au lieu de page 34)

**Prochaines étapes** (Sprint 2):

- [ ] FAQ pré-calculée (20-30 questions auto-générées)
- [x] **Intégration Knowledge Base (`past_proposals`, `historical_tenders`)** ✅ (3 oct 2025)
  - ✅ Modèles SQLAlchemy créés
  - ✅ Migration Alembic appliquée
  - ✅ Archive Service + endpoint API
  - ✅ RAG batch ingestion
  - ✅ LLM Service enrichi avec KB
  - Voir: [Issue #2 - RÉSOLU](https://github.com/cisbeo/scorpiusAO/issues/2)
- [ ] Intégration `case_studies` et `certifications` (optionnel)
- [ ] Composant frontend Chat Q&A
- [ ] Re-ranking avec Cohere/Voyage (optionnel)

---

#### 3bis. Compléter Pipeline Celery - Ingestion RAG Automatique

**Priorité**: HAUTE | **Effort**: 1-2 jours | **Status**: ⏳ À FAIRE

**Objectif**: Créer automatiquement les embeddings après l'extraction des sections pour que l'API retourne les **vraies pages** des documents.

**Problème actuel**:

- `process_tender_document()` extrait les sections mais ne crée pas les embeddings
- Résultat : 377 sections extraites, 0 embeddings en production
- L'API utilise les embeddings de test (2 sections fictives avec pages incorrectes)

**Tâches**:

- [ ] **Ajouter STEP 2 dans `process_tender_document()`** (après ligne 183)
  - Appeler `rag_service.ingest_document_sections_sync(db, document_id, tender_id)`
  - Créer embeddings pour toutes les sections non-TOC avec contenu
  - Logger le nombre d'embeddings créés (ex: 202 sections → ~140 embeddings)
  - Gestion d'erreur : si échec, logger mais ne pas bloquer le pipeline
- [ ] **Créer script CLI pour ingestion manuelle des documents existants**
  - `python scripts/ingest_tender_documents.py --tender_id=<uuid>`
  - Ingérer les 377 sections du tender VSGP-AO test (3cfc8207-f275-4e53-ae0c-bead08cc45b7)
  - Option `--force` pour réingérer (supprimer anciens embeddings)
- [ ] **Valider avec le vrai CCTP.pdf**
  - 202 sections → ~140 embeddings attendus
  - Vérifier que les pages retournées sont correctes (ex: section 4.1.5 = page 34)
- [ ] **Mettre à jour tests E2E** pour valider l'ingestion automatique
  - Test que `process_tender_document()` crée bien les embeddings
  - Vérifier le nombre d'embeddings créés

**Bénéfice attendu**:

- ✅ Les pages retournées par l'API seront les **vraies pages** du CCTP.pdf
- ✅ Plus besoin de données de test : production avec vrais documents
- ✅ Pipeline complet : Upload → Extract → Embed → Q&A opérationnel

**Coût estimé**: 377 sections × $0.0001/embed = ~$0.04 par tender

---

#### 4. WebSocket Notifications

**Priorité**: MOYENNE | **Effort**: 2 jours | **Status**: ⏳ Non démarré

Progress updates temps réel via WebSocket + Redis Pub/Sub

---

#### 5. Tests Unitaires Complets

**Priorité**: HAUTE | **Effort**: 3-4 jours | **Status**: ⏳ À compléter

Coverage > 80% + CI/CD GitHub Actions

---

### 📅 Moyen Terme (1 mois)

#### 5. Frontend MVP (Next.js 14)

**Priorité**: HAUTE | **Effort**: 2 semaines

- Dashboard tenders
- Upload documents (drag & drop)
- Visualisation analyses
- Éditeur basique réponses

#### 6. Intégrations Externes

**Priorité**: MOYENNE | **Effort**: 1 semaine

- Scraper BOAMP automatique
- Connecteur AWS PLACE
- Notifications email

#### 7. Sécurité Production

**Priorité**: HAUTE | **Effort**: 3-4 jours

- Authentification JWT + refresh tokens
- RBAC (3 rôles: admin, bid_manager, viewer)
- Rate limiting Redis
- Validation sécurisée uploads

---

### 📅 Long Terme (3 mois)

#### 8. Fonctionnalités Avancées

- **Génération Mémo Technique**: Templates Jinja2, export Word/PDF
- **Export DUME/DC4**: Format XML européen standard
- **Scoring Simulation**: Prédiction scores avec IA
- **Éditeur Collaboratif**: Temps réel avec WebSocket

#### 9. Optimisations Production

- **Cache Multi-Niveaux**: CDN + Redis L1/L2
- **Monitoring**: Grafana + Sentry + ELK Stack
- **Scaling Kubernetes**: HPA 2-10 replicas, 99.9% uptime

---

## 📊 Planning

| Phase | Durée | Priorité | Status |
|-------|-------|----------|--------|
| Phase 1 - MVP Backend | ✅ 3 semaines | HAUTE | ✅ DONE |
| **Solution 5.5 Adaptive (Sprint 1-6)** | **12 semaines** | **CRITIQUE** | 📋 Planifié |
| ├─ Sprint 1-2: Solution 5 (MVP) | 2 semaines | CRITIQUE | ⏳ À démarrer |
| ├─ Sprint 3-4: Solution 6 (Premium) | 2 semaines | CRITIQUE | ⏳ Planifié |
| └─ Sprint 5-6: Adaptive (ML) | 2 semaines | CRITIQUE | ⏳ Planifié |
| Court terme (Parsing + Tests) | 2 semaines | HAUTE | 🚧 EN COURS |
| Moyen terme | 1 mois | HAUTE | ⏳ Planifié |
| Long terme | 3 mois | MOYENNE | ⏳ Planifié |

**Total estimé avec Solution 5.5**: ~7 mois ETP

---

## 🎯 Critères de Succès

### Solution 5.5 Adaptive (Priorité Critique)

- [ ] **Sprint 1-2**: Solution 5 fonctionnelle
  - Executive analysis en <45 sec
  - RAG Q&A en <2 sec
  - Dashboard React avec risk scoring
  - Chat avec références sources
- [ ] **Sprint 3-4**: Solution 6 fonctionnelle
  - Analyse 377 sections en 3-4 min
  - Détection contradictions automatique
  - FAQ pré-calculée (20-30 questions)
  - A/B testing validé
- [ ] **Sprint 5-6**: Solution 5.5 en production
  - Scoring complexité précision >85%
  - Coût moyen <$2/AO
  - ROI >€600/AO
  - Satisfaction utilisateur >90%

### Court Terme

- [ ] Parsing tableaux: qualité > 85%
- [ ] RAG Service: recall@5 > 80%
- [ ] Tests: coverage > 80%
- [ ] WebSocket: latence < 100ms

### Moyen Terme

- [ ] Frontend: TTI < 3s (Lighthouse > 90)
- [ ] Sécurité: 0 vulnérabilités critiques
- [ ] BOAMP: Import 10+ tenders/jour
- [ ] API: P95 latence < 300ms

### Long Terme

- [ ] Scoring: précision > 70%
- [ ] Production: 99.9% uptime
- [ ] Performance: Analyse < 60s P95
- [ ] Scalabilité: 100+ users concurrents

---

## 🚀 Quick Wins Immédiats

### Priorité Absolue (Sprint 1-2)

1. **Solution 5 MVP** (2 semaines) → Analyse adaptative opérationnelle
   - Executive analysis avec 2 passes
   - RAG Service complet (embeddings + Q&A)
   - Dashboard React basique
   - ROI: +€599/AO vs manuel

### Court Terme

2. **Parsing Tableaux Phase 1** (4h) → +20% qualité
3. **Tests Unitaires** (2j) → Confiance déploiement
4. **WebSocket** (2j) → Meilleure UX

**Total Sprint 1-2**: 2 semaines → Solution 5 MVP utilisable en production

---

## 📚 Ressources

### Humaines

- 1 Dev Backend Python
- 1 Dev Frontend React/Next.js
- 0.5 DevOps
- 0.5 QA

### Budget Mensuel (Production)

- Infrastructure: $200-500
- **Claude API**: $300-800 (avec Solution 5.5 adaptive)
  - 50 AO/mois × $1.67 moyen = ~$83.50
  - 500 questions RAG/mois × $0.01 = ~$5
  - Marge sécurité + autres usages
- **OpenAI Embeddings**: $50-100
- SaaS: $100-150
- **Total**: ~$650-1,550/mois

**ROI estimé** (50 AO/mois):

- Coût outil: ~$650/mois
- Gain temps bid managers: 50 AO × €599 = **€29,950/mois**
- **ROI net**: **€29,300/mois** (45× le coût)

---

**Prochaine révision**: 15 octobre 2025
