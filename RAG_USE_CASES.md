# 🎯 RAG Service - Use Cases Détaillés

**Date**: 2 octobre 2025
**Version**: 1.0
**Objectif**: Définir les 5 use cases RAG à plus forte valeur ajoutée pour ScorpiusAO

---

## 📊 Vue d'Ensemble

Le RAG Service de ScorpiusAO a pour unique objectif d'**aider le bid manager à rédiger sa réponse** en recherchant du contenu réutilisable dans la **Knowledge Base (KB)**.

### ❌ Ce que le RAG NE FAIT PAS
- Analyser les documents d'appel d'offre (fait par Claude API)
- Créer des embeddings des tenders (économie $10-20/tender)
- Rechercher dans les documents CCTP/RC/AE

### ✅ Ce que le RAG FAIT
- Recherche sémantique dans la Knowledge Base
- Suggestions de contenu pertinent par critère
- Découverte de références clients similaires
- Récupération de certifications et templates

---

## 🏆 TOP 5 USE CASES (par valeur ajoutée)

---

## 1️⃣ Auto-Suggestion par Critère

### 🎯 Problème Métier

Le bid manager doit rédiger une réponse détaillée pour **chaque critère d'évaluation** du tender:
- Critères techniques (40% de la note)
- Critères financiers (60% de la note)
- Critères RSE/environnementaux (10% de la note)

**Pain points**:
- 10-20 critères par tender à traiter
- Chaque critère nécessite 30-60 min de rédaction
- Risque d'oublier du contenu pertinent existant
- Pression temps (deadline 30-45 jours)

**Temps actuel**: 8-12h par tender (rédaction critères)

---

### 💡 Solution RAG

**Workflow Automatisé**:

```
1. Claude extrait les critères du tender
   → Stockés dans `tender_criteria` avec description + poids

2. Pour CHAQUE critère automatiquement:
   a) RAG encode la description du critère en embedding
   b) Recherche cosine similarity dans `document_embeddings`
   c) Filtre par type: past_proposal, case_study, documentation
   d) Retourne Top 3 chunks les plus pertinents
   e) Stocke dans `criterion_suggestions`

3. Bid manager voit dans l'UI:
   - Liste des critères (gauche)
   - Pour chaque critère: 3 suggestions (droite)
   - Score de pertinence (%)
   - Source (quel document KB)

4. Bid manager:
   - Clique sur suggestion → Aperçu complet
   - Bouton "Insérer" → Copie dans éditeur
   - Adapte le texte au contexte spécifique
```

---

### 📋 Exemple Concret

**Tender**: EPT Vallée Sud Grand Paris - Infogérance

**Critère Extrait**:
```json
{
  "criterion_type": "technique",
  "description": "Gestion des incidents niveau 1 - Processus de détection, enregistrement, qualification et résolution des incidents avec engagements de niveaux de service",
  "weight": "15%",
  "is_mandatory": false
}
```

**RAG Retourne** (Top 3):

```
┌─────────────────────────────────────────────────────────────┐
│ Suggestion 1                                  Score: 92%    │
├─────────────────────────────────────────────────────────────┤
│ Source: Past Proposal - Mairie de Lyon (2023) - GAGNÉ      │
│                                                             │
│ "Notre processus de gestion des incidents niveau 1 repose  │
│  sur le référentiel ITIL v4 et comprend 5 étapes clés:     │
│                                                             │
│  1. Détection automatisée via supervision (Zabbix) avec    │
│     alertes temps réel envoyées au centre de services      │
│  2. Enregistrement dans l'outil ITSM (ServiceNow) avec     │
│     catégorisation automatique par mots-clés               │
│  3. Qualification niveau 1 par technicien (< 5 min) avec   │
│     détermination priorité (P1 à P4) selon matrice impact  │
│  4. Résolution de premier niveau avec base de connaissances│
│     (taux résolution N1: 65% en moyenne)                   │
│  5. Escalade niveau 2 si nécessaire avec transfert complet │
│     du contexte et documentation                           │
│                                                             │
│  Nos engagements de service:                               │
│  - P1 (critique): Prise en charge < 15 min, résolution 4h │
│  - P2 (majeur): Prise en charge < 30 min, résolution 8h   │
│  - P3 (mineur): Prise en charge < 2h, résolution 24h      │
│  - P4 (demande): Prise en charge < 4h, résolution 48h     │
│                                                             │
│  Performance 2023: 12,450 incidents N1 traités, taux      │
│  résolution premier contact 68%, satisfaction 4.2/5"       │
│                                                             │
│ [Bouton: Insérer dans éditeur] [Bouton: Voir document]    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Suggestion 2                                  Score: 87%    │
├─────────────────────────────────────────────────────────────┤
│ Source: Documentation Interne - Processus ITIL (2024)      │
│                                                             │
│ "La gestion des incidents de niveau 1 inclut:             │
│  - Détection proactive par monitoring (80% des incidents)  │
│  - Réception appels/emails/tickets utilisateurs           │
│  - Enregistrement systématique (0 incident non tracé)      │
│  - Classification urgence × impact (matrice 4×4)           │
│  - Diagnostic initial et tentative résolution              │
│  - Documentation systématique dans base de connaissances   │
│  - Mesure KPI: MTTR, taux résolution N1, satisfaction     │
│                                                             │
│  Nos techniciens N1 sont certifiés ITIL Foundation et      │
│  formés sur les outils spécifiques du client."            │
│                                                             │
│ [Bouton: Insérer dans éditeur] [Bouton: Voir document]    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Suggestion 3                                  Score: 84%    │
├─────────────────────────────────────────────────────────────┤
│ Source: Case Study - EPT Val-de-Marne (2020-2024)         │
│                                                             │
│ "Résultats gestion incidents niveau 1 sur 4 ans:          │
│  - Volume: 48,200 incidents traités                        │
│  - Taux résolution N1: 67% (objectif 60%)                 │
│  - Délai moyen prise en charge: 12 min (objectif 15 min)  │
│  - MTTR moyen: 2h15 (objectif 3h)                         │
│  - Satisfaction utilisateur: 92% (objectif 85%)            │
│  - Conformité SLA: 97.8% (pénalités évitées: 145k€)       │
│                                                             │
│  Technologies utilisées: ServiceNow ITSM, Zabbix monitoring│
│  Équipe: 6 techniciens N1 8h-20h, 2 techniciens astreinte"│
│                                                             │
│ [Bouton: Insérer dans éditeur] [Bouton: Voir document]    │
└─────────────────────────────────────────────────────────────┘
```

