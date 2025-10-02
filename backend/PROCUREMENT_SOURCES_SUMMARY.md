# Sources de Données pour les Appels d'Offres - Résumé des Améliorations

**Date**: 2025-10-02
**Statut**: ✅ **3 AMÉLIORATIONS COMPLÉTÉES**

---

## 📊 Vue d'Ensemble des Sources

ScorpiusAO récupère maintenant les appels d'offres depuis **2 sources principales** :

### 1. **BOAMP** (Bulletin Officiel des Annonces des Marchés Publics)
- **Type**: Marchés publics locaux et régionaux
- **Couverture**: Tous secteurs (dont IT)
- **Fréquence de mise à jour**: Toutes les heures
- **Période de recherche**: **90 jours** (amélioration #1)
- **Limite**: 500 publications par sync
- **API**: Opendatasoft Explore API v2.1

### 2. **AWS PLACE / DECP** (Données Essentielles de Commande Publique) ⭐ NOUVEAU
- **Type**: Marchés publics de l'État (valeur élevée)
- **Couverture**: Contrats IT infrastructure principalement
- **Fréquence de mise à jour**: Toutes les 4 heures
- **Période de recherche**: 30 jours
- **Limite**: 200 consultations par sync
- **Montant minimum**: 50 000€ (filtrage des petits marchés)
- **API**: DECP (data.economie.gouv.fr)

---

## ✅ Amélioration #1 : Période de Recherche Étendue (90 jours)

### Changements
- **BOAMP** : 1 jour → **90 jours**
- **Limite** : 100 → **500 publications**

### Fichier modifié
[app/core/celery_app.py](app/core/celery_app.py#L55-L56)

```python
# AVANT
"kwargs": {"days_back": 1, "limit": 100}

# APRÈS
"kwargs": {"days_back": 90, "limit": 500}
```

### Impact
- ✅ Capture les AO IT qui sont moins fréquents
- ✅ Meilleure couverture temporelle
- ✅ Réduit le risque de rater des marchés importants

---

## ✅ Amélioration #2 : Codes CPV Élargis

### Ajouts de Codes CPV

**Nouveaux codes ajoutés** (45 codes au total, contre 12 initialement) :

#### Core IT Services (72xxx)
- `72322000` - Services de gestion de données
- `72212000` - Services de programmation de logiciels système
- `72230000` - Services de développement de logiciels personnalisés
- `72240000` - Services de conseil en analyse de systèmes
- `72611000` - Services de soutien technique

#### Hardware & Equipment (30xxx, 48xxx)
- `30200000` - Équipements informatiques
- `30230000` - Matériel informatique
- `30231000` - Consoles d'affichage, terminaux
- `48000000` - Progiciels et systèmes d'information
- `48800000` - Systèmes et serveurs d'information
- `48820000` - Serveurs

#### Telecom & Network (32xxx, 64xxx)
- `32400000` - Réseaux
- `32412000` - Réseau informatique
- `32420000` - Équipements et matériel de réseau
- `64200000` - Services de télécommunications

#### Codes Famille (matching large)
- `72` - Tous les services informatiques
- `48` - Tous les progiciels/systèmes
- `30` - Tous les équipements informatiques

### Mots-clés Élargis

**Nouveaux mots-clés ajoutés** (89 mots-clés au total, contre 17 initialement) :

#### IT Services & Support
- support informatique, maintenance informatique
- supervision, monitoring, exploitation informatique
- administration système, gestion de parc
- hotline, helpdesk, service desk, astreinte

#### Security & Compliance
- cybersécurité, iso 27001, iso27001
- rgpd, gdpr, firewall, pare-feu, antivirus
- soc (Security Operations Center), siem

#### Methodologies & Standards
- itil, devops, agile, scrum
- iso 9001, iso 20000, cobit

#### Technologies & Solutions
- erp, crm, gestion documentaire, ged
- base de données, sgbd, middleware
- api, web service, interconnexion, intégration, migration

#### Telecom & Network
- voip, téléphonie ip, visioconférence, fibre optique
- wan, lan, vpn, wifi, commutateur, routeur, switch

#### Digital & Web
- site web, portail, application web, application mobile
- développement, logiciel, progiciel
- saas, paas, iaas

#### Organizations (DSI)
- dsi, direction informatique, direction numérique
- transformation digitale, transition numérique

### Fichier modifié
[app/services/boamp_service.py](app/services/boamp_service.py#L23-L177)

### Impact
- ✅ **Taux de matching attendu**: 5-15% (contre 0% précédemment)
- ✅ Couverture étendue aux marchés hardware, télécom, applications
- ✅ Détection des marchés de transformation digitale
- ✅ Capture des AO avec acronymes (DSI, ERP, CRM, etc.)

---

## ✅ Amélioration #3 : Intégration AWS PLACE/DECP

### Architecture

```
┌─────────────────────────────────────────────────────┐
│         AWS PLACE / DECP Integration                │
│                                                      │
│  ┌────────────┐    ┌──────────────┐   ┌──────────┐ │
│  │ DECP API   │───▶│ AWSPlaceService│──▶│Database │ │
│  │(data.gouv) │    │                │   │         │ │
│  └────────────┘    └──────────────┘   └──────────┘ │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ Celery Tasks (Every 4 hours)                   │ │
│  │  • Fetch consultations (min 50K€)             │ │
│  │  • Filter IT infrastructure                    │ │
│  │  • Save to aws_place_publications table        │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Nouveaux Fichiers Créés

#### 1. **Migration Base de Données**
[alembic/versions/2025_10_02_1727-add_aws_place_publications_table.py](alembic/versions/2025_10_02_1727-add_aws_place_publications_table.py)

Table `aws_place_publications` :
- **18 colonnes** (id, place_id, title, reference, organization, etc.)
- **6 indexes** (publication_date, deadline, status, cpv_codes, nuts_codes, organization)
- **Foreign key** vers `tenders.id`

#### 2. **Modèle SQLAlchemy**
[app/models/aws_place_publication.py](app/models/aws_place_publication.py)

- Propriétés calculées: `days_until_deadline`, `is_urgent`, `is_expired`
- Méthode `to_dict()` pour sérialisation API
- Relation vers `Tender` (matched_tender)

#### 3. **Service DECP**
[app/services/aws_place_service.py](app/services/aws_place_service.py)

**Fonctionnalités** :
- `fetch_latest_consultations()` - Récupération depuis DECP API
- `filter_relevant_consultations()` - Filtrage IT (CPV + keywords)
- `_parse_decp_record()` - Parsing des records DECP
- Codes CPV et mots-clés identiques à BOAMP (cohérence)

**API DECP** :
```
URL: https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp_augmente/records
Params:
  - limit: 100
  - order_by: datePublicationDonnees desc
  - where: datePublicationDonnees >= '2025-09-02' AND montant >= 50000
```

#### 4. **Tâches Celery**
[app/tasks/aws_place_tasks.py](app/tasks/aws_place_tasks.py)

**3 tâches** :
- `fetch_aws_place_consultations_task` - Récupération toutes les 4h
- `import_aws_place_as_tender_task` - Import manuel d'une consultation
- `cleanup_old_aws_place_publications_task` - Nettoyage hebdomadaire (6 mois)

#### 5. **Configuration Celery Beat**
[app/core/celery_app.py](app/core/celery_app.py#L65-L75)

**Planification** :
```python
# Fetch toutes les 4 heures
"fetch-aws-place-4hourly": {
    "schedule": crontab(minute=0, hour="*/4"),
    "kwargs": {"days_back": 30, "limit": 200, "min_amount": 50000}
}

# Cleanup dimanche 4h du matin
"cleanup-aws-place-weekly": {
    "schedule": crontab(hour=4, minute=0, day_of_week=0),
    "kwargs": {"days_to_keep": 180}
}
```

### Pourquoi DECP au lieu de AWS PLACE direct ?

**AWS PLACE** n'a pas d'API publique. Les alternatives :

1. ❌ **Web scraping** - Non recommandé (rate limiting, legal issues, fragilité)
2. ✅ **DECP API** - Données structurées open data (recommandé)
3. 💰 **API commerciale** - Coûteux

**DECP (Données Essentielles de Commande Publique)** :
- API REST publique et gratuite
- Données structurées et validées
- Mise à jour quotidienne
- Obligation légale de publication (fiabilité)
- Couvre tous les marchés publics > 25K€

### Impact
- ✅ **Source principale pour IT infrastructure** (marchés > 50K€)
- ✅ Taux de matching attendu : **15-30%** (focus IT)
- ✅ Complémentarité avec BOAMP (DECP = valeur élevée, BOAMP = volume)
- ✅ Données plus structurées (montants, CPV, NUTS)

---

## 📈 Comparaison Avant/Après

| Métrique | AVANT | APRÈS | Amélioration |
|----------|-------|-------|--------------|
| **Période de recherche BOAMP** | 1 jour | 90 jours | +8900% |
| **Limite BOAMP** | 100 | 500 | +400% |
| **Codes CPV** | 12 | 45 | +275% |
| **Mots-clés** | 17 | 89 | +424% |
| **Sources de données** | 1 (BOAMP) | 2 (BOAMP + DECP) | +100% |
| **Taux de matching estimé** | 0% | 10-20% | ∞ |
| **Fréquence BOAMP** | 1h | 1h | = |
| **Fréquence DECP** | N/A | 4h | NEW |

---

## 🚀 Déploiement

### 1. Appliquer la migration
```bash
cd backend
alembic upgrade head
```

### 2. Redémarrer Celery
```bash
# Arrêter les workers existants
celery -A app.core.celery_app control shutdown

# Redémarrer worker
celery -A app.core.celery_app worker --loglevel=info

# Redémarrer beat (scheduler)
celery -A app.core.celery_app beat --loglevel=info
```

### 3. Vérifier les tâches planifiées
```bash
# Liste des tâches actives
celery -A app.core.celery_app inspect active

# Liste des tâches planifiées
celery -A app.core.celery_app inspect scheduled
```

### 4. Test manuel
```python
# Test BOAMP (avec nouveaux paramètres)
from app.tasks.boamp_tasks import fetch_boamp_publications_task
result = fetch_boamp_publications_task.delay(days_back=90, limit=500)

# Test AWS PLACE
from app.tasks.aws_place_tasks import fetch_aws_place_consultations_task
result = fetch_aws_place_consultations_task.delay(days_back=30, limit=200, min_amount=50000)

# Voir le résultat
print(result.get())
```

---

## 📊 Monitoring

### Métriques à Surveiller

1. **Taux de matching** :
   - BOAMP : `relevant_count / total_count`
   - DECP : `relevant_count / total_count`
   - **Objectif** : 10-20% pour BOAMP, 15-30% pour DECP

2. **Volume de données** :
   - Publications BOAMP par jour
   - Consultations DECP par jour
   - **Objectif** : 5-10 AO IT pertinents par semaine

3. **Statuts** :
   - `new` - Nouvelles publications (à traiter)
   - `imported` - Importées comme Tender
   - `ignored` - Marquées comme non pertinentes
   - `error` - Erreurs de traitement

### Requêtes SQL Utiles

```sql
-- Statistiques BOAMP
SELECT
    status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM boamp_publications
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY status;

-- Statistiques DECP
SELECT
    status,
    COUNT(*) as count,
    AVG(estimated_amount) as avg_amount
FROM aws_place_publications
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY status;

-- Top CPV codes trouvés
SELECT
    cpv_code,
    COUNT(*) as count
FROM (
    SELECT jsonb_array_elements_text(cpv_codes) as cpv_code
    FROM aws_place_publications
    WHERE status = 'new'
) subquery
GROUP BY cpv_code
ORDER BY count DESC
LIMIT 10;

-- AO urgents (deadline < 7 jours)
SELECT
    title,
    organization,
    deadline,
    EXTRACT(DAY FROM (deadline - NOW())) as days_remaining
FROM aws_place_publications
WHERE deadline > NOW()
  AND deadline < NOW() + INTERVAL '7 days'
  AND status = 'new'
ORDER BY deadline ASC;
```

---

## 🔄 Prochaines Étapes Recommandées

### Court terme (1-2 semaines)
1. ✅ Valider le taux de matching réel sur données de production
2. ✅ Ajuster les codes CPV et mots-clés selon les résultats
3. ✅ Créer un dashboard de monitoring (Flower + custom metrics)

### Moyen terme (1 mois)
4. 🔄 Implémenter la détection automatique de faux positifs (ML-based)
5. 🔄 Ajouter des notifications (email/Slack) pour AO urgents
6. 🔄 Créer des templates de réponse basés sur les AO similaires

### Long terme (3 mois)
7. 🔄 Intégrer d'autres sources régionales (Maximilien Paris, AWS PLACE direct)
8. 🔄 Système de scoring prédictif (probabilité de gagner)
9. 🔄 Auto-import des AO avec score > 0.8

---

## 📝 Notes Techniques

### Différences BOAMP vs DECP

| Aspect | BOAMP | DECP |
|--------|-------|------|
| **Type de données** | Annonces (intention d'achat) | Contrats (attribution) |
| **Timing** | Avant signature | Après signature |
| **Montant** | Tous montants | > 25K€ obligatoire |
| **Structure** | Moins standardisée | Très structurée |
| **API** | Opendatasoft | data.gouv.fr |
| **Fréquence mise à jour** | Temps réel | Quotidienne |
| **Utilisation ScorpiusAO** | Détection précoce | Analyse rétroactive + veille |

### Stratégie de Filtrage

**Double filtrage** (CPV + Mots-clés) :
- ✅ **CPV match** → Publication pertinente
- ✅ **Keyword match** → Publication pertinente
- ✅ **Les deux** → Haute confiance
- ❌ **Aucun** → Ignorée

**Seuils recommandés** :
- BOAMP : Filtrage large (recall > precision)
- DECP : Filtrage précis (precision > recall) + montant > 50K€

---

## 🎯 Objectifs Atteints

### ✅ Amélioration #1 : Période de Recherche
- [x] BOAMP étendu à 90 jours
- [x] Limite augmentée à 500 publications
- [x] Configuration Celery Beat mise à jour

### ✅ Amélioration #2 : Codes CPV Élargis
- [x] 45 codes CPV (contre 12)
- [x] 89 mots-clés (contre 17)
- [x] Couverture hardware, telecom, digital
- [x] Support acronymes et termes techniques

### ✅ Amélioration #3 : AWS PLACE/DECP
- [x] Migration base de données
- [x] Modèle SQLAlchemy
- [x] Service DECP avec filtrage
- [x] Tâches Celery (fetch, import, cleanup)
- [x] Planification toutes les 4h
- [x] Filtrage > 50K€

---

**Conclusion** : Les 3 améliorations sont implémentées et prêtes pour le déploiement. Le système est maintenant capable de capturer efficacement les appels d'offres IT infrastructure depuis deux sources complémentaires (BOAMP + DECP).
