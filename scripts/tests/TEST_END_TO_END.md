# Procédure de Test End-to-End (E2E)

## 🎯 Objectif

Valider le pipeline complet d'analyse de tenders, de l'upload de documents PDF jusqu'à l'analyse LLM avec Claude, en passant par l'extraction, la structuration hiérarchique et la détection de sections clés.

---

## 📋 Prérequis

### Infrastructure Docker

Vérifier que tous les conteneurs sont actifs :

```bash
docker-compose ps
```

Conteneurs requis :

- ✅ `scorpius-postgres` (base de données)
- ✅ `scorpius-redis` (cache)
- ✅ `scorpius-rabbitmq` (message queue)
- ✅ `scorpius-celery-worker` (traitement async)
- ✅ `scorpius-minio` (stockage S3)

### Variables d'Environnement

Vérifier la présence de la clé API Anthropic :

```bash
docker exec scorpius-celery-worker python3 -c "from app.core.config import settings; print('API Key:', settings.anthropic_api_key[:20] + '...')"
```

### Documents de Test

Les PDFs VSGP-AO doivent être disponibles :

- `Examples/VSGP-AO/CCTP.pdf` (2.3 MB)
- `Examples/VSGP-AO/CCAP.pdf` (486 KB)
- `Examples/VSGP-AO/RC.pdf` (256 KB)

---

## 🧪 Procédure de Test Complète

### Étape 0 : Préparation - Réinitialiser la Base de Données

**Objectif** : Partir d'une base vide pour un test reproductible.

```bash
# Se connecter à PostgreSQL
docker exec scorpius-postgres psql -U scorpius -d scorpius_db

# Vider toutes les tables
TRUNCATE TABLE document_sections CASCADE;
TRUNCATE TABLE tender_documents CASCADE;
TRUNCATE TABLE tenders CASCADE;

# Vérifier que tout est vide
SELECT
    'tenders' as table_name, COUNT(*) as count FROM tenders
UNION ALL
SELECT 'tender_documents', COUNT(*) FROM tender_documents
UNION ALL
SELECT 'document_sections', COUNT(*) FROM document_sections;

# Sortir
\q
```

**Résultat attendu** :

```
 table_name        | count
-------------------+-------
 tenders           |     0
 tender_documents  |     0
 document_sections |     0
```

---

### Étape 1 : Copier les PDFs dans le Conteneur

**Objectif** : Rendre les PDFs accessibles depuis le conteneur Celery.

```bash
# Créer le répertoire
docker exec scorpius-celery-worker mkdir -p /app/real_pdfs

# Copier les 3 PDFs
docker cp Examples/dce-v1/CCTP.pdf scorpius-celery-worker:/app/real_pdfs/CCTP.pdf
docker cp Examples/dce-v1/CCAP.pdf scorpius-celery-worker:/app/real_pdfs/CCAP.pdf
docker cp Examples/dce-v1/RC.pdf scorpius-celery-worker:/app/real_pdfs/RC.pdf

# Vérifier la copie
docker exec scorpius-celery-worker ls -lh /app/real_pdfs/
```

**Résultat attendu** :

```
-rw-r--r-- 1 root root 2.3M Oct  2 09:00 CCTP.pdf
-rw-r--r-- 1 root root 486K Oct  2 09:00 CCAP.pdf
-rw-r--r-- 1 root root 256K Oct  2 09:00 RC.pdf
```

---

### Étape 2 : Créer le Tender et Uploader les Documents

**Objectif** : Créer l'entité tender et ses 3 documents associés.

```bash
# Exécuter le script de test E2E
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_fresh_e2e.py
```

**OU créer manuellement** :

```python
# Script Python pour création manuelle
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from app.core.config import settings
import uuid

engine = create_engine(settings.database_url_sync)

# 1. Créer le tender
tender_id = str(uuid.uuid4())
with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO tenders (id, title, organization, reference_number, status, source)
        VALUES (
            :id::UUID,
            'VSGP - Accord-cadre infogérance infrastructure et assistance utilisateur',
            'Établissement Public Territorial Vallée Sud Grand Paris',
            '25TIC06',
            'new',
            'manual_test'
        )
    """), {"id": tender_id})
    conn.commit()

print(f"✅ Tender créé : {tender_id}")

# 2. Uploader les documents
from app.services.storage_service import storage_service
import asyncio

async def upload_docs():
    files = ['CCTP.pdf', 'CCAP.pdf', 'RC.pdf']
    for filename in files:
        with open(f'/app/real_pdfs/{filename}', 'rb') as f:
            content = f.read()

        doc_id = await storage_service.store_document(
            tender_id=tender_id,
            filename=filename,
            file_content=content,
            content_type='application/pdf'
        )
        print(f"✅ Document uploadé : {filename} ({doc_id})")

asyncio.run(upload_docs())
```

