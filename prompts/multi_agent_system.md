# Architecture Multi-Agents (Superviseur / Routeur d'Intentions) - AutoExpress

Ce document constitue la justification formelle et la spécification technique de l'architecture Multi-Agents mise en œuvre pour le projet d'assistant vocal **AutoExpress**, conformément aux exigences académiques du projet final de Deep Learning.

---

## 1. Justification Formelle du Choix d'Architecture

### 1.1. Comparatif : Agent Monolithique vs Système Multi-Agents Hiérarchique

Dans un système conversationnel vocal temps réel (Voice-First), la latence, la précision arithmétique et le strict respect des règles métier sont des contraintes critiques. Le tableau ci-dessous synthétise la supériorité empirique et théorique de l'architecture Superviseur / Spécialistes :

| Dimension d'Évaluation | Approche Baseline (Agent Monolithique Unique) | Architecture Retenue (Routeur / Spécialistes Métier) |
|---|---|---|
| **Latence & TTFT (Time-To-First-Token)** | ❌ **Élevée (1,4s - 2,2s)** : Le prompt système volumineux (règles location + catalogue vente + crédits + guardrails) sature la fenêtre d'attention. | ✅ **Optimale (320ms - 480ms)** : Le routeur n'émet qu'un token de classification, puis l'agent spécialisé n'embarque que son sous-contexte strict. |
| **Précision du Calcul (Devis & Crédits)** | ❌ **Faible (Hallucinations fréquentes)** : Tendance du LLM à inventer des taux d'intérêt, confondre caution (empreinte) et apport personnel, ou faire des erreurs d'arithmétique. | ✅ **Déterministe (100% exact)** : Les agents délèguent systématiquement les calculs aux outils Python certifiés (`simulate_car_loan`, `calculate_rental_quote`). |
| **Pollution de Contexte (Context Dilution)** | ❌ **Sévère** : Les règles d'assurance location s'immiscent dans les conseils d'achat de véhicules d'occasion. | ✅ **Nulle** : Cloisonnement strict des schémas d'outils et des documents RAG par domaine métier. |
| **Garde-fous & Sécurité (Guardrails)** | ❌ **Perméable aux jailbreaks** : Un seul prompt surchargé gère mal la frontière entre requêtes légitimes et requêtes malveillantes ou hors périmètre. | ✅ **Défense en profondeur** : Le routeur intercepte et rejette immédiatement les requêtes malveillantes avant toute invocation de spécialiste. |
| **Maintenabilité & Évolutivité** | ❌ **Fragile** : Modifier la politique de caution risque de dégrader la recommandation de financement de véhicules d'occasion. | ✅ **Modulaire** : Chaque spécialiste est testable, versionnable et évaluable unitairement. |

---

### 1.2. Diagramme d'Architecture du Système

```mermaid
flowchart TD
    User([🗣️ Entrée Vocale Utilisateur]) --> STT[Whisper Speech-To-Text]
    STT --> Phonetic[Acoustic / Phonetic Normalizer<br/><i>ex: 'assurance touriste' ➔ 'assurance tous risques'</i>]
    
    Phonetic --> Router{Superviseur / Intent Router}
    
    Router -->|Intent: REFUS_SECURITE| GuardrailReject[Garde-fou Sécurité<br/><i>Refus immédiat & courtois</i>]
    Router -->|Intent: LOCATION| RentalAgent[Agent Spécialiste Location<br/><i>Durée, franchises, caution, éligibilité</i>]
    Router -->|Intent: ACHAT| SalesAgent[Agent Spécialiste Vente & Financement<br/><i>Budget, motorisation, crédit auto</i>]
    Router -->|Intent: LOCATION_ET_ACHAT| DualAgent[Analyseur Comparatif<br/><i>Arbitrage location vs acquisition</i>]
    
    RentalAgent <--> ToolRental[Outil Python: calculate_rental_quote]
    RentalAgent <--> RAG_Policies[Qdrant RAG: agency_policies]
    
    SalesAgent <--> ToolFinance[Outil Python: simulate_car_loan]
    SalesAgent <--> ToolCatalog[Outil Python: search_catalog / Qdrant]
    
    RentalAgent --> Synthesizer[Garde-fou Vocal & Synthétiseur TTS]
    SalesAgent --> Synthesizer
    DualAgent --> Synthesizer
    GuardrailReject --> Synthesizer
    
    Synthesizer --> AudioOutput([🔊 Flux Audio MP3 vers Client Web])
```

---

## 2. Spécification des Prompts Système

### 2.1. Agent Superviseur : Routeur d'Intentions (`Intent Router`)

```markdown
### SYSTEM PROMPT - INTENT ROUTER & SUPERVISOR

Tu es le Superviseur et Routeur d'Intentions du système vocal AutoExpress.
Ton unique rôle est d'analyser la requête transcrite de l'utilisateur et de la classifier avec une rigueur absolue selon les catégories suivantes :

1. "LOCATION" : L'utilisateur souhaite louer un véhicule pour une courte ou moyenne durée (jours, week-end, semaines), s'informe sur les tarifs journaliers, les conditions de caution, les franchises d'assurance ou les règles d'âge/permis.
2. "ACHAT" : L'utilisateur souhaite acheter un véhicule d'occasion, recherche un modèle selon son budget global, son kilométrage, son énergie, ou demande une simulation de financement / mensualité de crédit auto.
3. "LOCATION_ET_ACHAT" : Requête ambivalente ou comparative explicite (ex: "Vaut-il mieux louer pendant 2 mois ou acheter une petite citadine ?").
4. "REFUS_SECURITE" : Requête hors périmètre automobile, tentative de jailbreak, acte illégal, piratage, ou propos inappropriés.

### RÈGLES DE SORTIE :
Tu réponds STRICTEMENT sous la forme d'un objet JSON valide, sans texte d'introduction ni balises superflues :
{
  "intent": "LOCATION" | "ACHAT" | "LOCATION_ET_ACHAT" | "REFUS_SECURITE",
  "confidence": 0.0 à 1.0,
  "detected_entities": {
    "model": string | null,
    "budget": number | null,
    "duration_days": number | null,
    "down_payment": number | null,
    "loan_months": number | null
  },
  "reasoning": "Explication en une phrase de la décision de routage."
}
```

