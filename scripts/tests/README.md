# Scripts de Test End-to-End

Ce répertoire contient tous les scripts de test et la documentation pour valider le pipeline complet d'analyse de tenders.

---

## 📋 Liste des Scripts

### 🧪 Scripts de Test Principaux

#### `test_fresh_e2e.py`
**Description** : Test end-to-end complet avec base de données vide

**Usage** :
```bash
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_fresh_e2e.py
```

**Ce qu'il fait** :
1. Crée un tender VSGP (25TIC06)
2. Upload 3 PDFs (CCTP, CCAP, RC) vers MinIO
3. Traite chaque document avec le pipeline optimisé
4. Affiche statistiques détaillées par document
5. Résumé global des sections détectées

**Résultats attendus** :
- 377 sections extraites
- 106 sections clés (28%)
- 135 sections TOC (36%)
- 19 processus ITIL détectés

---

#### `test_hierarchical_analysis.py`
**Description** : Génère la structure hiérarchique et calcule les économies de tokens

**Usage** :
```bash
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_hierarchical_analysis.py
```

**Ce qu'il fait** :
1. Charge toutes les sections de la BDD
2. Construit la structure hiérarchique optimisée
3. Compare avec l'approche "flat"
4. Calcule réduction tokens et économies coûts
5. Affiche 10 exemples de relations parent-enfant

**Résultats attendus** :
- Réduction : 15-25% de tokens
- Économie : ~$0.02 par analyse
- Hiérarchie préservée : 295 relations parent-enfant

---

#### `test_llm_analysis.py`
**Description** : Exécute l'analyse LLM complète avec Claude API

**Usage** :
```bash
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_llm_analysis.py
```

**Ce qu'il fait** :
1. Charge les 377 sections depuis la BDD
2. Construit le prompt avec structure hiérarchique
3. Appelle Claude API (Sonnet 4)
4. Parse et affiche l'analyse complète
5. Sauvegarde résultat dans `/app/analysis_result.json`

**Résultats attendus** :
- Input tokens : 30-35k
- Output tokens : 1.5-2k
- Coût : $0.10-0.15
- Analyse contient : exigences, risques, processus ITIL

---

### 🔍 Scripts d'Analyse

#### `analyze_extraction_quality.py`
**Description** : Analyse la qualité de l'extraction de contenu

**Usage** :
```bash
python3 scripts/tests/analyze_extraction_quality.py
```

**Ce qu'il fait** :
1. Statistiques globales d'extraction
2. Distribution des sections par type
3. Analyse de la détection de structure
4. Vérification cohérence hiérarchique

---

#### `test_hierarchy.py`
**Description** : Test spécifique de la hiérarchie parent-enfant

**Usage** :
```bash
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_hierarchy.py
```

**Ce qu'il fait** :
1. Vérifie les relations parent-enfant
2. Valide l'intégrité des `parent_id`
3. Affiche arbre hiérarchique échantillon

---

#### `test_end_to_end.py`
**Description** : Version alternative du test E2E

**Usage** :
```bash
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_end_to_end.py
```

---

## 📚 Documentation

### `TEST_END_TO_END.md`
**Guide complet** de la procédure de test end-to-end avec :
- 7 étapes détaillées
- Critères de succès mesurables
- Scripts réutilisables (bash)
- Section troubleshooting
- Checklist pré-production

---

## 🚀 Quick Start

### Test Complet en 3 Commandes

```bash
# 1. Vider la base de données
docker exec scorpius-postgres psql -U scorpius -d scorpius_db -c \
  "TRUNCATE TABLE document_sections CASCADE;
   TRUNCATE TABLE tender_documents CASCADE;
   TRUNCATE TABLE tenders CASCADE;"

# 2. Copier les PDFs dans le conteneur
docker exec scorpius-celery-worker mkdir -p /app/real_pdfs
docker cp Examples/VSGP-AO/CCTP.pdf scorpius-celery-worker:/app/real_pdfs/
docker cp Examples/VSGP-AO/CCAP.pdf scorpius-celery-worker:/app/real_pdfs/
docker cp Examples/VSGP-AO/RC.pdf scorpius-celery-worker:/app/real_pdfs/

# 3. Exécuter le test E2E complet
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_fresh_e2e.py
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_hierarchical_analysis.py
docker exec scorpius-celery-worker python3 /app/scripts/tests/test_llm_analysis.py
```

---

## 📊 Résultats Attendus (Référence)

### Extraction (test_fresh_e2e.py)
```
✅ Documents uploadés : 3
✅ Sections extraites : 377
   - CCTP : 202 sections (56 TOC, 46 clés)
   - CCAP : 128 sections (47 TOC, 49 clés)
   - RC   : 47 sections  (22 TOC, 13 clés)
✅ Total sections clés : 106 (28%)
✅ Total TOC : 135 (36%)
✅ Processus ITIL : 19/19 détectés (4.1.5.x)
```

### Optimisation (test_hierarchical_analysis.py)
```
✅ Structure hiérarchique : 87,701 chars (~21,925 tokens)
✅ Approche flat : 116,862 chars (~29,215 tokens)
✅ Réduction : -20% tokens
✅ Économie : $0.0193/analyse ($1.93 pour 100 tenders)
```

### Analyse LLM (test_llm_analysis.py)
```
✅ Input tokens : 32,637
✅ Output tokens : 1,677
✅ Coût : $0.1231
✅ Qualité :
   - 10 exigences principales
   - 7 risques identifiés
   - Processus ITIL mentionnés
   - 10 documents obligatoires
   - 7 recommandations
```

---

## 🐛 Troubleshooting

### Erreur : "PDFs not found"
```bash
# Re-copier les PDFs
docker exec scorpius-celery-worker mkdir -p /app/real_pdfs
docker cp Examples/VSGP-AO/*.pdf scorpius-celery-worker:/app/real_pdfs/
```

### Erreur : "Module not found"
```bash
# Vérifier que le conteneur est à jour
docker-compose up -d --build celery-worker
```

### Base de données non vide
```bash
# Reset complet
docker exec scorpius-postgres psql -U scorpius -d scorpius_db -c \
  "TRUNCATE TABLE document_sections CASCADE;
   TRUNCATE TABLE tender_documents CASCADE;
   TRUNCATE TABLE tenders CASCADE;"
```

---

## 📝 Utilisation dans le Conteneur Docker

**Important** : Les scripts doivent être copiés dans le conteneur pour être exécutés.

### Option 1 : Copie manuelle (développement)
```bash
docker cp scripts/tests/test_fresh_e2e.py scorpius-celery-worker:/app/scripts/tests/
```

### Option 2 : Volume Docker (recommandé)
Ajouter dans `docker-compose.yml` :
```yaml
volumes:
  - ./scripts:/app/scripts:ro
```

---

## 🔗 Références

- [TEST_END_TO_END.md](TEST_END_TO_END.md) - Documentation complète
- [Backend README](../../backend/README.md) - Configuration backend
- [Issue #1](https://github.com/cisbeo/scorpiusAO/issues/1) - Amélioration parsing tableaux

---

**Dernière mise à jour** : 2 octobre 2025
**Validé avec** : CCTP VSGP 25TIC06 (69 pages, 2.3MB)
