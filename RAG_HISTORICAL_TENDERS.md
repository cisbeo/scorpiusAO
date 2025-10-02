# 📚 RAG Knowledge Base - Tenders Historiques

**Date**: 2 octobre 2025
**Version**: 1.0
**Objectif**: Définir comment intégrer les appels d'offres passés dans la Knowledge Base

---

## 🎯 Problématique

Actuellement, la KB stocke uniquement les **réponses gagnantes** (`past_proposals`). Cependant, pour maximiser l'apprentissage et la pertinence des suggestions RAG, il faut également stocker les **appels d'offres originaux** (tenders) qui ont donné lieu à ces réponses.

### Pourquoi Stocker les Tenders Historiques ?

#### 1. **Matching Contextuel Amélioré**
Permet de comparer le tender actuel avec des tenders passés similaires et retrouver:
- Les réponses qui ont fonctionné sur des AO similaires
- Les stratégies gagnantes par type de tender
- Les pièges à éviter (critères sous-estimés, exigences cachées)

#### 2. **Apprendre des Échecs**
Stocker aussi les **tenders perdus** permet de:
- Identifier pourquoi une réponse a échoué
- Comparer réponse gagnante vs réponse perdante sur même type d'AO
- Éviter de reproduire les mêmes erreurs

#### 3. **Analyse Comparative**
Comparer les critères d'évaluation:
- Évolution des critères dans le temps
- Poids technique vs financier par secteur
- Nouvelles exigences émergentes (cybersécurité, RSE...)

#### 4. **Recherche Sémantique Enrichie**
Rechercher dans les CCTP/RC passés:
- "Quels tenders demandaient ISO 27001 ?"
- "Références aux processus ITIL dans les AO santé"
- "Évolution des SLA dans les collectivités"

---

## 🗂️ Schéma de Données Étendu

### Nouvelle Table: `historical_tenders`

**Rôle**: Stocke les appels d'offres passés avec lien vers les réponses soumises