**Résultats attendus** :

- ✅ 1 tender créé dans la table `tenders`
- ✅ 3 documents créés dans `tender_documents` (status: `pending`)
- ✅ 3 fichiers stockés dans MinIO (bucket `tenders/`)

---

### Étape 3 : Traiter les Documents avec Pipeline Optimisé

**Objectif** : Extraire le contenu, détecter la structure, identifier les sections clés.

```bash
# Traiter les 3 documents
docker exec scorpius-celery-worker python3 << 'EOF'
import sys
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.tasks.tender_tasks import process_tender_document

engine = create_engine(settings.database_url_sync)

# Récupérer les IDs des documents
with engine.connect() as conn:
    docs = conn.execute(text("""
        SELECT id, filename
        FROM tender_documents
        WHERE extraction_status = 'pending'
        ORDER BY filename
    """)).fetchall()

# Traiter chaque document
for doc_id, filename in docs:
    print(f"\n{'='*80}")
    print(f"🔄 Traitement : {filename}")
    print(f"{'='*80}")

    result = process_tender_document(str(doc_id))

    print(f"✅ Status: {result['status']}")
    print(f"📊 Text length: {result.get('text_length', 0):,} chars")
    print(f"📄 Pages: {result.get('page_count', 0)}")

print("\n" + "="*80)
print("✅ TRAITEMENT TERMINÉ")
print("="*80)
EOF
```

**Résultats attendus par document** :

| Document | Pages | Text Length | Sections | TOC | Key Sections |
|----------|-------|-------------|----------|-----|--------------|
| CCTP.pdf | 69 | ~146,000 | 202 | 56 | 44 |
| CCAP.pdf | 38 | ~97,000 | 128 | 47 | 49 |
| RC.pdf | 12 | ~27,000 | 47 | 22 | 13 |
| **TOTAL** | **119** | **~270,000** | **377** | **135** | **106** |

---

### Étape 4 : Vérifier la Qualité de l'Extraction

**Objectif** : S'assurer que la structure hiérarchique et les sections clés sont bien détectées.

```bash
docker exec scorpius-postgres psql -U scorpius -d scorpius_db << 'EOF'
-- Statistiques globales
SELECT
    COUNT(*) FILTER (WHERE is_toc = true) as toc_sections,
    COUNT(*) FILTER (WHERE is_key_section = true) as key_sections,
    COUNT(*) FILTER (WHERE content_length > 0) as sections_with_content,
    COUNT(*) FILTER (WHERE parent_id IS NOT NULL) as sections_with_parent,
    COUNT(*) as total_sections
FROM document_sections;

-- Vérifier les processus ITIL (section 4.1.5)
SELECT
    section_number,
    title,
    is_key_section,
    content_length
FROM document_sections
WHERE section_number LIKE '4.1.5%'
  AND is_key_section = true
ORDER BY section_number;

-- Vérifier hiérarchie parent-enfant
SELECT
    child.section_number as child,
    child.title as child_title,
    parent.section_number as parent,
    parent.title as parent_title
FROM document_sections child
JOIN document_sections parent ON child.parent_id = parent.id
WHERE child.section_number LIKE '4.1.5.%'
ORDER BY child.section_number
LIMIT 10;
EOF
```

**Résultats attendus** :

#### Statistiques Globales

```
 toc_sections | key_sections | sections_with_content | sections_with_parent | total_sections
--------------+--------------+-----------------------+----------------------+----------------
          135 |          106 |                   220 |                  295 |            377
```

#### Processus ITIL (4.1.5.x)

**Tous les 18 processus doivent être `is_key_section = true`** :

- 4.1.5 - Processus à mettre en œuvre
- 4.1.5.1 - Gestion des sollicitations
- 4.1.5.2 - Gestion des évènements
- 4.1.5.3 - Gestion des Incidents
- 4.1.5.4 - Gestion des escalades et des crises
- 4.1.5.5 - Gestion des problèmes
- 4.1.5.6 - Gestion des demandes de Services
- 4.1.5.7 - Gestion des Changements
- 4.1.5.8 - Gestion des niveaux de Service
- 4.1.5.9 - Gestion des configurations
- 4.1.5.10 - Gestion des mises en production
- 4.1.5.11 - Gestion de la capacité
- 4.1.5.12 - Gestion de la disponibilité / performance
- 4.1.5.13 - Gestion de la continuité d'activité
- 4.1.5.14 - Gestion des Opérations
- 4.1.5.15 - Gestion des projets
- 4.1.5.16 - Gestion des contrats (Titulaire)
- 4.1.5.17 - Gestion des contrats (VSGP)

