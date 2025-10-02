# 🗄️ RAG Service - Schéma de Données Knowledge Base

**Date**: 2 octobre 2025
**Version**: 1.0
**Objectif**: Définir le schéma complet de la Knowledge Base pour les 5 use cases RAG

---

## 📊 Vue d'Ensemble

La Knowledge Base (KB) stocke **tout le contenu réutilisable** pour aider les bid managers à rédiger leurs réponses. Elle est organisée en 5 types de documents distincts.

### Types de Documents KB

1. **`past_proposals`** - Réponses gagnantes passées
2. **`case_studies`** - Références clients avec résultats
3. **`certifications`** - Certificats et accréditations
4. **`documentation`** - Processus internes, méthodologies
5. **`templates`** - Sections pré-rédigées réutilisables

---

## 🗂️ Schéma de Données Complet

### Table 1: `kb_documents` (Table Principale)

**Rôle**: Registre central de tous les documents de la KB

```sql
CREATE TABLE kb_documents (
    -- Identité
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type VARCHAR(50) NOT NULL CHECK (document_type IN (
        'past_proposal',
        'case_study',
        'certification',
        'documentation',
        'template'
    )),
    title VARCHAR(500) NOT NULL,
    description TEXT,

    -- Contenu
    content TEXT NOT NULL,  -- Texte brut extrait
    content_format VARCHAR(20) DEFAULT 'text',  -- text, markdown, html
    word_count INT,

    -- Fichier source
    file_name VARCHAR(255),
    file_path VARCHAR(500),  -- S3/MinIO path
    file_size_bytes BIGINT,
    file_mime_type VARCHAR(100),
    file_hash VARCHAR(64),  -- SHA-256 for deduplication

    -- Métadonnées
    tags JSONB DEFAULT '[]',  -- ["ITIL", "Infogérance", "Collectivité"]
    metadata JSONB DEFAULT '{}',  -- Métadonnées spécifiques par type

    -- Statut
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'draft')),
    quality_score FLOAT CHECK (quality_score BETWEEN 0 AND 1),  -- 0-1 score qualité
    usage_count INT DEFAULT 0,  -- Nombre fois utilisé

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    created_by UUID,  -- User ID

    -- Indexes
    CONSTRAINT kb_documents_pkey PRIMARY KEY (id)
);

-- Indexes
CREATE INDEX idx_kb_documents_type ON kb_documents(document_type);
CREATE INDEX idx_kb_documents_status ON kb_documents(status);
CREATE INDEX idx_kb_documents_created_at ON kb_documents(created_at DESC);
CREATE INDEX idx_kb_documents_tags ON kb_documents USING GIN (tags);
CREATE INDEX idx_kb_documents_usage ON kb_documents(usage_count DESC);
CREATE INDEX idx_kb_documents_file_hash ON kb_documents(file_hash);

-- Trigger mise à jour updated_at
CREATE TRIGGER update_kb_documents_updated_at
BEFORE UPDATE ON kb_documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

---

### Table 2: `past_proposals` (Réponses Gagnantes)

**Rôle**: Stocke les mémoires techniques et réponses ayant remporté des marchés

```sql
CREATE TABLE past_proposals (
    -- Relation avec kb_documents
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,

    -- Informations Tender
    tender_title VARCHAR(500) NOT NULL,
    tender_organization VARCHAR(200),
    tender_reference VARCHAR(100),
    tender_year INT,
    tender_sector VARCHAR(100),  -- Collectivité, Santé, Éducation...

    -- Résultat
    won BOOLEAN DEFAULT true,  -- true si gagné
    score_obtained FLOAT,  -- Note obtenue (ex: 18.5/20)
    score_max FLOAT,  -- Note max possible (ex: 20)
    rank INT,  -- Classement (1 = premier)

    -- Contrat résultant
    contract_value DECIMAL(15,2),  -- Montant contrat (€)
    contract_duration_months INT,  -- Durée contrat (mois)
    contract_start_date DATE,
    contract_end_date DATE,

    -- Critères d'évaluation
    criteria_technical_weight FLOAT,  -- Poids technique (%)
    criteria_financial_weight FLOAT,  -- Poids financier (%)
    criteria_other_weight FLOAT,  -- Poids autres (RSE, etc.)

    -- Services proposés
    services JSONB DEFAULT '[]',  -- ["Infogérance", "Support N1", "Hébergement"]

    -- Équipe mobilisée
    team_size INT,  -- Nombre personnes dédiées
    team_composition JSONB,  -- {\"n1\": 6, \"n2\": 4, \"chef_projet\": 1}

    -- Contexte technique
    technologies JSONB DEFAULT '[]',  -- ["ServiceNow", "Zabbix", "VMware"]
    methodologies JSONB DEFAULT '[]',  -- ["Agile", "ITIL", "DevOps"]

    -- Raisons du succès
    success_factors TEXT,  -- Pourquoi a-t-on gagné?
    lessons_learned TEXT,  -- Leçons apprises

    -- Réutilisation
    reusable_sections JSONB,  -- {"presentation": "Section 1.2", "methodologie": "Section 3.1"}

    -- Métadonnées
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT past_proposals_pkey PRIMARY KEY (id),
    CONSTRAINT fk_past_proposals_kb_document FOREIGN KEY (kb_document_id)
        REFERENCES kb_documents(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_past_proposals_kb_document ON past_proposals(kb_document_id);
CREATE INDEX idx_past_proposals_won ON past_proposals(won);
CREATE INDEX idx_past_proposals_year ON past_proposals(tender_year DESC);
CREATE INDEX idx_past_proposals_sector ON past_proposals(tender_sector);
CREATE INDEX idx_past_proposals_services ON past_proposals USING GIN (services);
CREATE INDEX idx_past_proposals_score ON past_proposals(score_obtained DESC) WHERE won = true;
```

---

### Table 3: `case_studies` (Références Clients)

**Rôle**: Références clients détaillées avec résultats mesurables

```sql
CREATE TABLE case_studies (
    -- Relation avec kb_documents
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,

    -- Client
    client_name VARCHAR(200) NOT NULL,
    client_type VARCHAR(100),  -- EPT, Mairie, Département, Région, Hôpital, Université...
    client_sector VARCHAR(100),  -- Collectivité, Santé, Éducation, Industrie...
    client_location VARCHAR(200),  -- Région, département

    -- Taille organisation
    users_count INT,  -- Nombre utilisateurs
    sites_count INT,  -- Nombre sites/implantations
    annual_budget DECIMAL(15,2),  -- Budget annuel organisation (€)

    -- Contrat
    contract_type VARCHAR(50),  -- Infogérance, Support, Hébergement, TMA...
    contract_start_date DATE NOT NULL,
    contract_end_date DATE,
    contract_duration_months INT,
    contract_value_annual DECIMAL(15,2),  -- Montant annuel (€)
    contract_value_total DECIMAL(15,2),  -- Montant total (€)
    contract_renewed BOOLEAN DEFAULT false,  -- Reconduit?

    -- Services fournis
    services JSONB DEFAULT '[]',  -- ["Infogérance", "Support N1-N2", "Supervision"]
    service_levels JSONB,  -- {"availability": "99.7%", "mttr": "2h15"}

    -- Résultats / KPIs
    results_summary TEXT NOT NULL,  -- Résumé résultats obtenus
    kpis JSONB,  -- {"availability": 99.7, "satisfaction": 92, "incidents_resolved_n1": 67}
    achievements JSONB DEFAULT '[]',  -- ["Migration cloud", "Certification ISO"]

    -- Équipe mobilisée
    team_size INT,
    team_roles JSONB,  -- {"responsable_compte": 1, "techniciens_n1": 6, "ingenieurs_n2": 4}

    -- Technologies utilisées
    technologies JSONB DEFAULT '[]',  -- ["ServiceNow", "Zabbix", "VMware"]
    infrastructure JSONB,  -- {"servers": 50, "datacenter": "Tier 3"}

    -- Contact référent
    contact_name VARCHAR(200),
    contact_title VARCHAR(200),  -- DSI, Directeur IT...
    contact_email VARCHAR(200),
    contact_phone VARCHAR(50),
    contact_authorized BOOLEAN DEFAULT true,  -- Autorisation contact par prospect

    -- Documents associés
    documents JSONB DEFAULT '[]',
    -- [
    --   {"type": "attestation", "url": "s3://...", "title": "Attestation fin contrat"},
    --   {"type": "testimonial_video", "url": "https://...", "duration_sec": 180},
    --   {"type": "case_study_pdf", "url": "s3://...", "pages": 8}
    -- ]

    -- Témoignage client
    testimonial_text TEXT,  -- Citation client
    testimonial_author VARCHAR(200),
    testimonial_date DATE,
    testimonial_rating INT CHECK (testimonial_rating BETWEEN 1 AND 5),

    -- Métadonnées
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT case_studies_pkey PRIMARY KEY (id),
    CONSTRAINT fk_case_studies_kb_document FOREIGN KEY (kb_document_id)
        REFERENCES kb_documents(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_case_studies_kb_document ON case_studies(kb_document_id);
CREATE INDEX idx_case_studies_client_type ON case_studies(client_type);
CREATE INDEX idx_case_studies_client_sector ON case_studies(client_sector);
CREATE INDEX idx_case_studies_users_count ON case_studies(users_count);
CREATE INDEX idx_case_studies_contract_type ON case_studies(contract_type);
CREATE INDEX idx_case_studies_services ON case_studies USING GIN (services);
CREATE INDEX idx_case_studies_contact_auth ON case_studies(contact_authorized) WHERE contact_authorized = true;
CREATE INDEX idx_case_studies_active ON case_studies(contract_end_date DESC NULLS FIRST);
```

---

### Table 4: `certifications` (Certificats & Accréditations)

**Rôle**: Stocke toutes les certifications de l'entreprise et des collaborateurs

```sql
CREATE TABLE certifications (
    -- Relation avec kb_documents
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_document_id UUID REFERENCES kb_documents(id) ON DELETE CASCADE,  -- Optionnel (certificats individuels n'ont pas forcément de PDF)

    -- Type
    certification_type VARCHAR(100) NOT NULL,
    -- ISO27001, ISO9001, HDS, Qualiopi, CISSP, ITIL, PSM, PMP...
    certification_category VARCHAR(50) CHECK (certification_category IN (
        'company',      -- Certification entreprise
        'individual',   -- Certification individuelle
        'infrastructure' -- Certification infra (datacenter Tier 3...)
    )),

    -- Détails certification
    certification_name VARCHAR(200) NOT NULL,
    certificate_number VARCHAR(100),
    issuing_body VARCHAR(200) NOT NULL,  -- AFNOR, Scrum.org, PMI, Uptime Institute...

    -- Dates
    issue_date DATE NOT NULL,
    expiry_date DATE,  -- NULL si pas d'expiration
    is_valid BOOLEAN GENERATED ALWAYS AS (
        expiry_date IS NULL OR expiry_date >= CURRENT_DATE
    ) STORED,
    days_until_expiry INT GENERATED ALWAYS AS (
        CASE
            WHEN expiry_date IS NULL THEN NULL
            ELSE expiry_date - CURRENT_DATE
        END
    ) STORED,

    -- Périmètre
    scope TEXT,  -- Périmètre de la certification
    coverage JSONB,  -- {"services": ["Infogérance", "Hébergement"], "locations": ["Paris", "Lyon"]}

    -- Norme/Standard
    standard_version VARCHAR(50),  -- "ISO/IEC 27001:2013", "ITIL v4", "Scrum Guide 2020"
    standard_url VARCHAR(500),  -- URL documentation standard

    -- Document certificat
    certificate_pdf_url VARCHAR(500),  -- S3 path vers PDF certificat
    certificate_pdf_size_bytes BIGINT,

    -- Pour certifications individuelles
    holder_name VARCHAR(200),  -- Nom personne certifiée
    holder_role VARCHAR(100),  -- Poste dans l'entreprise
    holder_employee_id UUID,  -- Lien vers table employees (future)

    -- Template description
    description_template TEXT,
    -- Texte pré-rédigé réutilisable dans réponses
    -- Ex: "Notre organisation est certifiée ISO 27001:2013 depuis 2019..."

    -- Audits
    last_audit_date DATE,
    last_audit_result VARCHAR(50),  -- "Aucune non-conformité", "1 NC mineure"...
    next_audit_date DATE,

    -- Métadonnées
    notes TEXT,  -- Notes internes
    auto_renew BOOLEAN DEFAULT false,  -- Renouvellement automatique?
    cost_annual DECIMAL(10,2),  -- Coût annuel certification

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT certifications_pkey PRIMARY KEY (id),
    CONSTRAINT fk_certifications_kb_document FOREIGN KEY (kb_document_id)
        REFERENCES kb_documents(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_certifications_kb_document ON certifications(kb_document_id);
CREATE INDEX idx_certifications_type ON certifications(certification_type);
CREATE INDEX idx_certifications_category ON certifications(certification_category);
CREATE INDEX idx_certifications_valid ON certifications(is_valid) WHERE is_valid = true;
CREATE INDEX idx_certifications_expiry ON certifications(expiry_date) WHERE expiry_date IS NOT NULL;
CREATE INDEX idx_certifications_expiring_soon ON certifications(days_until_expiry)
    WHERE days_until_expiry IS NOT NULL AND days_until_expiry <= 180;
```

---

### Table 5: `documentation` (Docs Internes)

**Rôle**: Documentation interne (processus, méthodologies, fiches techniques)

```sql
CREATE TABLE documentation (
    -- Relation avec kb_documents
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,

    -- Classification
    doc_category VARCHAR(50) NOT NULL CHECK (doc_category IN (
        'process',      -- Processus (ITIL, ITSM...)
        'methodology',  -- Méthodologie (Agile, DevOps...)
        'technical',    -- Fiche technique (infrastructure, réseau...)
        'procedure',    -- Procédure opérationnelle
        'policy',       -- Politique (sécurité, RGPD...)
        'guide',        -- Guide utilisateur/administrateur
        'other'
    )),
    doc_subcategory VARCHAR(100),  -- "ITIL Process", "Agile Framework", "Network Architecture"...

    -- Contenu structuré
    version VARCHAR(20),  -- v1.0, v2.1...
    language VARCHAR(10) DEFAULT 'fr',  -- fr, en

    -- Référentiel
    framework VARCHAR(50),  -- ITIL, COBIT, PRINCE2, ISO, ANSSI...
    framework_version VARCHAR(50),  -- "ITIL v4", "ISO 27001:2013"

    -- Applicabilité
    applicable_to JSONB DEFAULT '[]',
    -- ["Infogérance", "Support", "Hébergement"]
    target_audience JSONB DEFAULT '[]',
    -- ["Bid Managers", "Technical Team", "Management"]

    -- Processus ITIL spécifiques
    itil_process VARCHAR(100),
    -- "Incident Management", "Change Management", "Problem Management"...
    itil_phase VARCHAR(50),
    -- "Service Strategy", "Service Design", "Service Transition", "Service Operation", "Continual Improvement"

    -- Méthodologie
    methodology_type VARCHAR(50),
    -- "Agile", "Scrum", "Kanban", "SAFe", "DevOps", "PRINCE2"...

    -- Approbation
    approved_by VARCHAR(200),  -- Nom approbateur
    approved_date DATE,
    review_frequency_months INT,  -- Fréquence révision (mois)
    next_review_date DATE,

    -- Liens
    related_docs JSONB DEFAULT '[]',
    -- [{"doc_id": "uuid", "title": "...", "relation": "prerequisite"}]
    external_references JSONB DEFAULT '[]',
    -- [{"title": "ITIL 4 Foundation", "url": "https://..."}]

    -- Métadonnées
    author VARCHAR(200),
    confidentiality VARCHAR(20) DEFAULT 'internal' CHECK (confidentiality IN (
        'public', 'internal', 'confidential', 'secret'
    )),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT documentation_pkey PRIMARY KEY (id),
    CONSTRAINT fk_documentation_kb_document FOREIGN KEY (kb_document_id)
        REFERENCES kb_documents(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_documentation_kb_document ON documentation(kb_document_id);
CREATE INDEX idx_documentation_category ON documentation(doc_category);
CREATE INDEX idx_documentation_framework ON documentation(framework);
CREATE INDEX idx_documentation_itil_process ON documentation(itil_process);
CREATE INDEX idx_documentation_methodology ON documentation(methodology_type);
CREATE INDEX idx_documentation_version ON documentation(version);
CREATE INDEX idx_documentation_review_date ON documentation(next_review_date);
```

---

### Table 6: `templates` (Templates Réutilisables)

**Rôle**: Sections pré-rédigées réutilisables (présentation entreprise, méthodologie...)

```sql
CREATE TABLE templates (
    -- Relation avec kb_documents
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,

    -- Classification
    template_name VARCHAR(200) NOT NULL,
    template_type VARCHAR(50) NOT NULL CHECK (template_type IN (
        'presentation',   -- Présentation entreprise
        'team',          -- Composition équipe
        'infrastructure', -- Infrastructure technique
        'methodology',   -- Méthodologie projet
        'pricing',       -- Grille tarifaire
        'commitment',    -- Engagements (SLA, pénalités...)
        'rse',           -- RSE / Environnement
        'reference',     -- Format référence client
        'other'
    )),

    -- Version
    version VARCHAR(20) NOT NULL,  -- v2024, v2025, v1.0...
    is_latest BOOLEAN DEFAULT true,

    -- Contenu template
    content_format VARCHAR(20) DEFAULT 'markdown' CHECK (content_format IN (
        'markdown', 'html', 'text', 'docx'
    )),

    -- Placeholders
    placeholders JSONB DEFAULT '[]',
    -- [
    --   {
    --     "name": "responsable_compte",
    --     "type": "text",
    --     "label": "Nom responsable compte",
    --     "required": true,
    --     "default": null,
    --     "validation": "^[A-Za-z\\s-]+$"
    --   },
    --   {
    --     "name": "agence",
    --     "type": "select",
    --     "label": "Agence référente",
    --     "required": false,
    --     "options": ["Paris", "Lyon", "Marseille"],
    --     "default": "Paris"
    --   }
    -- ]

    -- Applicabilité
    applicable_sectors JSONB DEFAULT '[]',
    -- ["Collectivité", "Santé", "Éducation"] - null = tous
    applicable_services JSONB DEFAULT '[]',
    -- ["Infogérance", "Support"] - null = tous
    min_contract_value DECIMAL(15,2),  -- Seuil minimum utilisation
    max_contract_value DECIMAL(15,2),  -- Seuil maximum

    -- Sections CCTP typiques
    typical_cctp_sections JSONB DEFAULT '[]',
    -- ["2.1 - Présentation candidat", "2.2 - Moyens humains"]

    -- Métriques utilisation
    usage_count INT DEFAULT 0,
    avg_adaptation_time_min INT,  -- Temps moyen adaptation (minutes)
    satisfaction_score FLOAT CHECK (satisfaction_score BETWEEN 0 AND 5),

    -- Personnalisation
    allow_customization BOOLEAN DEFAULT true,
    customization_notes TEXT,  -- Instructions personnalisation

    -- Validation
    validated_by VARCHAR(200),
    validated_date DATE,

    -- Expiration
    expires_at DATE,  -- Date expiration template (ex: chiffres 2024 périmés en 2025)

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,

    CONSTRAINT templates_pkey PRIMARY KEY (id),
    CONSTRAINT fk_templates_kb_document FOREIGN KEY (kb_document_id)
        REFERENCES kb_documents(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_templates_kb_document ON templates(kb_document_id);
CREATE INDEX idx_templates_type ON templates(template_type);
CREATE INDEX idx_templates_latest ON templates(is_latest) WHERE is_latest = true;
CREATE INDEX idx_templates_version ON templates(version);
CREATE INDEX idx_templates_usage ON templates(usage_count DESC);
CREATE INDEX idx_templates_expires ON templates(expires_at) WHERE expires_at IS NOT NULL;
```

---

## 🔗 Tables Complémentaires

### Table 7: `kb_tags` (Tags Standardisés)

**Rôle**: Taxonomie standardisée pour taguer les documents

```sql
CREATE TABLE kb_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag_name VARCHAR(100) NOT NULL UNIQUE,
    tag_category VARCHAR(50),  -- Secteur, Service, Technologie, Méthodologie...
    tag_description TEXT,
    usage_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_kb_tags_category ON kb_tags(tag_category);
CREATE INDEX idx_kb_tags_usage ON kb_tags(usage_count DESC);
```

---

### Table 8: `kb_relationships` (Relations entre Documents)

**Rôle**: Liens entre documents KB (prérequis, similaire, mis à jour par...)

```sql
CREATE TABLE kb_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    target_doc_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN (
        'prerequisite',   -- Target est prérequis de Source
        'related',        -- Documents liés
        'supersedes',     -- Source remplace Target
        'references',     -- Source référence Target
        'derived_from'    -- Source dérivé de Target
    )),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT kb_relationships_pkey PRIMARY KEY (id),
    CONSTRAINT kb_relationships_unique UNIQUE (source_doc_id, target_doc_id, relationship_type)
);

CREATE INDEX idx_kb_relationships_source ON kb_relationships(source_doc_id);
CREATE INDEX idx_kb_relationships_target ON kb_relationships(target_doc_id);
CREATE INDEX idx_kb_relationships_type ON kb_relationships(relationship_type);
```

---

### Table 9: `kb_usage_logs` (Logs Utilisation)

**Rôle**: Tracker utilisation documents pour analytics et amélioration

```sql
CREATE TABLE kb_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kb_document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,

    -- Contexte utilisation
    used_in_tender_id UUID REFERENCES tenders(id) ON DELETE SET NULL,
    used_in_proposal_id UUID REFERENCES proposals(id) ON DELETE SET NULL,
    used_by_user_id UUID,  -- Future: REFERENCES users(id)

    -- Type utilisation
    usage_type VARCHAR(50) CHECK (usage_type IN (
        'search',         -- Trouvé via recherche
        'suggestion',     -- Suggéré automatiquement
        'inserted',       -- Inséré dans réponse
        'viewed',         -- Simplement consulté
        'downloaded'      -- Téléchargé
    )),

    -- Métadonnées
    search_query TEXT,  -- Requête recherche ayant mené au document
    relevance_score FLOAT,  -- Score pertinence si suggestion
    inserted_section VARCHAR(200),  -- Quelle section de la réponse

    -- Feedback
    user_rating INT CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback TEXT,

    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT kb_usage_logs_pkey PRIMARY KEY (id)
);

CREATE INDEX idx_kb_usage_logs_document ON kb_usage_logs(kb_document_id);
CREATE INDEX idx_kb_usage_logs_tender ON kb_usage_logs(used_in_tender_id);
CREATE INDEX idx_kb_usage_logs_type ON kb_usage_logs(usage_type);
CREATE INDEX idx_kb_usage_logs_created ON kb_usage_logs(created_at DESC);
```

---

## 📊 Statistiques et Vues

### Vue 1: `v_kb_stats` (Statistiques KB)

```sql
CREATE VIEW v_kb_stats AS
SELECT
    document_type,
    status,
    COUNT(*) as document_count,
    SUM(word_count) as total_words,
    AVG(quality_score) as avg_quality,
    SUM(usage_count) as total_usage,
    MIN(created_at) as oldest_doc,
    MAX(created_at) as newest_doc
FROM kb_documents
GROUP BY document_type, status;
```

---

### Vue 2: `v_certifications_expiring` (Certifications Expirant Bientôt)

```sql
CREATE VIEW v_certifications_expiring AS
SELECT
    c.id,
    c.certification_name,
    c.certification_type,
    c.certificate_number,
    c.expiry_date,
    c.days_until_expiry,
    CASE
        WHEN c.days_until_expiry <= 30 THEN 'critical'
        WHEN c.days_until_expiry <= 90 THEN 'warning'
        WHEN c.days_until_expiry <= 180 THEN 'info'
    END as alert_level
FROM certifications c
WHERE c.is_valid = true
  AND c.expiry_date IS NOT NULL
  AND c.days_until_expiry <= 180
ORDER BY c.days_until_expiry ASC;
```

---

### Vue 3: `v_top_documents` (Documents Les Plus Utilisés)

```sql
CREATE VIEW v_top_documents AS
SELECT
    d.id,
    d.document_type,
    d.title,
    d.usage_count,
    d.quality_score,
    d.last_used_at,
    COUNT(l.id) as log_entries_count,
    AVG(l.user_rating) as avg_user_rating
FROM kb_documents d
LEFT JOIN kb_usage_logs l ON d.id = l.kb_document_id
WHERE d.status = 'active'
GROUP BY d.id, d.document_type, d.title, d.usage_count, d.quality_score, d.last_used_at
ORDER BY d.usage_count DESC, avg_user_rating DESC
LIMIT 50;
```

---

## 🔧 Fonctions Utilitaires

### Fonction 1: Mise à Jour `updated_at`

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

### Fonction 2: Incrémenter `usage_count`

```sql
CREATE OR REPLACE FUNCTION increment_kb_usage(doc_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE kb_documents
    SET
        usage_count = usage_count + 1,
        last_used_at = NOW()
    WHERE id = doc_id;
END;
$$ LANGUAGE plpgsql;
```

---

### Fonction 3: Recherche Full-Text

```sql
-- Ajouter colonne tsvector pour recherche plein texte
ALTER TABLE kb_documents ADD COLUMN content_tsv tsvector;

-- Fonction mise à jour tsvector
CREATE OR REPLACE FUNCTION kb_documents_content_tsv_trigger()
RETURNS TRIGGER AS $$
BEGIN
    NEW.content_tsv :=
        setweight(to_tsvector('french', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('french', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('french', COALESCE(NEW.content, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger
CREATE TRIGGER kb_documents_content_tsv_update
BEFORE INSERT OR UPDATE ON kb_documents
FOR EACH ROW
EXECUTE FUNCTION kb_documents_content_tsv_trigger();

-- Index GIN
CREATE INDEX idx_kb_documents_content_tsv ON kb_documents USING GIN (content_tsv);
```

---

## 📈 Métriques et KPIs

### Requêtes Analytiques

**1. Documents par type et statut**:
```sql
SELECT document_type, status, COUNT(*)
FROM kb_documents
GROUP BY document_type, status;
```

**2. Taux utilisation par type**:
```sql
SELECT
    document_type,
    COUNT(*) as total_docs,
    SUM(CASE WHEN usage_count > 0 THEN 1 ELSE 0 END) as used_docs,
    ROUND(100.0 * SUM(CASE WHEN usage_count > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) as usage_rate
FROM kb_documents
WHERE status = 'active'
GROUP BY document_type;
```

**3. Certifications expirant sous 6 mois**:
```sql
SELECT * FROM v_certifications_expiring;
```

**4. Top 10 documents les plus consultés (30 derniers jours)**:
```sql
SELECT
    d.title,
    d.document_type,
    COUNT(l.id) as views_last_30d,
    AVG(l.user_rating) as avg_rating
FROM kb_documents d
JOIN kb_usage_logs l ON d.id = l.kb_document_id
WHERE l.created_at >= NOW() - INTERVAL '30 days'
GROUP BY d.id, d.title, d.document_type
ORDER BY views_last_30d DESC
LIMIT 10;
```

---

## 🚀 Migration et Initialisation

### Script Migration Alembic

```python
\"\"\"Add Knowledge Base tables

Revision ID: kb_schema_v1
Revises: previous_revision
Create Date: 2025-10-02

\"\"\"
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'kb_schema_v1'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade():
    # Table kb_documents
    op.create_table('kb_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('document_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        # ... (voir schéma complet ci-dessus)
    )

    # Tables past_proposals, case_studies, certifications, documentation, templates
    # ... (voir schéma complet ci-dessus)

    # Vues
    op.execute(\"\"\"
        CREATE VIEW v_kb_stats AS ...
    \"\"\")

def downgrade():
    op.drop_view('v_kb_stats')
    op.drop_table('kb_usage_logs')
    op.drop_table('kb_relationships')
    op.drop_table('kb_tags')
    op.drop_table('templates')
    op.drop_table('documentation')
    op.drop_table('certifications')
    op.drop_table('case_studies')
    op.drop_table('past_proposals')
    op.drop_table('kb_documents')
```

---

## 📊 Récapitulatif

### Tables Créées (9 tables)

1. ✅ `kb_documents` - Table principale (registre)
2. ✅ `past_proposals` - Réponses gagnantes
3. ✅ `case_studies` - Références clients
4. ✅ `certifications` - Certificats
5. ✅ `documentation` - Docs internes
6. ✅ `templates` - Templates réutilisables
7. ✅ `kb_tags` - Tags standardisés
8. ✅ `kb_relationships` - Relations documents
9. ✅ `kb_usage_logs` - Analytics utilisation

### Vues Créées (3 vues)

1. ✅ `v_kb_stats` - Statistiques globales
2. ✅ `v_certifications_expiring` - Alertes expiration
3. ✅ `v_top_documents` - Documents populaires

### Fonctions Créées (3 fonctions)

1. ✅ `update_updated_at_column()` - Trigger updated_at
2. ✅ `increment_kb_usage()` - Incrémenter usage
3. ✅ `kb_documents_content_tsv_trigger()` - Full-text search

---

**Prochaine étape**: Création migration Alembic et implémentation modèles SQLAlchemy

**Dernière mise à jour**: 2 octobre 2025
**Version**: 1.0
