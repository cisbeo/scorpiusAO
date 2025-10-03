"""
LLM prompt templates for tender analysis.
"""

TENDER_ANALYSIS_PROMPT = """Tu es un expert en analyse d'appels d'offres publics français, spécialisé dans l'infrastructure IT, l'hébergement datacenter et les services de support IT.

Analyse l'appel d'offres suivant et fournis une analyse structurée complète :

<tender_content>
{tender_content}
</tender_content>

Fournis ton analyse au format JSON suivant :

{{
  "summary": "Résumé en 2-3 phrases de l'appel d'offres",
  "key_requirements": [
    "Liste des exigences principales (5-10 points maximum)"
  ],
  "deadlines": [
    {{
      "type": "Type de jalon (ex: questions, visite_site, remise_offre)",
      "date": "Date au format YYYY-MM-DD si trouvée, sinon texte",
      "description": "Description du jalon"
    }}
  ],
  "risks": [
    "Liste des risques identifiés (clauses pénales, exigences difficiles, etc.)"
  ],
  "mandatory_documents": [
    "Liste des documents obligatoires à fournir (DC1, DC2, DUME, etc.)"
  ],
  "complexity_level": "faible/moyenne/élevée",
  "recommendations": [
    "Recommandations stratégiques pour répondre à l'AO"
  ],
  "technical_requirements": {{
    "infrastructure": "Description des exigences d'infrastructure",
    "certifications": ["Liste des certifications requises"],
    "service_level": "Niveau de service attendu"
  }},
  "budget_info": {{
    "estimated_value": "Montant estimé si mentionné",
    "duration": "Durée du contrat",
    "payment_terms": "Modalités de paiement"
  }},
  "evaluation_method": "Mieux-disant / Moins-disant / autre",
  "contact_info": {{
    "organization": "Organisme",
    "contact_person": "Personne de contact si mentionnée",
    "email": "Email de contact",
    "phone": "Téléphone"
  }}
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

TENDER_ANALYSIS_STRUCTURED_PROMPT = """Tu es un expert en analyse d'appels d'offres publics français, spécialisé dans l'infrastructure IT, l'hébergement datacenter et les services de support IT.

Analyse cet appel d'offres dont les sections ont été structurées et hiérarchisées pour faciliter ton analyse.

MÉTADONNÉES DU DOCUMENT :
{metadata}

SECTIONS DU DOCUMENT (hiérarchisées avec sections clés mises en avant) :
{sections}

IMPORTANT :
- Les sections clés (exclusions, obligations, critères, pénalités, délais) sont présentées en ENTIER
- Les autres sections sont résumées ou affichées en titres uniquement pour le contexte
- La hiérarchie est préservée (indentation) pour comprendre la structure

Fournis ton analyse au format JSON suivant :