---

### Étape 5 : Générer la Structure Hiérarchique

**Objectif** : Vérifier l'optimisation de structure pour le LLM.

```bash
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_hierarchical_analysis.py
```

**Résultats attendus** :

```
=== STRUCTURE HIÉRARCHIQUE ===
Caractères : 97,967
Tokens estimés : ~24,491

=== COMPARAISON FLAT vs HIÉRARCHIQUE ===
Flat (avant):        123,691 chars   30,922 tokens   $0.0928
Hiérarchique:         97,967 chars   24,491 tokens   $0.0735

RÉDUCTION:            25,724 (-21%)   6,431 (-21%)   $0.0193 (-21%)

✅ Économie par analyse : $0.0193
✅ Économie sur 100 tenders : $1.93
```

**Vérifications** :

- ✅ Réduction tokens : 15-25%
- ✅ Sections clés en entier
- ✅ Sections longues résumées (200 chars)
- ✅ TOC exclues
- ✅ Hiérarchie préservée

---

### Étape 6 : Exécuter l'Analyse LLM avec Claude

**Objectif** : Générer l'analyse complète du tender avec Claude API.

```bash
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_llm_analysis.py
```

**Résultats attendus** :

```
🤖 ANALYSE LLM AVEC CLAUDE API - STRUCTURE HIÉRARCHIQUE

✅ Clé API Anthropic configurée : sk-ant-api03-WSHePoK...
✅ 377 sections chargées
✅ Tender : VSGP - Accord-cadre d'infogérance...

🤖 Appel de Claude API pour analyse structurée...
✅ Claude API response: 32,636 input, 1,607 output tokens
💰 Cost estimate: $0.1220

📋 RÉSULTATS DE L'ANALYSE

📌 RÉSUMÉ :
Accord-cadre d'infogérance d'infrastructure et d'assistance utilisateur
de premier niveau pour l'EPT Vallée Sud Grand Paris, couvrant 1200
utilisateurs sur 40 sites...

🎯 EXIGENCES PRINCIPALES :
  1. Infogérance complète du SI (serveurs, réseau, sécurité, supervision)
  2. Assistance utilisateur niveau 1 avec centre de contact unique
  3. Respect des niveaux de service avec pénalités (95% appels <20s)
  4. Fourniture et maintenance des outils (ITSM, supervision, portail)
  5. Mise en place de processus ITIL et respect recommandations ANSSI
  ...

📅 DÉLAIS :
  • questions : 2025-04-07
  • remise_offre : 2025-04-15

⚠️  RISQUES IDENTIFIÉS :
  1. Pénalités sur niveaux de service (P1: 50-150€, P2: 100-300€...)
  2. Phase de vérification d'aptitude de 3 mois obligatoire
  ...

📄 DOCUMENTS OBLIGATOIRES :
  • Formulaire DC1 (lettre de candidature)
  • Formulaire DC2 (déclaration candidat)
  ...

💡 RECOMMANDATIONS :
  1. Prévoir équipe expérimentée en infogérance collectivités
  2. Anticiper phase de transition critique de 3 mois
  ...
```

**Vérifications critiques** :

#### ✅ Processus ITIL mentionnés

```bash
# Vérifier que les processus ITIL sont dans l'analyse
cat /app/analysis_result.json | grep -i "ITIL\|processus"
```

Doit contenir :

- ✅ "Mise en place de processus ITIL"
- ✅ "Compétences ITIL"
- ✅ "respect processus ITIL"

#### ✅ Informations CCAP capturées

```bash
# Vérifier les pénalités
cat /app/analysis_result.json | grep -i "pénalités\|penalties"
```

Doit contenir :

- ✅ Pénalités niveaux de service (P1, P2, P3)
- ✅ Modalités de paiement
- ✅ Évaluation (Prix 60%, Technique 40%)

---

### Étape 7 : Vérifications Finales

#### 7.1 Vérifier le Stockage MinIO

```bash
docker exec scorpius-minio mc ls minio/tenders/
```

**Résultat attendu** :

```
[2025-10-02 09:00:00 UTC]     0B <tender_id>/
```