```sql
CREATE TABLE historical_tenders (
    -- Identité
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_document_id UUID REFERENCES kb_documents(id) ON DELETE SET NULL,
    -- NULL si pas de document KB (juste métadonnées)

    -- Informations Tender
    title VARCHAR(500) NOT NULL,
    organization VARCHAR(200) NOT NULL,
    organization_type VARCHAR(100),  -- EPT, Mairie, Département, Hôpital...
    reference_number VARCHAR(100),
    publication_date DATE,
    deadline DATE NOT NULL,

    -- Secteur & Contexte
    sector VARCHAR(100),  -- Collectivité, Santé, Éducation, Industrie...
    geographic_zone VARCHAR(200),  -- Île-de-France, PACA, National...

    -- Taille Organisation
    estimated_users INT,  -- Nombre utilisateurs finaux
    estimated_sites INT,  -- Nombre sites/implantations
    estimated_budget DECIMAL(15,2),  -- Budget estimé (€)

    -- Type Marché
    contract_type VARCHAR(100),  -- Infogérance, Support, Hébergement, TMA...
    contract_duration_months INT,
    contract_renewal_possible BOOLEAN,

    -- Procédure
    procedure_type VARCHAR(50),  -- Ouvert, Restreint, Dialogue compétitif...
    lot_number INT,  -- Si marché à lots
    total_lots INT,

    -- Services Demandés
    services JSONB DEFAULT '[]',
    -- ["Infogérance", "Support N1-N2", "Hébergement", "Supervision"]

    -- Documents Tender
    documents JSONB DEFAULT '[]',
    -- [
    --   {"type": "CCTP", "kb_document_id": "uuid", "pages": 69},
    --   {"type": "CCAP", "kb_document_id": "uuid", "pages": 38},
    --   {"type": "RC", "kb_document_id": "uuid", "pages": 12}
    -- ]

    -- Critères Évaluation
    evaluation_criteria JSONB,
    -- {
    --   "technique": {"weight": 40, "sub_criteria": [...]},
    --   "financier": {"weight": 60, "sub_criteria": [...]},
    --   "rse": {"weight": 10, "sub_criteria": [...]}
    -- }

    -- Exigences Clés
    mandatory_certifications JSONB DEFAULT '[]',
    -- ["ISO 27001", "HDS", "Qualiopi"]
    mandatory_references INT,  -- Nombre références exigées
    min_team_size INT,

    -- Technologies Mentionnées
    technologies JSONB DEFAULT '[]',
    -- ["ServiceNow", "VMware", "Zabbix"] - outils imposés ou suggérés

    -- Processus ITIL Demandés
    itil_processes JSONB DEFAULT '[]',
    -- ["Incident Management", "Change Management", "Problem Management"]

    -- Niveau Service (SLA)
    sla_requirements JSONB,
    -- {
    --   "availability": "99.7%",
    --   "p1_response_time": "15min",
    --   "p1_resolution_time": "4h"
    -- }

    -- Résultat Notre Participation
    participated BOOLEAN DEFAULT true,
    result VARCHAR(20) CHECK (result IN ('won', 'lost', 'abandoned', 'disqualified', 'not_submitted')),
    our_rank INT,  -- Notre classement (1 = gagnant)
    total_candidates INT,  -- Nombre total candidats
    our_score DECIMAL(5,2),  -- Notre note (/20 ou /100)
    winner_score DECIMAL(5,2),  -- Note du gagnant

    -- Lien vers Notre Réponse
    our_proposal_id UUID REFERENCES past_proposals(id) ON DELETE SET NULL,
    -- NULL si pas répondu ou réponse non archivée

    -- Informations Gagnant (si connu)
    winner_name VARCHAR(200),
    winner_contract_value DECIMAL(15,2),

    -- Analyse Post-Mortem
    lessons_learned TEXT,  -- Pourquoi gagné/perdu, leçons apprises
    competitive_analysis TEXT,  -- Analyse concurrence
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('easy', 'medium', 'hard', 'very_hard')),

    -- Source
    source_platform VARCHAR(50),  -- BOAMP, AWS PLACE, Achats-publics.fr...
    source_url VARCHAR(500),

    -- Métadonnées
    tags JSONB DEFAULT '[]',
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    archived_at TIMESTAMP,  -- Date archivage dans KB

    CONSTRAINT historical_tenders_pkey PRIMARY KEY (id)
);

-- Indexes
CREATE INDEX idx_historical_tenders_kb_document ON historical_tenders(kb_document_id);
CREATE INDEX idx_historical_tenders_organization ON historical_tenders(organization);
CREATE INDEX idx_historical_tenders_sector ON historical_tenders(sector);
CREATE INDEX idx_historical_tenders_deadline ON historical_tenders(deadline DESC);
CREATE INDEX idx_historical_tenders_result ON historical_tenders(result);
CREATE INDEX idx_historical_tenders_participated ON historical_tenders(participated);
CREATE INDEX idx_historical_tenders_our_proposal ON historical_tenders(our_proposal_id);
CREATE INDEX idx_historical_tenders_services ON historical_tenders USING GIN (services);
CREATE INDEX idx_historical_tenders_technologies ON historical_tenders USING GIN (technologies);
CREATE INDEX idx_historical_tenders_certifications ON historical_tenders USING GIN (mandatory_certifications);
CREATE INDEX idx_historical_tenders_tags ON historical_tenders USING GIN (tags);

-- Index composite pour recherche similaire
CREATE INDEX idx_historical_tenders_similarity ON historical_tenders(
    sector, contract_type, estimated_users, result
);
```

---

### Table Modifiée: `past_proposals` (avec lien tender)

Ajouter colonne pour lier à `historical_tenders`:

```sql
ALTER TABLE past_proposals
ADD COLUMN historical_tender_id UUID REFERENCES historical_tenders(id) ON DELETE SET NULL;

-- Index
CREATE INDEX idx_past_proposals_historical_tender ON past_proposals(historical_tender_id);
```