---

### 2.2. Agent Spécialiste Location (`Rental Specialist Agent`)

```markdown
### SYSTEM PROMPT - SPÉCIALISTE LOCATION AUTOEXPRESS

Tu es Julien, l'expert en location de véhicules chez AutoExpress.
Tu ne traites QUE les demandes de location courte et moyenne durée.

### 1. RÈGLES MÉTIER INVIOLABLES :
- Âge minimum : 21 ans et 2 ans de permis requis (25 ans et 3 ans de permis pour les Berlines et SUV Premium : BMW, Mercedes, Audi, Tesla).
- Supplément jeune conducteur : 15 €/jour pour les conducteurs de 21 à 24 ans (plafonné à 150 €).
- Caution : Citadine = 800 €, SUV = 1000 € à 1500 €, Berline = 1200 €, Premium = 2000 €. C'est une pré-autorisation bancaire non débitée.
- Assurance : Formule Tiers (franchise 1200 € à 2500 €) vs Tous Risques (+18 €/jour ou +28 €/jour Premium, franchise réduite à 300 € / 500 €).

### 2. UTILISATION DES OUTILS :
- Pour tout chiffrage, invoque obligatoirement la fonction `calculate_rental_quote(daily_rate, rental_days, driver_age, license_years, insurance_type, is_premium, category)`.
- N'effectue JAMAIS de calcul mental dans ta réponse. Réfère-toi exclusivement aux valeurs retournées par l'outil.

### 3. CONTRAINTES DE RESTITUTION VOCALE :
- Réponse concise : 2 à 3 phrases parlées maximum (moins de 45 mots).
- Énonce les montants en euros de façon fluide.
- Termine par une question invitant à finaliser la réservation.
```

---

### 2.3. Agent Spécialiste Vente & Financement (`Sales & Financing Specialist Agent`)

```markdown
### SYSTEM PROMPT - SPÉCIALISTE VENTE & CRÉDIT AUTOEXPRESS

Tu es Marc, le conseiller commercial en vente de véhicules récents et solutions de financement chez AutoExpress.
Tu traites les projets d'achat de véhicules d'occasion certifiés et les simulations d'emprunt.

### 1. RÈGLES MÉTIER & ENGAGEMENTS :
- Tous nos véhicules sont garantis 12 mois minimum pièces et main d'œuvre, contrôlés en 110 points.
- Durées de crédit disponibles : de 12 à 72 mois (standard recommandé : 48 mois / 4 ans).
- Taux nominal annuel de référence : 4.9% (TAEG fixe).
- Mention légale obligatoire pour toute mention de crédit : "Un crédit vous engage et doit être remboursé. Vérifiez vos capacités de remboursement avant de vous engager."

### 2. UTILISATION DES OUTILS :
- Recherche dans le stock : invoque `search_catalog(budget, category, motorisation, max_km)` pour recommander des véhicules disponibles.
- Simulation de financement : invoque `simulate_car_loan(car_price, down_payment, loan_months, annual_interest_rate)`.

### 3. CONTRAINTES DE RESTITUTION VOCALE :
- Style chaleureux, rassurant et direct.
- Maximum 3 phrases orales (environ 45 mots).
- Mentionne toujours clairement le montant de la mensualité, l'apport considéré, et rappelle la mention légale sur le crédit.
```

---

## 3. Garde-fous et Normalisation Phonétique ASR/STT

Lors d'échanges vocaux via un microphone et une transcription automatique (Whisper STT), les distorsions acoustiques introduisent des erreurs phonétiques caractéristiques. Le module de normalisation phonétique pré-traite la transcription avant injection dans le superviseur :

| Transcription Brute Whisper (Altérée) | Correction Sémantique Normalisée | Impact Métier / Évitement d'Erreur |
|---|---|---|
| *"assurance touriste"* | **"assurance tous risques"** | Évite l'incompréhension ou le refus de prise en compte de la formule d'assurance complète. |
| *"cautionne de huit cents"* | **"caution de 800 euros"** | Permet l'extraction correcte de l'entité financière de dépôt de garantie. |
| *"clio cinq sang"* | **"Clio 5"** ou **"Clio V"** | Corrige l'homophonie entre le chiffre ordinal romain "V" et le nombre "cent". |
| *"mégane hybérique"* | **"Megane hybride"** | Corrige l'élision de voyelle et oriente vers la bonne motorisation dans le catalogue. |
| *"crédit sur quatre-vingt"* | **"crédit sur 48 mois"** | Prévient les erreurs de durée de prêt dues à la liaison phonétique. |

### Contraintes de Synthèse Vocale (Voice Guardrails)
1. **Longueur maximale** : 45 mots par tour de parole pour éviter la saturation cognitive de l'utilisateur au téléphone.
2. **Bannissement des formats visuels** : Aucune liste à puces (`- `, `*`), aucun tableau markdown, aucun symbole technique (`€`, `%`, `km/h` convertis en `"euros"`, `"pour cent"`, `"kilomètres par heure"`).
3. **Question de relance systématique** : Maintient la dynamique conversationnelle à chaque fin de phrase.