```bash
# Lister les fichiers du tender
docker exec scorpius-minio mc ls minio/tenders/<tender_id>/
```

**Résultat attendu** :

```
[2025-10-02 09:00:00 UTC]  2.3MB CCTP.pdf
[2025-10-02 09:00:00 UTC]  486KB CCAP.pdf
[2025-10-02 09:00:00 UTC]  256KB RC.pdf
```

#### 7.2 Vérifier l'Intégrité des Données

```bash
docker exec scorpius-postgres psql -U scorpius -d scorpius_db << 'EOF'
-- Vérifier cohérence
SELECT
    t.reference_number as tender,
    COUNT(DISTINCT td.id) as documents,
    COUNT(ds.id) as total_sections,
    COUNT(DISTINCT ds.document_id) as docs_with_sections
FROM tenders t
LEFT JOIN tender_documents td ON t.id = td.tender_id
LEFT JOIN document_sections ds ON td.id = ds.document_id
WHERE t.reference_number = '25TIC06'
GROUP BY t.id, t.reference_number;
EOF
```

**Résultat attendu** :

```
 tender  | documents | total_sections | docs_with_sections
---------+-----------+----------------+--------------------
 25TIC06 |         3 |            377 |                  3
```

#### 7.3 Vérifier les Logs Celery

```bash
docker logs scorpius-celery-worker --tail=50 | grep -i "error\|warning\|success"
```

**Aucune erreur critique attendue**.

---

## 📊 Critères de Succès du Test E2E

### ✅ Extraction et Stockage

- [ ] 3 documents uploadés dans MinIO
- [ ] 3 documents avec `extraction_status = 'completed'`
- [ ] 377 sections créées dans `document_sections`
- [ ] Aucune erreur d'extraction dans les logs

### ✅ Détection de Structure

- [ ] 135 sections TOC détectées (~36%)
- [ ] 106 sections clés détectées (~28%)
- [ ] 295 relations parent-enfant établies (~78%)
- [ ] 18/18 processus ITIL détectés comme sections clés

### ✅ Optimisation Hiérarchique

- [ ] Réduction tokens : 15-25% vs approche flat
- [ ] Structure hiérarchique générée : ~98k chars
- [ ] Sections clés en contenu complet
- [ ] TOC exclues du prompt LLM

### ✅ Analyse LLM

- [ ] Appel Claude API réussi
- [ ] Input tokens : 30-35k
- [ ] Output tokens : 1.5-2k
- [ ] Coût : $0.10-0.15
- [ ] Analyse contient :
  - [ ] Résumé du tender
  - [ ] 10+ exigences principales
  - [ ] Mention "processus ITIL"
  - [ ] Délais identifiés
  - [ ] Risques identifiés
  - [ ] Documents obligatoires
  - [ ] Recommandations stratégiques

---

## 🐛 Troubleshooting

### Problème : Documents non trouvés

```bash
# Vérifier que les PDFs sont bien copiés
docker exec scorpius-celery-worker ls -la /app/real_pdfs/
```

**Solution** : Re-copier les PDFs (Étape 1)

### Problème : Erreur d'extraction "pdfplumber failed"

```bash
# Vérifier les logs détaillés
docker logs scorpius-celery-worker | grep -A 10 "pdfplumber"
```

**Solution** : Vérifier que le PDF n'est pas corrompu

### Problème : Aucune section clé détectée

```bash
# Vérifier les patterns de détection
docker exec scorpius-celery-worker python3 -c "
from app.services.parser_service import ParserService
ps = ParserService()
print(f'Total patterns: {len(ps.KEY_SECTION_PATTERNS)}')
process_patterns = [p for p in ps.KEY_SECTION_PATTERNS if 'process' in p[1]]
print(f'Process patterns: {len(process_patterns)}')
"
```

**Résultat attendu** :

```
Total patterns: 33
Process patterns: 7
```

### Problème : Erreur Claude API "Invalid API key"

```bash
# Vérifier la clé API
docker exec scorpius-celery-worker python3 -c "
from app.core.config import settings
print(f'API Key configured: {bool(settings.anthropic_api_key)}')
print(f'API Key starts with: {settings.anthropic_api_key[:10]}...')
"
```

**Solution** : Vérifier `.env` et reconstruire le conteneur

### Problème : Tokens trop élevés (>40k)