---

### 🎯 Workflow Bid Manager

**Sans RAG** (Avant):
1. Lire critère "Gestion incidents N1" ⏱️ 2 min
2. Chercher dans dossiers partagés ⏱️ 10-15 min
3. Relire 3-4 anciennes réponses ⏱️ 15-20 min
4. Copier-coller morceaux ⏱️ 5 min
5. Adapter et réécrire ⏱️ 15-20 min
**TOTAL**: 45-60 min par critère

**Avec RAG** (Après):
1. Lire critère "Gestion incidents N1" ⏱️ 2 min
2. Voir 3 suggestions RAG automatiques ⏱️ 3-5 min
3. Choisir suggestion la plus pertinente ⏱️ 1 min
4. Insérer dans éditeur ⏱️ 30s
5. Adapter au contexte spécifique ⏱️ 5-8 min
**TOTAL**: 12-17 min par critère

**GAIN**: 30-45 min par critère
**GAIN TOTAL**: 5-7h par tender (15 critères moyens)

---

### 📊 Métriques de Succès

| KPI | Objectif | Mesure |
|-----|----------|--------|
| **Taux adoption** | >80% | % critères avec suggestion insérée |
| **Qualité suggestions** | >85% | Score pertinence moyen >85% |
| **Gain temps** | >60% | Temps rédaction critère -60% |
| **Réutilisation contenu** | >70% | % suggestions issues past proposals gagnés |
| **Satisfaction** | >4/5 | Note bid managers sur pertinence |

---

### 🛠️ Spécifications Techniques

**Tables impliquées**:
- `tender_criteria` (source: critères extraits)
- `document_embeddings` (search: chunks KB)
- `criterion_suggestions` (output: suggestions stockées)

**API Endpoint**:
```http
POST /api/v1/tenders/{tender_id}/criteria/{criterion_id}/suggest

Response:
{
  "criterion_id": "uuid",
  "suggestions": [
    {
      "id": "uuid",
      "source_type": "past_proposal",
      "source_id": "uuid",
      "source_document": "Mairie Lyon - Mémoire Technique 2023",
      "suggested_text": "Notre processus de gestion...",
      "relevance_score": 0.92,
      "context": {
        "tender_title": "Infogérance IT",
        "won": true,
        "year": 2023
      }
    }
  ]
}
```

**Algorithme RAG**:
1. Encode `criterion.description` → embedding (OpenAI text-embedding-3-small)
2. Query pgvector: `SELECT * FROM document_embeddings WHERE document_type IN ('past_proposal', 'case_study', 'documentation') ORDER BY embedding <=> criterion_embedding LIMIT 10`
3. Rerank Top 10 → Top 3 (cross-encoder ou règles métier)
4. Store dans `criterion_suggestions`

---

## 2️⃣ Recherche Sémantique Libre

### 🎯 Problème Métier

Le bid manager a besoin de trouver du contenu spécifique mais **ne sait pas où il se trouve** dans la Knowledge Base:
- "processus de gestion des changements"
- "certification ISO 27001 description"
- "méthodologie Agile Scrum"
- "datacenter Tier 3 caractéristiques"

**Pain points**:
- Arborescence dossiers complexe (100+ documents)
- Nomenclature incohérente (différents noms pour même concept)
- Contenu enterré dans PDFs de 50+ pages
- Perte de temps à rechercher manuellement

**Temps actuel**: 2-4h par tender (recherche documentaire)

---

### 💡 Solution RAG

**Interface Utilisateur**:

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Recherche dans la Knowledge Base                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [processus de gestion des changements              ] 🔍    │
│                                                             │
│  Filtres: [x] Past Proposals  [x] Documentation             │
│           [ ] Certifications  [ ] Case Studies              │
│           [ ] Templates                                     │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  📄 10 résultats trouvés                    Tri: Pertinence │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ 1. Processus Gestion des Changements ITIL    Score: 94%│
│     Source: Documentation Interne - ITIL v4 2024           │
│     Preview: "Le processus de gestion des changements vise │
│              à contrôler le cycle de vie de tous les       │
│              changements avec un minimum de perturbations.."│
│     Tags: #ITIL #Change-Management #RFC                    │
│     [Voir plus] [Copier] [Insérer dans éditeur]           │
│                                                             │
│  ✅ 2. RFC Process - Mairie Lyon                 Score: 91%│
│     Source: Past Proposal - Mairie Lyon 2023 (GAGNÉ)       │
│     Preview: "Notre processus RFC (Request For Change)     │
│              comprend 7 étapes: 1) Demande initiale..."    │
│     Tags: #RFC #CAB #Production                            │
│     [Voir plus] [Copier] [Insérer dans éditeur]           │
│                                                             │
│  ✅ 3. Change Advisory Board Composition          Score: 87%│
│     Source: Template - Gouvernance IT Standard             │
│     Preview: "Le CAB (Change Advisory Board) est composé   │
│              de 7 membres: DSI, Responsable Production..." │
│     Tags: #CAB #Gouvernance                                │
│     [Voir plus] [Copier] [Insérer dans éditeur]           │
│                                                             │
│  ... (7 autres résultats)                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 📋 Exemple Concret