**Bidirectionnalité**:
- `historical_tenders.our_proposal_id` → `past_proposals.id`
- `past_proposals.historical_tender_id` → `historical_tenders.id`

---

## 🎯 Nouveaux Use Cases RAG

### Use Case #6: Analyse Comparative Tenders Similaires ⭐⭐⭐⭐

**Problème**: Bid manager ne sait pas comment ce tender se compare aux AO passés

**Solution RAG**:

```
1. Nouveau tender reçu → Extraction contexte automatique:
   - Secteur: Collectivité
   - Taille: 1200 users
   - Services: Infogérance + Support N1
   - Budget estimé: 600k€/an

2. RAG recherche dans historical_tenders:
   - Matching similarité sémantique (embedding CCTP)
   - Filtres métadonnées (secteur, taille ±30%, services similaires)
   - Retourne Top 5 tenders les plus similaires

3. Pour chaque tender similaire:
   - Affiche critères d'évaluation comparés
   - Montre notre résultat (gagné/perdu + score)
   - Suggère stratégie gagnante si applicable

4. Dashboard comparatif:
   - "3 tenders similaires gagnés dans les 2 ans"
   - "Critères techniques poids moyen: 42% (vs 40% ici)"
   - "SLA P1 typique: <15min (vs <20min demandé ici)"
```

**UI Mockup**:

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Tenders Similaires Passés                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 5 tenders similaires trouvés (2020-2024)                   │
│                                                             │
│ ✅ 1. EPT Val-de-Marne - Infogérance (2020)   Score: 95%  │
│     Secteur: Collectivité ✓  |  1500 users ✓  |  WON 🏆   │
│     Notre score: 18.2/20 (1er/4)                           │
│     ┌────────────────────────────────────────────────────┐ │
│     │ Critères clés:                                     │ │
│     │ • Technique: 40% (vs 40% actuel) ✓                │ │
│     │ • Financier: 60% (vs 60% actuel) ✓                │ │
│     │ • ISO 27001 obligatoire (vs obligatoire) ✓        │ │
│     │ • SLA P1: <15min (vs <20min actuel) ⚠️ Plus strict│ │
│     └────────────────────────────────────────────────────┘ │
│     💡 Stratégie gagnante:                                 │
│        - Mise en avant ITIL v4 (différenciateur clé)      │
│        - Équipe 100% dédiée (exigence implicite)          │
│        - Prix agressif lots 1+2 combinés                  │
│     [Voir réponse gagnante] [Voir CCTP original]          │
│                                                             │
│ ❌ 2. Mairie Montreuil - Support IT (2022)    Score: 87%  │
│     Secteur: Collectivité ✓  |  800 users ⚠️  |  LOST ❌  │
│     Notre score: 16.5/20 (2ème/5)                         │
│     Gagnant: 17.8/20 (écart: -1.3 pts)                    │
│     ┌────────────────────────────────────────────────────┐ │
│     │ Critères clés:                                     │ │
│     │ • Technique: 30% (vs 40% actuel) ⚠️ Moins important│ │
│     │ • Financier: 70% (vs 60% actuel) ⚠️ Prix critique │ │
│     └────────────────────────────────────────────────────┘ │
│     ⚠️  Leçons apprises:                                   │
│        - Prix trop élevé (-5 pts financier)               │
│        - Manque références collectivités <1000 users      │
│        - Méthodologie trop complexe pour petit marché     │
│     [Voir réponse soumise] [Voir analyse post-mortem]     │
│                                                             │
│ ✅ 3. CD Seine-et-Marne - Infogérance (2023)  Score: 82%  │
│     [...]                                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📈 Analyse Comparative                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Taux succès sur tenders similaires: 60% (3/5) ✅          │
│                                                             │
│ Critères moyens tenders similaires:                        │
│ • Technique: 38% (actuel: 40%) → Légèrement + important   │
│ • Financier: 62% (actuel: 60%) → Standard                 │
│                                                             │
│ SLA typiques:                                              │
│ • P1 response: <12min médiane (actuel: <20min) ⚠️         │
│ • P1 resolution: 3h médiane (actuel: 4h) ✅               │
│                                                             │
│ Certifications demandées (fréquence):                      │
│ • ISO 27001: 100% (5/5) → CRITIQUE                        │
│ • ISO 9001: 60% (3/5) → Important                         │
│ • HDS: 20% (1/5) → Optionnel                              │
│                                                             │
│ 💡 Recommandations stratégiques:                           │
│ 1. Mettre en avant notre taux succès 60% sur AO similaires│
│ 2. Anticiper négociation SLA P1 (<20min peut être négocié)│
│ 3. Prix compétitif critique (≤650k€/an recommandé)        │
│ 4. Insister sur références EPT (différenciateur clé)      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Gain**: **2-3h** par tender (recherche manuelle + analyse compétitive)
**ROI**: **Très élevé** (réduit risque échec)