```bash
# Analyser la distribution des sections
docker exec scorpius-postgres psql -U scorpius -d scorpius_db -c "
SELECT
    is_key_section,
    is_toc,
    COUNT(*) as count,
    AVG(content_length) as avg_length,
    SUM(content_length) as total_chars
FROM document_sections
GROUP BY is_key_section, is_toc;
"
```

**Solution** : Vérifier que les TOC sont bien exclues et que les sections longues sont résumées

---

## 📝 Scripts de Test Réutilisables

### Script 1 : Reset Complet

```bash
#!/bin/bash
# reset_test_env.sh

echo "🗑️  Vidage de la base de données..."
docker exec scorpius-postgres psql -U scorpius -d scorpius_db -c "
TRUNCATE TABLE document_sections CASCADE;
TRUNCATE TABLE tender_documents CASCADE;
TRUNCATE TABLE tenders CASCADE;
"

echo "🗑️  Suppression des fichiers MinIO..."
docker exec scorpius-minio mc rm --recursive --force minio/tenders/

echo "✅ Environnement de test réinitialisé"
```

### Script 2 : Test E2E Automatisé

```bash
#!/bin/bash
# run_e2e_test.sh

set -e  # Exit on error

echo "🧪 TEST END-TO-END AUTOMATISÉ"
echo "=============================="

# 1. Reset
./reset_test_env.sh

# 2. Copier PDFs
echo "📄 Copie des PDFs..."
docker exec scorpius-celery-worker mkdir -p /app/real_pdfs
docker cp Examples/VSGP-AO/CCTP.pdf scorpius-celery-worker:/app/real_pdfs/
docker cp Examples/VSGP-AO/CCAP.pdf scorpius-celery-worker:/app/real_pdfs/
docker cp Examples/VSGP-AO/RC.pdf scorpius-celery-worker:/app/real_pdfs/

# 3. Exécuter test E2E
echo "🔄 Traitement des documents..."
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_fresh_e2e.py

# 4. Exécuter analyse LLM
echo "🤖 Analyse LLM..."
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_llm_analysis.py

# 5. Vérifications
echo "✅ Vérifications finales..."
docker exec scorpius-postgres psql -U scorpius -d scorpius_db -c "
SELECT
    COUNT(*) FILTER (WHERE is_key_section = true) as key_sections,
    COUNT(*) as total_sections
FROM document_sections;
" | grep -q "106.*377" && echo "✅ Sections OK" || echo "❌ Sections KO"

echo ""
echo "✅ TEST E2E TERMINÉ AVEC SUCCÈS"
```

### Script 3 : Validation Rapide

```bash
#!/bin/bash
# quick_validate.sh

echo "🔍 Validation rapide de l'état actuel"
echo "====================================="

# Statistiques BDD
echo "📊 Base de données:"
docker exec scorpius-postgres psql -U scorpius -d scorpius_db -t -c "
SELECT
    'Tenders: ' || COUNT(*) FROM tenders
UNION ALL
SELECT 'Documents: ' || COUNT(*) FROM tender_documents
UNION ALL
SELECT 'Sections: ' || COUNT(*) FROM document_sections
UNION ALL
SELECT 'Sections clés: ' || COUNT(*) FROM document_sections WHERE is_key_section = true
UNION ALL
SELECT 'Processus ITIL: ' || COUNT(*) FROM document_sections WHERE section_number LIKE '4.1.5.%' AND is_key_section = true;
"

# Vérifier MinIO
echo ""
echo "📦 Stockage MinIO:"
docker exec scorpius-minio mc ls minio/tenders/ | wc -l | xargs echo "Tenders stockés:"

# Vérifier dernière analyse
echo ""
echo "📄 Dernière analyse:"
docker exec scorpius-celery-worker ls -lh /app/analysis_result.json 2>/dev/null || echo "Aucune analyse trouvée"
```

---

## 🎯 Checklist Pré-Production

Avant de déployer en production, s'assurer que :

- [ ] Le test E2E passe sans erreur
- [ ] Les 18 processus ITIL sont détectés
- [ ] L'analyse LLM mentionne "processus ITIL"
- [ ] Les coûts LLM sont conformes ($0.10-0.15/tender)
- [ ] Aucune régression sur les tenders existants
- [ ] La documentation est à jour
- [ ] Les scripts de test sont versionnés
- [ ] Les feature flags sont configurés correctement
- [ ] Les logs ne montrent pas d'erreurs critiques
- [ ] Le temps de traitement est acceptable (<2 min/tender)

---

**Date de dernière mise à jour** : 2 octobre 2025
**Version** : 1.0
**Auteur** : Claude (avec validation humaine)