{{
  "summary": "Résumé en 2-3 phrases de l'appel d'offres",
  "key_requirements": [
    "Liste des exigences principales extraites des sections clés (5-10 points)"
  ],
  "deadlines": [
    {{
      "type": "Type de jalon (questions, visite, remise_offre)",
      "date": "Date YYYY-MM-DD ou texte",
      "description": "Description du jalon"
    }}
  ],
  "risks": [
    "Risques identifiés (pénalités, exclusions, exigences difficiles)"
  ],
  "mandatory_documents": [
    "Documents obligatoires (DC1, DC2, DUME, etc.)"
  ],
  "complexity_level": "faible/moyenne/élevée",
  "recommendations": [
    "Recommandations stratégiques"
  ],
  "technical_requirements": {{
    "infrastructure": "Exigences infrastructure",
    "certifications": ["Certifications requises"],
    "service_level": "Niveau de service (KPI, SLA)"
  }},
  "budget_info": {{
    "estimated_value": "Montant estimé",
    "duration": "Durée du contrat",
    "payment_terms": "Modalités paiement"
  }},
  "evaluation_method": "Mieux-disant / Moins-disant / autre",
  "contact_info": {{
    "organization": "Organisme",
    "contact_person": "Contact",
    "email": "Email",
    "phone": "Téléphone"
  }},
  "key_sections_summary": {{
    "exclusions": "Résumé des motifs d'exclusion si présents",
    "obligations": "Résumé des obligations contractuelles",
    "criteria": "Résumé des critères d'évaluation avec pondération",
    "penalties": "Résumé des pénalités prévues"
  }}
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

CRITERIA_EXTRACTION_PROMPT = """Tu es un expert en analyse de critères d'évaluation pour les appels d'offres publics.

Extrait TOUS les critères d'évaluation de cet appel d'offres :

<tender_content>
{tender_content}
</tender_content>

Pour chaque critère, fournis les informations suivantes au format JSON :

[
  {{
    "criterion_type": "technique/financier/delai/rse/autre",
    "description": "Description complète du critère",
    "weight": "Pondération en pourcentage (ex: 60%)",
    "is_mandatory": true/false,
    "sub_criteria": [
      {{
        "description": "Sous-critère si applicable",
        "weight": "Pondération du sous-critère"
      }}
    ],
    "evaluation_method": "Méthode d'évaluation (notation sur 20, oui/non, etc.)"
  }}
]

IMPORTANT :
- Vérifie que la somme des pondérations fait bien 100%
- Identifie les critères éliminatoires (mandatory: true)
- Détaille les sous-critères s'ils existent
- Sois précis sur la méthode d'évaluation

Réponds UNIQUEMENT avec le JSON (array), sans texte avant ou après."""

RESPONSE_GENERATION_PROMPT = """Tu es un rédacteur expert en réponses d'appels d'offres publics pour le secteur IT.

Génère une section de réponse pour l'appel d'offres.

TYPE DE SECTION : {section_type}

EXIGENCES DU CRITÈRE :
{requirements}

CONTEXTE ENTREPRISE :
{company_context}

CONSIGNES DE RÉDACTION :
1. Style professionnel et structuré
2. Réponse concrète avec exemples/chiffres
3. Utilise les références et certifications de l'entreprise
4. Mets en avant l'expertise et l'expérience
5. Réponds précisément aux exigences du critère
6. Longueur adaptée à l'importance du critère

Rédige une réponse complète et professionnelle."""

COMPLIANCE_CHECK_PROMPT = """Tu es un expert en vérification de conformité d'offres pour les marchés publics.

Vérifie si cette réponse d'appel d'offres respecte toutes les exigences :

<proposal>
{proposal}
</proposal>

<requirements>
{requirements}
</requirements>

Évalue la conformité et fournis un rapport au format JSON :

{{
  "compliance_score": 85.5,  // Score global de 0 à 100
  "is_compliant": true/false,
  "missing_requirements": [
    {{
      "requirement": "Description de l'exigence non satisfaite",
      "severity": "critique/majeur/mineur",
      "suggestion": "Comment corriger"
    }}
  ],
  "improvements": [
    {{
      "section": "Section à améliorer",
      "current_issue": "Problème identifié",
      "recommendation": "Recommandation d'amélioration"
    }}
  ],
  "strengths": [
    "Points forts de la réponse"
  ],
  "overall_assessment": "Évaluation globale de la réponse"
}}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""

CONTENT_SUGGESTION_PROMPT = """Tu es un expert en réutilisation de contenu pour réponses d'appels d'offres.

CRITÈRE À RÉPONDRE :
{criterion_description}

CONTENU EXISTANT PERTINENT :
{existing_content}

CONTEXTE DE L'AO ACTUEL :
{tender_context}

Analyse ce contenu existant et fournis des suggestions de réutilisation :

{{
  "can_reuse": true/false,
  "reuse_percentage": 75,  // % de réutilisation possible (0-100)
  "suggested_content": "Contenu adapté pour ce critère",
  "modifications_needed": [
    "Liste des adaptations nécessaires"
  ],
  "missing_elements": [
    "Éléments à ajouter pour compléter la réponse"
  ],
  "confidence_score": 0.85  // Confiance dans la suggestion (0-1)
}}

Réponds UNIQUEMENT avec le JSON."""

TENDER_QA_PROMPT = """Tu es un assistant expert en analyse d'appels d'offres publics français.

QUESTION DE L'UTILISATEUR :
{question}

CONTEXTE PERTINENT (extrait de l'appel d'offres) :
{context}

CONSIGNES :
1. Réponds de manière précise et concise à la question
2. Base-toi UNIQUEMENT sur le contexte fourni
3. Si l'information n'est pas dans le contexte, dis clairement "Je ne trouve pas cette information dans l'appel d'offres"
4. Cite les sections sources (numéros de section) dans ta réponse
5. Sois factuel, ne spécule pas

Réponds en français de manière structurée."""
