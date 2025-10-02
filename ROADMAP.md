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

### 📅 Court Terme (1-2 semaines)

#### 1. Amélioration Parsing Tableaux
**Priorité**: HAUTE | **Effort**: 1-2 semaines | **Status**: 📋 Documenté

**3 Solutions Complémentaires**:
- **Phase 1**: Enrichissement Prompt (2-4h) → +20% qualité
- **Phase 2**: Post-Processing (8-16h) → +50% qualité totale
- **Phase 3**: Intégration Camelot (4-8h) → 90-98% qualité finale

---

#### 2. Compléter RAG Service
**Priorité**: HAUTE | **Effort**: 2-3 jours | **Status**: ⚠️ À finaliser

**Tâches**:
- Implémenter embeddings OpenAI réels
- Tester recherche vectorielle pgvector
- Valider chunking strategy (recall@5 > 80%)

---

#### 3. WebSocket Notifications
**Priorité**: MOYENNE | **Effort**: 2 jours | **Status**: ⏳ Non démarré

Progress updates temps réel via WebSocket + Redis Pub/Sub

---

#### 4. Tests Unitaires Complets
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
| Court terme | 2 semaines | HAUTE | 🚧 EN COURS |
| Moyen terme | 1 mois | HAUTE | ⏳ Planifié |
| Long terme | 3 mois | MOYENNE | ⏳ Planifié |

**Total estimé**: ~4.5 mois ETP

---

## 🎯 Critères de Succès

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

1. **Parsing Tableaux Phase 1** (4h) → +20% qualité
2. **RAG Service** (3j) → Débloque suggestions
3. **Tests Unitaires** (2j) → Confiance déploiement
4. **WebSocket** (2j) → Meilleure UX

**Total**: ~12 jours → MVP utilisable end-to-end

---

## 📚 Ressources

### Humaines
- 1 Dev Backend Python
- 1 Dev Frontend React/Next.js
- 0.5 DevOps
- 0.5 QA

### Budget Mensuel (Production)
- Infrastructure: $200-500
- Claude API: $300-500
- OpenAI Embeddings: $50-100
- SaaS: $100-150
- **Total**: ~$650-1,250/mois

---

**Prochaine révision**: 15 octobre 2025