**Recherche**: "méthodologie agile scrum"

**RAG Retourne** (Top 5):

1. **[Documentation Interne] Score: 95%**
   - "Notre équipe projet suit la méthodologie Agile Scrum avec sprints de 2 semaines. Chaque sprint comprend: Planning Meeting (2h), Daily Standups (15 min), Sprint Review (1h), Rétrospective (1h). Rôles: Product Owner (priorités backlog), Scrum Master (facilitation, blocages), Dev Team (5-7 personnes cross-functional)..."
   - **Tags**: #Agile #Scrum #Méthodologie

2. **[Past Proposal - APHP 2024] Score: 92%**
   - "Nous utilisons Scrum pour la gestion projet avec Product Owner dédié à temps plein, immergé dans les équipes métier. Notre vélocité moyenne est de 45 points par sprint (2 semaines). Outils: Jira pour backlog, Confluence pour documentation, Slack pour communication quotidienne..."
   - **Tags**: #Scrum #Projet #APHP #Gagné-2024

3. **[Certification] Score: 89%**
   - "Scrum Master certifié PSM II (Professional Scrum Master niveau 2, Scrum.org). Notre équipe compte 3 Scrum Masters certifiés et 12 développeurs formés Agile. Nous respectons le Scrum Guide 2020 avec adaptations contextuelles validées avec le client..."
   - **Tags**: #Certification #PSM #Scrum-Master

4. **[Template] Score: 85%**
   - "Présentation méthodologie Agile (slide deck PowerPoint 15 slides réutilisable): Introduction Agile, Manifeste Agile, Framework Scrum, Cérémonies, Artefacts, Rôles, Métriques (vélocité, burndown), Transition vers Agile, FAQ..."
   - **Tags**: #Template #Présentation #Slides

5. **[Case Study - Région IDF] Score: 82%**
   - "Projet migration infrastructure cloud géré en Scrum (12 sprints, 6 mois). Équipe 8 personnes, vélocité initiale 28 pts → finale 52 pts (+85%). Satisfaction Product Owner: 5/5. Livraison dans les délais et budget respecté..."
   - **Tags**: #CaseStudy #Cloud #Scrum

---

### 🎯 Workflow Bid Manager

**Cas d'usage typiques**:

1. **Rédaction en cours**: Besoin d'un concept spécifique
   - Recherche: "datacenter tier 3"
   - Insère description technique trouvée

2. **Vérification**: Vérifier qu'une certification existe
   - Recherche: "ISO 27001"
   - Confirme certificat valide + récupère numéro

3. **Inspiration**: Trouver comment décrire une méthodologie
   - Recherche: "méthodologie devops"
   - Trouve 3 exemples différents, choisit le meilleur

4. **Découverte**: Découvrir du contenu oublié
   - Recherche: "satisfaction client"
   - Trouve témoignage client de 2022 jamais réutilisé

---

### 📊 Métriques de Succès

| KPI | Objectif | Mesure |
|-----|----------|--------|
| **Temps recherche** | <30s | P95 latence recherche |
| **Précision** | >80% | % requêtes où résultat pertinent dans Top 3 |
| **Rappel** | >85% | % contenu pertinent retrouvé |
| **Fréquence usage** | 5-10x/tender | Nombre recherches par bid manager |
| **Taux insertion** | >60% | % résultats insérés dans réponse |

---

### 🛠️ Spécifications Techniques

**API Endpoint**:
```http
POST /api/v1/search/semantic

Request:
{
  "query": "méthodologie agile scrum",
  "filters": {
    "document_types": ["past_proposal", "documentation", "template"],
    "date_range": {
      "start": "2022-01-01",
      "end": "2025-12-31"
    }
  },
  "top_k": 10
}

Response:
{
  "query": "méthodologie agile scrum",
  "results": [
    {
      "id": "uuid",
      "document_id": "uuid",
      "document_type": "documentation",
      "source_document": "Documentation Interne - ITIL v4 2024",
      "chunk_text": "Notre équipe projet suit...",
      "similarity_score": 0.95,
      "metadata": {
        "chunk_index": 12,
        "total_chunks": 45,
        "tags": ["Agile", "Scrum", "Méthodologie"],
        "created_at": "2024-03-15"
      }
    }
  ],
  "total_results": 10,
  "search_time_ms": 127
}
```

**Algorithme**:
1. Encode `query` → embedding (OpenAI)
2. Query pgvector avec filtres optionnels
3. Retourne Top K avec scores
4. Log recherche pour analytics

---

## 3️⃣ Références Clients Contextuelles

### 🎯 Problème Métier

Les tenders demandent systématiquement **3-5 références clients similaires** avec critères précis:
- Secteur d'activité (collectivité, santé, éducation...)
- Taille organisation (nombre utilisateurs, budget...)
- Type de prestation (infogérance, support, hébergement...)
- Durée contrat et résultats obtenus

