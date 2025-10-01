# 🎯 Roadmap ScorpiusAO

## 🎯 Prochaines étapes recommandées

### 📅 Court terme (1-2 semaines)

#### 1. Compléter RAG Service
**Priorité**: HAUTE
**Effort**: 2-3 jours

**Tâches**:
- [ ] Implémenter embeddings OpenAI réels dans `rag_service.py`
  - Remplacer placeholders par vrais appels API
  - Gérer rate limiting OpenAI
  - Ajouter cache embeddings similaire à LLM Service
- [ ] Tester recherche vectorielle pgvector
  - Valider requêtes cosine similarity
  - Optimiser index IVFFlat (tuning `lists` parameter)
  - Benchmarker performance sur 1k/10k/100k embeddings
- [ ] Valider chunking strategy
  - Tester différentes tailles (512, 1024, 2048 tokens)
  - Optimiser overlap (100, 200, 300 tokens)
  - Mesurer recall@5 et recall@10

**Dépendances**:
- OpenAI API key configurée
- Budget embeddings (~$0.01 / 1M tokens)

**Livrables**:
- RAG Service 100% fonctionnel
- Documentation exemples d'utilisation
- Métriques performance (latence, recall)

---

#### 2. Tests end-to-end
**Priorité**: HAUTE
**Effort**: 3-4 jours

**Tâches**:
- [ ] Tests unitaires services
  ```python
  tests/
  ├── test_storage_service.py
  ├── test_parser_service.py
  ├── test_llm_service.py (avec mocks Claude API)
  └── test_rag_service.py (avec mocks OpenAI)
  ```
- [ ] Tests intégration API
  ```python
  tests/integration/
  ├── test_tender_crud.py
  ├── test_document_upload.py
  ├── test_analysis_pipeline.py
  └── test_search_endpoints.py
  ```
- [ ] Tests Celery pipeline complet
  - Mock MinIO/Redis/PostgreSQL avec testcontainers
  - Valider états intermédiaires
  - Tester gestion erreurs et retry

**Outils**:
- pytest + pytest-asyncio
- pytest-cov (coverage >80%)
- httpx pour tests API

**Livrables**:
- Suite de tests complète (>80% coverage)
- CI/CD pipeline GitHub Actions
- Rapport coverage

---

#### 3. WebSocket pour notifications temps réel
**Priorité**: MOYENNE
**Effort**: 2 jours

**Tâches**:
- [ ] Ajouter support WebSocket FastAPI
  ```python
  # app/api/v1/endpoints/websocket.py
  @router.websocket("/ws/{tender_id}")
  async def websocket_endpoint(websocket, tender_id):
      # Stream progress updates
  ```
- [ ] Intégrer dans pipeline Celery
  ```python
  # Dans process_tender_documents
  await broadcast_progress(tender_id, {
      "step": 3,
      "progress": 50,
      "message": "Analysing with Claude API..."
  })
  ```
- [ ] Implémenter broadcast Redis Pub/Sub
  - Channel: `tender:{tender_id}:progress`
  - Message: `{"step": int, "progress": int, "message": str}`

**Livrables**:
- WebSocket endpoint `/ws/{tender_id}`
- Progress updates temps réel
- Documentation client WebSocket

---

### 📅 Moyen terme (1 mois)

#### 4. Frontend MVP (Next.js 14)
**Priorité**: HAUTE
**Effort**: 2 semaines

**Structure**:
```
frontend/
├── app/
│   ├── page.tsx                    # Dashboard
│   ├── tenders/
│   │   ├── page.tsx                # Liste tenders
│   │   ├── [id]/
│   │   │   ├── page.tsx            # Détail tender
│   │   │   ├── documents/page.tsx  # Upload documents
│   │   │   ├── analysis/page.tsx   # Résultats analyse
│   │   │   └── response/page.tsx   # Éditeur réponse
│   └── proposals/
│       └── [id]/page.tsx           # Détail proposition
├── components/
│   ├── TenderCard.tsx
│   ├── DocumentUpload.tsx
│   ├── AnalysisDisplay.tsx
│   ├── CriteriaTable.tsx
│   └── ProposalEditor.tsx
└── lib/
    ├── api.ts                      # Client API
    └── websocket.ts                # WebSocket client
```

**Fonctionnalités MVP**:
1. **Dashboard tenders**
   - Liste paginée avec filtres (status, date)
   - Carte tender (titre, organisation, deadline, status)
   - Bouton "Nouveau tender"

2. **Interface upload documents**
   - Drag & drop multi-fichiers
   - Sélection type document (CCTP, RC, AE, etc.)
   - Barre progression extraction
   - Preview PDF intégré

3. **Vue analyse + critères**
   - Résumé exécutif
   - Timeline deadlines
   - Liste critères avec poids (graphique camembert)
   - Section risques avec badges
   - Documents obligatoires checklist

4. **Éditeur basique réponses**
   - Sections pré-remplies (méthodologie, présentation)
   - Rich text editor (TipTap)
   - Export Word/PDF (via API)