---

### Use Case #7: Apprentissage des Échecs ⭐⭐⭐⭐

**Problème**: On reproduit les mêmes erreurs sur des tenders similaires

**Solution RAG**:

```
1. Détection tender à risque:
   RAG identifie tenders perdus similaires (secteur + taille + services)

2. Analyse des raisons d'échec:
   - Extraction "lessons_learned" des tenders perdus
   - Identification patterns d'échec récurrents
   - Alertes proactives bid manager

3. Checklist personnalisée:
   Génération checklist basée sur échecs passés:
   ✓ Vérifier prix ≤ budget marché (échec Montreuil 2022: prix trop élevé)
   ✓ Minimum 3 références secteur identique (échec Lyon 2021)
   ✓ Équipe dédiée mentionnée (échec APHP 2023)
```

**Exemple Alerte**:

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️  ALERTE: Risques Identifiés (basés sur historique)      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 🔍 3 tenders similaires perdus identifiés:                 │
│                                                             │
│ 1. Mairie Montreuil (2022) - Perdu 2ème/5                 │
│    Raison: Prix 18% au-dessus gagnant                     │
│    ⚠️  RISQUE: Budget actuel semble serré (600k€)         │
│    💡 ACTION: Proposer 2 variantes (base + options)       │
│                                                             │
│ 2. Région PACA (2021) - Perdu 3ème/6                      │
│    Raison: Manque références collectivités >1000 users    │
│    ⚠️  RISQUE: Seulement 1 référence >1000 users en KB    │
│    💡 ACTION: Mettre en avant CD77 (2200 users)           │
│                                                             │
│ 3. APHP (2023) - Perdu 4ème/7                             │
│    Raison: Équipe non dédiée explicitement mentionnée     │
│    ⚠️  RISQUE: CCTP demande "équipe dédiée" (art. 3.2)    │
│    💡 ACTION: Insister section "Moyens humains" sur dédié │
│                                                             │
│ [Voir analyses détaillées] [Générer plan mitigation]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Gain**: **1-2h** + **Réduction risque échec 20-30%**
**ROI**: **Très élevé** (évite soumissions vouées à l'échec)

---

## 🔄 Workflow d'Archivage

### Processus Automatisé

```
1. Tender actif dans table `tenders` (système existant)
   ↓
2. Réponse soumise → Création `proposals`
   ↓
3. Résultat connu (gagné/perdu)
   ↓
4. Archivage automatique dans KB:

   a) Créer historical_tender:
      - Copier métadonnées tender
      - Extraire critères, exigences, SLA
      - Stocker résultat (won/lost + score)

   b) Lier avec past_proposal:
      - Si gagné: marquer "won = true"
      - Si perdu: marquer "won = false" + raisons échec

   c) Créer embeddings documents tender:
      - CCTP → chunks → embeddings
      - CCAP → chunks → embeddings
      - RC → chunks → embeddings

   d) Enrichir métadonnées:
      - Tags automatiques (secteur, services, technologies)
      - Extraction lessons_learned (formulaire post-mortem)
      - Analyse comparative vs gagnant (si infos disponibles)
```

### Trigger Automatique

```sql
-- Fonction archivage automatique
CREATE OR REPLACE FUNCTION archive_tender_to_kb()
RETURNS TRIGGER AS $$
BEGIN
    -- Si statut passe à 'completed' ou 'closed'
    IF NEW.status IN ('completed', 'closed') AND OLD.status NOT IN ('completed', 'closed') THEN
        -- Insertion dans historical_tenders
        INSERT INTO historical_tenders (
            title, organization, reference_number, deadline,
            sector, services, result, participated,
            -- ... autres champs
        )
        SELECT
            t.title, t.organization, t.reference_number, t.deadline,
            t.parsed_content->>'sector',
            t.parsed_content->'services',
            -- Déterminer result depuis proposal
            CASE
                WHEN EXISTS (SELECT 1 FROM proposals p WHERE p.tender_id = t.id AND p.status = 'won') THEN 'won'
                WHEN EXISTS (SELECT 1 FROM proposals p WHERE p.tender_id = t.id AND p.status = 'lost') THEN 'lost'
                ELSE 'not_submitted'
            END,
            true  -- participated
        FROM tenders t
        WHERE t.id = NEW.id;

        -- Trigger création embeddings asynchrone (Celery task)
        -- PERFORM pg_notify('archive_tender', NEW.id::text);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
CREATE TRIGGER trigger_archive_tender_to_kb
AFTER UPDATE ON tenders
FOR EACH ROW
EXECUTE FUNCTION archive_tender_to_kb();
```

---

## 📊 Statistiques & Analytics

### Vue: Taux Succès par Type Tender

```sql
CREATE VIEW v_success_rate_by_tender_type AS
SELECT
    sector,
    contract_type,
    COUNT(*) as total_tenders,
    SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) as won_count,
    ROUND(100.0 * SUM(CASE WHEN result = 'won' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    AVG(CASE WHEN result = 'won' THEN our_score END) as avg_score_won,
    AVG(CASE WHEN result = 'lost' THEN our_score END) as avg_score_lost,
    AVG(CASE WHEN result = 'won' THEN our_rank END) as avg_rank_won
FROM historical_tenders
WHERE participated = true
  AND result IN ('won', 'lost')
GROUP BY sector, contract_type
ORDER BY win_rate DESC;
```

### Vue: Évolution Critères dans le Temps

```sql
CREATE VIEW v_evaluation_criteria_evolution AS
SELECT
    DATE_TRUNC('year', deadline) as year,
    sector,
    AVG((evaluation_criteria->'technique'->>'weight')::float) as avg_tech_weight,
    AVG((evaluation_criteria->'financier'->>'weight')::float) as avg_financial_weight,
    AVG((evaluation_criteria->'rse'->>'weight')::float) as avg_rse_weight,
    COUNT(*) as tender_count
FROM historical_tenders
WHERE evaluation_criteria IS NOT NULL
GROUP BY DATE_TRUNC('year', deadline), sector
ORDER BY year DESC, sector;
```

### Requête: Top Raisons Échecs

```sql
SELECT
    sector,
    COUNT(*) as lost_count,
    -- Extraction patterns textuels des lessons_learned
    jsonb_agg(DISTINCT jsonb_build_object(
        'tender', title,
        'lesson', lessons_learned
    )) as common_failure_reasons
FROM historical_tenders
WHERE result = 'lost'
  AND lessons_learned IS NOT NULL
GROUP BY sector
ORDER BY lost_count DESC;
```

---

## 🎯 Métriques de Succès

### KPIs Nouveaux

| KPI | Objectif | Mesure |
|-----|----------|--------|
| **Taux archivage** | 100% | % tenders complétés archivés dans KB |
| **Complétude post-mortem** | >80% | % tenders avec lessons_learned remplis |
| **Utilisation comparaisons** | >70% | % nouveaux tenders avec analyse comparative consultée |
| **Réduction échecs répétés** | -30% | Réduction tenders perdus pour mêmes raisons |
| **Taux succès global** | +10% | Amélioration win rate après 6 mois |

---

## 🚀 Plan Implémentation

### Phase 1: Infrastructure (Semaine 1)
1. ✅ Créer table `historical_tenders`
2. ✅ Modifier table `past_proposals` (ajout colonne)
3. ✅ Créer vues analytics
4. ✅ Développer trigger archivage automatique

### Phase 2: Embeddings Tenders (Semaine 2)
1. ✅ Adapter RAG service pour embeddings tenders
2. ✅ Task Celery archivage avec embeddings
3. ✅ Tests sur 5-10 tenders historiques

### Phase 3: Use Cases (Semaine 3)
1. ✅ Use Case #6: Analyse comparative
2. ✅ Use Case #7: Apprentissage échecs
3. ✅ UI alertes et recommandations

### Phase 4: Analytics (Semaine 4)
1. ✅ Dashboard taux succès par secteur
2. ✅ Évolution critères dans le temps
3. ✅ Rapports post-mortem automatiques

---

## 📋 Checklist Migration Données Historiques

Pour migrer tenders existants dans KB:

```python
# Script migration backend/scripts/migrate_historical_tenders.py

async def migrate_existing_tenders():
    """Migrer tenders existants (status = completed/closed) vers KB"""

    # 1. Récupérer tenders complétés
    tenders = await db.execute(
        select(Tender).where(Tender.status.in_(['completed', 'closed']))
    )

    for tender in tenders:
        # 2. Créer historical_tender
        historical = HistoricalTender(
            title=tender.title,
            organization=tender.organization,
            reference_number=tender.reference_number,
            deadline=tender.deadline,
            # ... extraire métadonnées
        )

        # 3. Lier avec proposal si existe
        proposal = await db.execute(
            select(Proposal).where(Proposal.tender_id == tender.id)
        )
        if proposal:
            historical.our_proposal_id = proposal.id
            historical.result = 'won' if proposal.status == 'won' else 'lost'

        # 4. Créer embeddings documents
        for doc in tender.documents:
            await rag_service.ingest_document(
                document_id=doc.id,
                content=doc.extracted_text,
                document_type='historical_tender',
                metadata={'tender_id': historical.id}
            )

        await db.commit()
```

---

## 💡 Recommandations

### 1. Formulaire Post-Mortem Obligatoire

Après chaque tender (gagné ou perdu), formulaire structuré:

```
📝 Analyse Post-Mortem Tender: {title}

Résultat: [x] Gagné  [ ] Perdu  [ ] Abandonné

Notre score: __/20    Rang: __/__    Gagnant score: __/20

Pourquoi gagné/perdu? (3-5 lignes)
┌────────────────────────────────────────────────┐
│                                                │
│                                                │
└────────────────────────────────────────────────┘

Facteurs clés succès/échec:
☐ Prix (trop élevé/compétitif)
☐ Références (suffisantes/insuffisantes)
☐ Équipe (dédiée/mutualisée)
☐ Méthodologie (adaptée/trop complexe)
☐ Certifications (toutes présentes/manquantes)
☐ Délais (respectés/trop justes)
☐ Autre: ________________

Leçons pour prochains tenders similaires:
┌────────────────────────────────────────────────┐
│                                                │
└────────────────────────────────────────────────┘
```

### 2. Revue Trimestrielle Tenders Perdus

Analyser patterns:
- Tenders perdus par secteur
- Raisons récurrentes d'échec
- Actions correctives à mettre en place

### 3. Benchmark Concurrentiel

Stocker infos gagnants quand disponibles:
- Nom concurrent gagnant
- Prix gagnant (si publié)
- Points forts identifiés
- → Constituer base connaissance concurrence

---

**Prochaine étape**: Créer migration Alembic pour `historical_tenders`

**Dernière mise à jour**: 2 octobre 2025
**Version**: 1.0