**Pain points**:
- 50+ références clients dans la base
- Difficile de trouver la plus similaire
- Risque de proposer référence non pertinente → mauvaise note
- Temps perdu à comparer manuellement

**Temps actuel**: 1-2h par tender (sélection références)

---

### 💡 Solution RAG

**Matching Intelligent**:

```
1. Analyse contexte tender automatiquement:
   - Organisation: "EPT Vallée Sud Grand Paris"
   - Secteur: "Collectivité territoriale"
   - Taille: "1200 utilisateurs, 40 sites"
   - Prestations: "Infogérance infrastructure + Support N1"

2. RAG encode le contexte en embedding

3. Recherche dans case_studies avec:
   - Similarité sémantique (60% poids)
   - Filtres métadonnées (40% poids):
     * Même secteur (+30 points)
     * Taille similaire ±30% (+20 points)
     * Même type prestation (+25 points)
     * Contrat > 2 ans (+15 points)
     * Résultats positifs (+10 points)

4. Retourne Top 3-5 références les mieux matchées
```

---

### 📋 Exemple Concret

**Tender**: EPT Vallée Sud Grand Paris - Infogérance

**Contexte Extrait**:
```json
{
  "organization_type": "EPT (Établissement Public Territorial)",
  "sector": "Collectivité territoriale",
  "users": 1200,
  "sites": 40,
  "services": ["Infogérance infrastructure", "Support N1", "Supervision"],
  "budget_range": "500k-1M€/an"
}
```

**RAG Retourne** (Top 3):

```
┌─────────────────────────────────────────────────────────────┐
│ 🏆 Référence #1                       Match Score: 95%      │
├─────────────────────────────────────────────────────────────┤
│ Client: EPT Val-de-Marne                                    │
│ Type: Établissement Public Territorial (94)                │
│ Période: 2020-2024 (4 ans)                                 │
│ Budget: 2.4M€ total (600k€/an)                             │
│                                                             │
│ 📊 Contexte:                                                │
│ • 1500 utilisateurs (vs 1200 demandé) ✅                   │
│ • 35 sites (vs 40 demandé) ✅                              │
│ • Services: Infogérance complète + Support N1-N2 ✅        │
│                                                             │
│ 📈 Résultats:                                               │
│ • Disponibilité: 99.7% (objectif 99.5%)                    │
│ • Satisfaction: 92% (objectif 85%)                         │
│ • Incidents N1: 48,200 traités, 67% résolus premier niveau │
│ • Délai résolution moyen: 2h15 (objectif 3h)               │
│ • Conformité SLA: 97.8% (pénalités évitées: 145k€)         │
│                                                             │
│ 👤 Contact référent:                                        │
│ • Nom: Jean Dupont - DSI EPT Val-de-Marne                  │
│ • Email: jean.dupont@valdemarne.fr                         │
│ • Tel: 01 XX XX XX XX                                      │
│ • Autorisation contact: ✅ Oui                             │
│                                                             │
│ 📄 Documents disponibles:                                   │
│ • Attestation fin de contrat                               │
│ • Témoignage client (vidéo 3 min)                          │
│ • Case study détaillé (PDF 8 pages)                        │
│                                                             │
│ [Bouton: Ajouter à la réponse] [Bouton: Voir case study]  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🥈 Référence #2                       Match Score: 87%      │
├─────────────────────────────────────────────────────────────┤
│ Client: Mairie de Montreuil (93)                           │
│ Type: Commune urbaine                                      │
│ Période: 2021-2024 (3 ans)                                 │
│ Budget: 1.8M€ total (600k€/an)                             │
│                                                             │
│ 📊 Contexte:                                                │
│ • 800 utilisateurs (vs 1200 demandé) ⚠️ Plus petit        │
│ • 15 sites (vs 40 demandé) ⚠️ Moins de sites              │
│ • Services: Support N1-N2 + Hébergement datacenter ✅      │
│                                                             │
│ 📈 Résultats:                                               │
│ • Satisfaction: 94% (très élevée)                          │
│ • Migration cloud réussie en 6 mois                        │
│ • Réduction coûts infra: -25%                              │
│ • Disponibilité services: 99.8%                            │
│                                                             │
│ 👤 Contact référent: Marie Martin - DSI Montreuil          │
│ 📄 Documents: Attestation + témoignage écrit               │
│                                                             │
│ [Bouton: Ajouter à la réponse] [Bouton: Voir case study]  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🥉 Référence #3                       Match Score: 82%      │
├─────────────────────────────────────────────────────────────┤
│ Client: Conseil Départemental 77                           │
│ Type: Collectivité départementale                          │
│ Période: 2019-2023 (4 ans)                                 │
│ Budget: 3.2M€ total (800k€/an)                             │
│                                                             │
│ 📊 Contexte:                                                │
│ • 2200 utilisateurs (vs 1200 demandé) ⚠️ Plus grand       │
│ • 60 sites (vs 40 demandé) ✅ Plus complexe               │
│ • Services: Infogérance complète + Sécurité SOC ✅         │
│                                                             │
│ 📈 Résultats:                                               │
│ • Modernisation infrastructure (50+ serveurs)              │
│ • Certification ISO 27001 obtenue                          │
│ • Zéro incident sécurité majeur en 4 ans                   │
│                                                             │
│ 👤 Contact référent: Pierre Leroy - DSI CD77               │
│ 📄 Documents: Case study détaillé + attestation           │
│                                                             │
│ [Bouton: Ajouter à la réponse] [Bouton: Voir case study]  │
└─────────────────────────────────────────────────────────────┘
```