**Stack technique**:
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS + shadcn/ui
- React Query (cache API)
- Zustand (state management)

**Livrables**:
- Application web déployable
- Documentation composants
- Tests E2E Playwright

---

#### 5. Intégrations externes
**Priorité**: MOYENNE
**Effort**: 1 semaine

**5.1 Scraper BOAMP**
```python
# app/services/boamp_scraper.py
class BOAMPScraper:
    async def search_tenders(filters):
        # Parse BOAMP RSS/API
        # Extract: title, org, ref, deadline, CPV codes

    async def download_dce(tender_url):
        # Download DCE zip
        # Upload to MinIO
        # Create tender + documents
```

**5.2 AWS PLACE Connector**
```python
# app/services/aws_place_service.py
class AWSPlaceService:
    async def authenticate():
        # OAuth2 flow

    async def list_consultations(filters):
        # API calls

    async def download_documents(consultation_id):
        # Bulk download
```

**5.3 Notifications email**
```python
# app/services/notification_service.py
class NotificationService:
    async def send_analysis_complete(user_email, tender_id):
        # SendGrid/Mailgun

    async def send_deadline_reminder(tender_id, days_before):
        # Cron job daily
```

**Livrables**:
- Scrapers opérationnels (cron jobs)
- Dashboard monitoring imports
- Email templates

---

#### 6. Sécurité production
**Priorité**: HAUTE
**Effort**: 3-4 jours

**6.1 Authentification JWT**
```python
# app/core/security.py
def create_access_token(user_id, expires_delta):
    # JWT avec refresh token

# app/api/dependencies.py
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Validation token
```

**6.2 RBAC (Role-Based Access Control)**
```python
# app/models/user.py
class User(Base):
    id, email, hashed_password
    role: Enum("admin", "bid_manager", "viewer")
    organization_id: UUID

# app/core/permissions.py
def require_role(role: UserRole):
    # Decorator pour endpoints
```

**6.3 Rate limiting**
```python
# app/middleware/rate_limit.py
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    # Redis sliding window
    # 60 req/min par user
```

**6.4 Validation fichiers**
```python
# app/api/v1/endpoints/tender_documents.py
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_MIME_TYPES = ["application/pdf"]

async def validate_upload(file: UploadFile):
    # Taille
    # Type MIME
    # Scan antivirus (ClamAV)
```

**Livrables**:
- Authentification JWT opérationnelle
- RBAC avec 3 rôles
- Rate limiting actif
- Validation sécurisée uploads

---

### 📅 Long terme (3 mois)

#### 7. Fonctionnalités avancées

**7.1 Génération mémo technique automatique**
```python
# app/services/document_generator.py
class DocumentGenerator:
    async def generate_technical_memo(
        tender_id: UUID,
        template: str,
        company_context: dict
    ) -> bytes:
        # Populate template with:
        # - Extracted requirements
        # - Company certifications
        # - Past references
        # - Infrastructure details
        # Output: Word/PDF
```

**Fonctionnalités**:
- Templates personnalisables (Jinja2)
- Insertion automatique logos, graphiques
- Table des matières auto
- Export Word (.docx) et PDF

---

**7.2 Export DUME/DC4 automatique**
```python
# app/services/dume_generator.py
class DUMEGenerator:
    async def generate_dume_xml(
        company_info: dict,
        certifications: list
    ) -> str:
        # Format XML DUME européen standard
        # Validation XSD
```

**Formats supportés**:
- DUME XML (format européen)
- DC4 PDF pré-rempli
- Attestations fiscales/sociales

---

**7.3 Scoring simulation**
```python
# app/services/scoring_service.py
class ScoringService:
    async def simulate_score(
        proposal_id: UUID,
        criteria: list[TenderCriterion]
    ) -> dict:
        # Pour chaque critère:
        # - Analyser contenu proposition
        # - Comparer avec requirements
        # - Calculer score partiel
        # Return: {criterion_id: {score, confidence, feedback}}
```

**Algorithmes**:
- NLP similarity (BERT embeddings)
- Keyword matching pondéré
- Compliance checklist
- Score global avec intervalle confiance

---

**7.4 Éditeur collaboratif temps réel**
```python
# app/api/v1/endpoints/collaboration.py
@router.websocket("/ws/proposals/{id}/edit")
async def collaborative_edit(websocket, proposal_id):
    # Operational Transform (OT) ou CRDT
    # Broadcast changes to all editors
```

**Features**:
- Multi-cursors avec noms utilisateurs
- Versions/snapshots automatiques
- Commentaires inline
- Suggestions IA contextuelle

---

#### 8. Optimisations production

**8.1 Cache multi-niveaux**
```
User → CDN (CloudFront)
     → Nginx (static assets)
     → Redis (API responses)
     → PostgreSQL
```

**Stratégie**:
- CDN: Assets statiques, images, PDFs
- Redis L1: API responses (TTL 5-60min)
- Redis L2: Embeddings, analyses (TTL 24h)
- PostgreSQL: Source of truth

---