---

### 🎯 Workflow Bid Manager

**Avec RAG**:
1. Ouvre section "Références clients" ⏱️ 30s
2. Voit 3 suggestions automatiques pré-matchées ⏱️ 2-3 min
3. Vérifie pertinence (taille, secteur, résultats) ⏱️ 3-5 min
4. Sélectionne les 3 références ⏱️ 1 min
5. Adapte descriptions si nécessaire ⏱️ 5-10 min
**TOTAL**: 12-20 min

**GAIN**: 40-80 min par tender

---

### 📊 Métriques de Succès

| KPI | Objectif | Mesure |
|-----|----------|--------|
| **Précision matching** | >85% | % références acceptées par bid manager |
| **Diversité** | 3 secteurs différents | Éviter 3 refs identiques |
| **Complétude** | 100% | Toutes refs ont contact + résultats |
| **Taux réussite** | >75% | % tenders avec refs RAG insérées |

---

### 🛠️ Spécifications Techniques

**Table `case_studies`** (à créer):
```sql
CREATE TABLE case_studies (
    id UUID PRIMARY KEY,
    client_name VARCHAR(200),
    client_type VARCHAR(100),  -- EPT, Mairie, Département, Région, Hôpital...
    sector VARCHAR(100),  -- Collectivité, Santé, Éducation...
    users_count INT,
    sites_count INT,
    services JSONB,  -- ["Infogérance", "Support N1", ...]
    contract_start_date DATE,
    contract_end_date DATE,
    budget_annual DECIMAL,
    results_summary TEXT,
    kpis JSONB,  -- {"availability": 99.7, "satisfaction": 92, ...}
    contact_name VARCHAR(200),
    contact_email VARCHAR(200),
    contact_phone VARCHAR(50),
    contact_authorized BOOLEAN,
    documents JSONB,  -- [{"type": "attestation", "url": "..."}, ...]
    created_at TIMESTAMP
);
```

**API Endpoint**:
```http
POST /api/v1/tenders/{tender_id}/references/suggest

Response:
{
  "tender_context": {
    "organization_type": "EPT",
    "sector": "Collectivité",
    "users": 1200,
    "services": ["Infogérance", "Support N1"]
  },
  "suggested_references": [
    {
      "case_study_id": "uuid",
      "match_score": 0.95,
      "client_name": "EPT Val-de-Marne",
      "match_reasons": [
        "Même type organisation (+30 pts)",
        "Taille similaire (+20 pts)",
        "Services identiques (+25 pts)",
        "Résultats excellents (+15 pts)"
      ],
      "summary": {...},
      "documents": [...]
    }
  ]
}
```

---

## 4️⃣ Compliance & Certifications Auto-Proof

### 🎯 Problème Métier

Les tenders exigent **certifications obligatoires** avec preuves:
- ISO 27001 (sécurité info)
- ISO 9001 (qualité)
- HDS (Hébergement Données Santé)
- Qualiopi (formations)
- Certifications individuelles (Scrum Master, ITIL, etc.)

**Pain points**:
- Risque d'oubli → disqualification automatique
- Recherche manuelle des certificats (scan, PDF...)
- Rédaction description certification (pourquoi pertinent?)
- Vérification dates validité

**Temps actuel**: 30-60 min par tender (compliance check)

---

### 💡 Solution RAG

**Détection + Auto-Insert**:

```
1. Claude analyse CCTP et détecte exigences:
   → "ISO 27001 OBLIGATOIRE"
   → "Certification Scrum Master souhaitée"

2. RAG cherche dans KB type=certification:
   - Trouve certificat ISO 27001 (PDF + métadonnées)
   - Trouve 3 Scrum Masters certifiés

3. Pour chaque certification trouvée:
   - Vérifie date validité (alerte si expiré)
   - Récupère paragraphe pré-rédigé d'explication
   - Suggère insertion automatique section "Conformité"

4. Si certification manquante:
   - ⚠️ Alerte bid manager (risque disqualification)
   - Suggère alternatives si possibles
```

---

### 📋 Exemple Concret

**Exigence Détectée**: "Certification ISO 27001 OBLIGATOIRE (cf. RC art. 3.2)"

**RAG Fournit**:

```
┌─────────────────────────────────────────────────────────────┐
│ ✅ Certification ISO 27001 - TROUVÉE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📜 Certificat:                                              │
│ • Numéro: FR-2019-12345-ISO27001                           │
│ • Organisme: AFNOR Certification                           │
│ • Date obtention: 15/03/2019                               │
│ • Date validité: 14/03/2026 ✅ Valide 1 an                │
│ • Périmètre: Infogérance infrastructure IT + Datacenter    │
│ • Norme: ISO/IEC 27001:2013                                │
│                                                             │
│ 📄 Document: [certificat_iso27001_2024.pdf] (245 KB)       │
│                                                             │
│ ✍️ Texte pré-rédigé suggéré:                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ "Notre organisation est certifiée ISO 27001:2013 depuis│ │
│ │  2019 (certificat AFNOR #FR-2019-12345). Cette         │ │
│ │  certification atteste de notre Système de Management  │ │
│ │  de la Sécurité de l'Information (SMSI) couvrant       │ │
│ │  l'ensemble de nos activités d'infogérance et          │ │
│ │  d'hébergement datacenter.                             │ │
│ │                                                         │ │
│ │  Notre SMSI comprend:                                  │ │
│ │  • Analyse de risques annuelle avec plan de traitement│ │
│ │  • Politiques de sécurité (60+ documents)              │ │
│ │  • Procédures de gestion incidents sécurité            │ │
│ │  • Audits internes semestriels + audit externe annuel  │ │
│ │  • Veille réglementaire (RGPD, NIS, ANSSI)             │ │
│ │  • Formation continue équipes sécurité                 │ │
│ │                                                         │ │
│ │  Certification valide jusqu'au 14/03/2026, avec audits │ │
│ │  de surveillance annuels réalisés par AFNOR. Dernier   │ │
│ │  audit: septembre 2024 (0 non-conformité majeure)."    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [Bouton: Insérer dans section Conformité]                  │
│ [Bouton: Joindre certificat PDF à la réponse]              │
│ [Bouton: Voir certificat complet]                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ✅ Certifications Complémentaires Disponibles               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ • ISO 9001:2015 (Qualité) - Valide jusqu'à 2025           │
│ • HDS (Hébergement Données Santé) - Valide jusqu'à 2026    │
│ • 3 Scrum Masters PSM II certifiés                         │
│ • 8 techniciens ITIL Foundation v4                         │
│ • Datacenter certifié Tier 3 (Uptime Institute)            │
│                                                             │
│ [Bouton: Voir toutes les certifications]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Si Certification Manquante**:

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️  Certification Qualiopi - NON TROUVÉE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ❌ Cette certification est OBLIGATOIRE (cf. RC art. 5.3)   │
│                                                             │
│ 💡 Actions recommandées:                                    │
│ • Vérifier si certification en cours d'obtention           │
│ • Mentionner engagement à obtenir sous 6 mois              │
│ • Proposer partenariat avec organisme certifié             │
│                                                             │
│ ⚠️  RISQUE: Disqualification possible si non justifiée     │
│                                                             │
│ [Bouton: Ajouter à la checklist de suivi]                  │
│ [Bouton: Notifier responsable certifications]              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 🎯 Workflow Bid Manager

**Avec RAG**:
1. Ouvre tender → Claude détecte exigences certifications ⏱️ Auto
2. RAG affiche toutes certifications requises + statut ⏱️ 2-3 min
3. Pour chaque certification trouvée:
   - Vérifie validité ⏱️ 10s
   - Insère texte pré-rédigé ⏱️ 30s
   - Joint PDF certificat ⏱️ 20s
4. Si certification manquante: alerte + action ⏱️ 5 min
**TOTAL**: 10-15 min

**GAIN**: 15-45 min par tender
**SÉCURITÉ**: Zéro oubli de certification obligatoire

---

### 📊 Métriques de Succès

| KPI | Objectif | Mesure |
|-----|----------|--------|
| **Détection complète** | 100% | % exigences certifications détectées |
| **Taux matching** | >95% | % certifications requises trouvées en KB |
| **Zéro oubli** | 100% | Aucun tender sans vérif certifications |
| **Alertes validité** | 100% | Alertes si certificat expire <6 mois |

---

### 🛠️ Spécifications Techniques

**Table `certifications`** (à créer):
```sql
CREATE TABLE certifications (
    id UUID PRIMARY KEY,
    certification_type VARCHAR(100),  -- ISO27001, ISO9001, HDS, Qualiopi...
    certification_name VARCHAR(200),
    certificate_number VARCHAR(100),
    issuing_body VARCHAR(200),
    issue_date DATE,
    expiry_date DATE,
    scope TEXT,
    certificate_pdf_url VARCHAR(500),
    description_template TEXT,  -- Texte pré-rédigé réutilisable
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**API Endpoint**:
```http
GET /api/v1/tenders/{tender_id}/compliance/check

Response:
{
  "required_certifications": [
    {
      "requirement": "ISO 27001 OBLIGATOIRE",
      "status": "found",
      "certification": {
        "id": "uuid",
        "type": "ISO27001",
        "number": "FR-2019-12345",
        "valid_until": "2026-03-14",
        "days_until_expiry": 365,
        "certificate_url": "s3://...",
        "description_template": "Notre organisation est certifiée..."
      }
    },
    {
      "requirement": "Qualiopi souhaité",
      "status": "not_found",
      "risk_level": "medium",
      "recommended_actions": [...]
    }
  ],
  "compliance_score": 0.85,
  "missing_critical": []
}
```

---

## 5️⃣ Smart Templates Assembly

### 🎯 Problème Métier

Chaque réponse contient **sections récurrentes** quasi-identiques:
- Présentation de l'entreprise (histoire, chiffres clés, valeurs)
- Méthodologie de projet (Agile, cycle en V, PRINCE2...)
- Composition de l'équipe type (organigramme, compétences)
- Infrastructure technique (datacenter, réseau, sécurité)
- Engagements RSE et environnementaux

**Pain points**:
- Réécriture à chaque tender avec variations minimes
- Risque d'incohérence (chiffres différents, dates...)
- Temps perdu sur sections "boilerplate"

**Temps actuel**: 3-4h par tender (sections standard)

---

### 💡 Solution RAG

**Pré-Remplissage Intelligent**:

```
1. Claude analyse structure CCTP:
   → Détecte sections: "Présentation candidat", "Moyens humains", "Moyens techniques"

2. RAG mappe sections CCTP → templates KB:
   - "Présentation candidat" → Template "Présentation Entreprise v2024"
   - "Moyens humains" → Template "Composition Équipe Standard"
   - "Moyens techniques" → Template "Infrastructure Datacenter Tier 3"

3. Auto-insertion dans éditeur de réponse:
   - Sections standard pré-remplies (90% complètes)
   - Placeholders pour infos spécifiques (nom responsable, dates...)
   - Bid manager adapte uniquement le contexte

4. Personnalisation:
   - Bid manager modifie nom responsable compte
   - Ajuste dates de disponibilité
   - Ajoute spécificités tender (ex: localisation datacenter)
```

---

### 📋 Exemple Concret

**Sections Détectées dans CCTP**:

```
Section 2.1 - Présentation du candidat
Section 2.2 - Moyens humains et organisation
Section 2.3 - Moyens techniques
Section 2.4 - Références clients (≥ 3)
Section 2.5 - Méthodologie projet
```

**RAG Pré-Remplit**:

```
┌─────────────────────────────────────────────────────────────┐
│ 📝 Éditeur de Réponse - VSGP Infogérance                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Section 2.1 - Présentation du candidat        [90% rempli] │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Template: Présentation Entreprise v2024]              │ │
│ │                                                         │ │
│ │ [Logo Entreprise]                                      │ │
│ │                                                         │ │
│ │ Notre société, créée en 2005, est spécialisée dans     │ │
│ │ l'infogérance d'infrastructures IT et le support      │ │
│ │ utilisateur pour les collectivités territoriales et    │ │
│ │ établissements publics.                                │ │
│ │                                                         │ │
│ │ Chiffres clés 2024:                                    │ │
│ │ • Chiffre d'affaires: 12.5M€ (+15% vs 2023)           │ │
│ │ • Effectif: 85 collaborateurs                          │ │
│ │ • Clients: 28 collectivités, 45,000 utilisateurs      │ │
│ │ • Taux fidélisation: 96% (reconductions contrats)     │ │
│ │                                                         │ │
│ │ Nos valeurs:                                           │ │
│ │ • Excellence technique et innovation continue          │ │
│ │ • Proximité et réactivité (agences Île-de-France)     │ │
│ │ • Engagement RSE (Bilan Carbone, achats responsables) │ │
│ │                                                         │ │
│ │ Certifications: ISO 27001, ISO 9001, HDS, Qualiopi    │ │
│ │                                                         │ │
│ │ ⚠️  À PERSONNALISER:                                   │ │
│ │ [ ] Nom responsable compte: _______________           │ │
│ │ [ ] Agence référente: [ ] Paris [ ] Versailles        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Section 2.2 - Moyens humains                  [85% rempli] │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Template: Composition Équipe Standard]                │ │
│ │                                                         │ │
│ │ [Organigramme schématique]                             │ │
│ │                                                         │ │
│ │ Équipe dédiée au contrat:                              │ │
│ │ • 1 Responsable de compte (pilotage global)           │ │
│ │ • 1 Chef de projet technique (coordination)            │ │
│ │ • 6 Techniciens support N1 (8h-20h)                   │ │
│ │ • 4 Ingénieurs N2-N3 (expertise pointue)              │ │
│ │ • 2 Techniciens astreinte (20h-8h + week-ends)        │ │
│ │                                                         │ │
│ │ Compétences clés:                                      │ │
│ │ • ITIL v4: 12 personnes certifiées                    │ │
│ │ • Scrum Master: 3 personnes PSM II                    │ │
│ │ • Sécurité: 4 personnes CISSP ou équivalent           │ │
│ │                                                         │ │
│ │ Formation continue: 40h/an par collaborateur          │ │
│ │                                                         │ │
│ │ ⚠️  À ADAPTER:                                         │ │
│ │ [ ] Ajuster taille équipe si besoin: ______           │ │
│ │ [ ] Mentionner compétences spécifiques VSGP: ______   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Section 2.3 - Moyens techniques               [95% rempli] │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [Template: Infrastructure Datacenter Tier 3]           │ │
│ │                                                         │ │
│ │ Notre infrastructure technique repose sur 2 datacenters│ │
│ │ certifiés Tier 3 (Uptime Institute) situés à:         │ │
│ │ • Datacenter principal: Saint-Denis (93)               │ │
│ │ • Datacenter secours: Nanterre (92)                    │ │
│ │                                                         │ │
│ │ Caractéristiques techniques:                           │ │
│ │ • Redondance électrique: N+1 (2 arrivées EDF)         │ │
│ │ • Climatisation: Free-cooling + groupes froid         │ │
│ │ • Disponibilité garantie: 99.98%                       │ │
│ │ • Connexions: 2× 10 Gbps fibre (opérateurs distincts) │ │
│ │                                                         │ │
│ │ Sécurité physique:                                     │ │
│ │ • Contrôle accès biométrique                           │ │
│ │ • Vidéosurveillance 24/7                              │ │
│ │ • Gardiennage permanent                                │ │
│ │                                                         │ │
│ │ Outils de supervision:                                 │ │
│ │ • Zabbix (monitoring infrastructure)                   │ │
│ │ • ServiceNow (ITSM)                                    │ │
│ │ • Splunk (SIEM sécurité)                              │ │
│ │                                                         │ │
│ │ ⚠️  À VÉRIFIER:                                        │ │
│ │ [ ] Localisation datacenters OK pour VSGP: ✅         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [Autres sections à remplir manuellement...]                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 🎯 Workflow Bid Manager

**Avec RAG**:
1. Ouvre éditeur réponse ⏱️ 30s
2. RAG pré-remplit 5 sections standard ⏱️ Auto (5s)
3. Bid manager vérifie sections pré-remplies ⏱️ 10-15 min
4. Adapte placeholders et infos spécifiques ⏱️ 15-20 min
5. Complète sections non-template ⏱️ 2-3h
**TOTAL**: 2h30-3h50 (vs 6-8h avant)

**GAIN**: 3-4h par tender

---

### 📊 Métriques de Succès

| KPI | Objectif | Mesure |
|-----|----------|--------|
| **Taux pré-remplissage** | >60% | % contenu réponse pré-rempli par templates |
| **Cohérence** | 100% | Aucune incohérence chiffres/dates entre tenders |
| **Qualité templates** | >4/5 | Note bid managers sur qualité templates |
| **Personnalisation** | <30 min | Temps adaptation templates par tender |

---

### 🛠️ Spécifications Techniques

**Table `templates`** (à créer):
```sql
CREATE TABLE templates (
    id UUID PRIMARY KEY,
    template_name VARCHAR(200),
    template_type VARCHAR(100),  -- presentation, team, infrastructure, methodology...
    version VARCHAR(20),  -- v2024, v2025...
    content TEXT,  -- Contenu markdown avec placeholders
    placeholders JSONB,  -- [{"name": "responsable_compte", "type": "text", "required": true}, ...]
    tags JSONB,  -- ["entreprise", "collectivité", ...]
    usage_count INT DEFAULT 0,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Format Template**:
```markdown
# Présentation de l'Entreprise

{{logo_entreprise}}

Notre société, créée en {{annee_creation}}, est spécialisée dans...

Chiffres clés {{annee_en_cours}}:
• Chiffre d'affaires: {{ca_annuel}}M€
• Effectif: {{nombre_collaborateurs}} collaborateurs
• Clients: {{nombre_clients}} collectivités...

⚠️  À PERSONNALISER:
- [ ] Nom responsable compte: {{responsable_compte}}
- [ ] Agence référente: {{agence}}
```

**API Endpoint**:
```http
POST /api/v1/tenders/{tender_id}/proposal/auto-fill

Response:
{
  "sections_filled": 5,
  "sections_total": 12,
  "coverage_percentage": 42,
  "templates_used": [
    {
      "template_id": "uuid",
      "template_name": "Présentation Entreprise v2024",
      "section": "2.1 - Présentation candidat",
      "placeholders_remaining": [
        {"name": "responsable_compte", "required": true},
        {"name": "agence", "required": false}
      ]
    }
  ]
}
```

---

## 📊 Récapitulatif Global

### Gains Cumulés par Tender

| Use Case | Temps Gagné | Fréquence | Impact |
|----------|-------------|-----------|--------|
| 1. Auto-Suggestion par Critère | 5-7h | 100% | ⭐⭐⭐⭐⭐ |
| 2. Recherche Sémantique Libre | 2-3h | 90% | ⭐⭐⭐⭐⭐ |
| 3. Références Clients | 1-2h | 80% | ⭐⭐⭐⭐ |
| 4. Compliance Auto-Proof | 30-60 min | 100% | ⭐⭐⭐⭐ |
| 5. Smart Templates | 3-4h | 70% | ⭐⭐⭐ |
| **TOTAL MOYEN** | **12-17h** | - | **Très Élevé** |

**Équivalent**: **2-3 jours de travail** économisés par réponse
**ROI Annuel**: Pour 20 tenders/an → **240-340h** gagnées → **30-42 jours** → **1.5-2 mois ETP**

---

### Stratégie d'Implémentation

#### Phase 1 - MVP Critique (Semaines 1-2)
**Objectif**: Délivrer 80% de la valeur rapidement

✅ **Use Case #1**: Auto-Suggestion par Critère
- Moteur RAG de base (OpenAI embeddings + pgvector)
- API suggestions par critère
- UI simple liste suggestions

✅ **Use Case #2**: Recherche Sémantique Libre
- Même moteur RAG
- Barre recherche + résultats
- Filtres par type document

**Effort**: 10-12 jours
**Impact**: 7-10h gagnées/tender

---

#### Phase 2 - Valeur Ajoutée (Semaine 3)
**Objectif**: Ajouter différenciation compétitive

✅ **Use Case #3**: Références Clients
- Matching intelligent contexte tender
- Table case_studies
- Scoring multi-critères

✅ **Use Case #4**: Compliance Auto-Proof
- Détection exigences certifications
- Table certifications
- Alertes validité

**Effort**: 5-6 jours
**Impact**: +2-3h gagnées/tender

---

#### Phase 3 - Optimisation (Semaine 4)
**Objectif**: Maximiser productivité

✅ **Use Case #5**: Smart Templates Assembly
- Mapping sections CCTP → templates
- Auto-fill avec placeholders
- Gestion versions templates

**Effort**: 4-5 jours
**Impact**: +3-4h gagnées/tender

---

## 🎯 Prochaines Étapes

1. ✅ **Validation use cases** avec bid managers (feedback)
2. 🔨 **Création schéma BD** (tables: case_studies, certifications, templates)
3. 🔨 **Implémentation RAG engine** (OpenAI + pgvector)
4. 🔨 **API endpoints** (5 endpoints principaux)
5. 🔨 **Tests E2E** avec données réelles
6. 🔨 **UI/UX** pour chaque use case
7. 🚀 **Déploiement Phase 1** (MVP)

---

**Dernière mise à jour**: 2 octobre 2025
**Auteur**: Équipe ScorpiusAO
**Version**: 1.0 - Définition initiale