**8.2 Monitoring & Observabilité**
```python
# Sentry pour erreurs
sentry_sdk.init(dsn=settings.sentry_dsn)

# Prometheus pour métriques
from prometheus_client import Counter, Histogram
tender_analysis_duration = Histogram(
    "tender_analysis_duration_seconds",
    "Time spent analyzing tender"
)

# Structlog pour logs
import structlog
logger = structlog.get_logger()
```

**Dashboards**:
- Grafana: Latence, throughput, erreurs
- Sentry: Crash reports, stack traces
- ELK Stack: Recherche logs
- Flower: Celery workers health

---

**8.3 Scaling Kubernetes**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scorpius-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
  template:
    spec:
      containers:
      - name: api
        image: scorpius-api:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: scorpius-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scorpius-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**Infrastructure**:
- Kubernetes (EKS/GKE/AKS)
- Helm charts pour déploiement
- ArgoCD pour GitOps
- Istio pour service mesh

---

## 📊 Planning prévisionnel

| Phase | Durée | Effort (j/h) | Priorité |
|-------|-------|--------------|----------|
| **Court terme** | 2 semaines | 40h | HAUTE |
| - RAG Service | 3j | 24h | HAUTE |
| - Tests | 4j | 32h | HAUTE |
| - WebSocket | 2j | 16h | MOYENNE |
| **Moyen terme** | 1 mois | 120h | HAUTE |
| - Frontend MVP | 10j | 80h | HAUTE |
| - Intégrations | 5j | 40h | MOYENNE |
| - Sécurité | 4j | 32h | HAUTE |
| **Long terme** | 3 mois | 400h | MOYENNE |
| - Features avancées | 30j | 240h | MOYENNE |
| - Optimisations prod | 20j | 160h | MOYENNE |

**Total estimé**: ~4.5 mois ETP (Équivalent Temps Plein)

---

## 🎯 Critères de succès

### Court terme (1-2 semaines)
- [ ] RAG Service: recall@5 > 80% sur benchmark
- [ ] Tests: coverage > 80%
- [ ] WebSocket: latence < 100ms pour progress updates

### Moyen terme (1 mois)
- [ ] Frontend: Time to Interactive < 3s
- [ ] Sécurité: 0 vulnérabilités critiques (Snyk scan)
- [ ] Intégrations: Import automatique 10+ tenders/jour depuis BOAMP

### Long terme (3 mois)
- [ ] Scoring simulation: précision > 70% vs. scores réels
- [ ] Production: 99.9% uptime
- [ ] Performance: Analyse tender < 60s (P95)
- [ ] Scalabilité: Support 100+ utilisateurs concurrents

---

## 🚀 Quick wins (priorité immédiate)

1. **Compléter RAG Service** (3 jours)
   - Impact: Débloque recherche similarité + suggestions
   - Complexité: Moyenne

2. **Tests unitaires critiques** (2 jours)
   - Impact: Confiance déploiement
   - Complexité: Faible

3. **WebSocket notifications** (2 jours)
   - Impact: Meilleure UX
   - Complexité: Faible

4. **Frontend dashboard basique** (5 jours)
   - Impact: Application utilisable end-to-end
   - Complexité: Moyenne

**Total Quick Wins**: 12 jours → MVP utilisable

---

## 📚 Ressources nécessaires

### Humaines
- 1 Développeur Backend Python (FastAPI, Celery, PostgreSQL)
- 1 Développeur Frontend (React/Next.js, TypeScript)
- 0.5 DevOps (Docker, K8s, CI/CD)
- 0.5 QA (Tests, automatisation)

### Budget mensuel estimé
- Infrastructure AWS/GCP: ~$200-500/mois
- Claude API (100k tokens/jour): ~$300/mois
- OpenAI Embeddings: ~$50/mois
- Services SaaS (Sentry, monitoring): ~$100/mois
- **Total**: ~$650-950/mois

### Outils développement
- GitHub/GitLab (version control)
- Linear/Jira (project management)
- Figma (design frontend)
- Postman (API testing)
- DataGrip (DB management)

---

## 🔄 Méthodologie

### Sprint cycle (2 semaines)
```
Semaine 1:
  Lundi: Sprint planning + review
  Mardi-Jeudi: Développement
  Vendredi: Code review + démo interne

Semaine 2:
  Lundi-Mercredi: Développement + tests
  Jeudi: QA + bug fixes
  Vendredi: Déploiement staging + rétrospective
```

### Definition of Done
- [ ] Code reviewé par 1+ développeur
- [ ] Tests unitaires passent (coverage >80%)
- [ ] Tests intégration passent
- [ ] Documentation à jour
- [ ] Déployé en staging
- [ ] Validation PO/utilisateur

---

## 📞 Contact & Support

- **Product Owner**: À définir
- **Tech Lead**: À définir
- **Repo GitHub**: `ScorpiusAO/scorpius-platform`
- **Slack**: `#scorpius-dev`
- **Documentation**: https://docs.scorpius.ai

---

*Dernière mise à jour: 2025-10-01*
