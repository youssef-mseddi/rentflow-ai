# RentFlow - Assistant Vocal de Location & Vente de Véhicules

Architecture complète pour un assistant vocal conversationnel dédié à la location courte/moyenne durée et à la vente de véhicules récents chez **RentFlow**.

---

## 📁 Structure du Projet

```text
RentFlow/
├── docker-compose.yml              # Déploiement n8n (5678) et Qdrant (6333) avec volumes persistants
├── requirements.txt                # Dépendances Python (qdrant-client, fastembed, cohere, openai)
├── README.md                       # Documentation d'architecture et guide de démarrage
├── data/
│   ├── vehicles_catalog.json       # Catalogue étendu de 527 véhicules (marché français actuel)
│   └── agency_policies.md          # Conditions d'éligibilité, caution, franchise, assurances
├── scripts/
│   └── generate_vehicles_catalog.py # Générateur du catalogue réaliste (527 véhicules équilibrés)
├── backend/app/tools/
│   └── finance_tools.py            # Outils financiers (simulate_car_loan, calculate_rental_quote, search_catalog)
├── rag/
│   ├── ingest_and_eval.py          # Benchmark comparatif de chunking (Récursif vs Structuré)
│   ├── populate_qdrant.py          # Ingestion Qdrant Cloud (text-embedding-3-small, 1536 dim)
│   └── populate_qdrant_cohere.py   # Ingestion Qdrant Cloud (Cohere embed-multilingual-v3.0, 1024 dim)
├── prompts/
│   ├── prompt_library.md           # Prompts V1 vs V2, CoT devis, guardrails et cas d'échec
│   └── multi_agent_system.md       # Architecture formelle multi-agents (Superviseur & Spécialistes)
├── frontend/
│   └── index.html                  # Interface web monopage pour tester l'assistant vocal n8n
└── tests/
    └── evaluate_agents.py          # Banc d'essai multi-agents (6 requêtes, routage, outils, phonétique)
```

---

## 🌐 Interface Web de Test Vocal (`frontend/index.html`)

Une application web monopage moderne (Tailwind CSS, design sombre) permettant de tester l'assistant vocal en conditions réelles :
- **Capture Micro** : Enregistrement WebRTC / MediaRecorder (`audio/webm`) avec animation d'onde pulsante et chronomètre en temps réel.
- **Envoi Webhook n8n** : Requête POST multipart (`data`: blob audio, `sessionId`: identifiant de session).
  - *URL Webhook n8n* : `http://localhost:5678/webhook/car-rental-voice-agent` par défaut (à remplacer par votre URL n8n dans `frontend/app.js`)
- **Entrée Texte alternative** : Formulaire de repli pour tester l'agent à l'écrit sans micro.
- **Restitution Multimodale** :
  - Transcription utilisateur par Whisper (`transcript` ou `user_text`).
  - Réponse textuelle et devis chiffré rédigé par l'agent IA.
  - Lecteur audio HTML5 décodant le flux MP3 base64 retourné par n8n avec lecture automatique instantanée.

### Lancement de l'Interface Web :
Ouvrez simplement le fichier [`frontend/index.html`](frontend/index.html) dans votre navigateur, ou lancez un serveur local rapide :
```powershell
python -m http.server 8000 --directory frontend
```
Puis accédez à [http://localhost:8000](http://localhost:8000).

---

## 🚗 Catalogue Véhicules Étendu (`data/vehicles_catalog.json`)

Le catalogue contient **527 véhicules réalistes** respectant rigoureusement la distribution demandée :
- **Catégories** : Citadines (25%), SUV (35%), Berlines (25%), Utilitaires / Monospaces (15%).
- **Motorisations** : Essence, Diesel, Hybride, Hybride Rechargeable (PHEV), 100% Électrique.
- **Segments** : Économique (Clio, 208, Sandero, Yaris), Milieu de gamme (3008, Arkana, Golf, Tucson, Qashqai), Premium (Classe C, BMW Série 3, Audi Q5, Tesla Model 3/Y, Porsche Macan), Utilitaires (Kangoo, Berlingo, Trafic, Transit Custom).

---

## 🚀 Utilisation des Scripts d'Ingestion Vectorielle

### 1. Ingestion Qdrant Cloud avec Cohere (`rag/populate_qdrant_cohere.py`)

Crée/réinitialise la collection `car_catalog` en **1024 dimensions (Distance: COSINE)**, 100% compatible avec le nœud n8n `Embed-Multilingual-v3.0` :

```powershell
# Avec votre clé API Cohere
python rag/populate_qdrant_cohere.py --cohere-key "VOTRE_CLE_COHERE"

# Ou via variable d'environnement
$env:COHERE_API_KEY="VOTRE_CLE_COHERE"
python rag/populate_qdrant_cohere.py
```

### 2. Ingestion Qdrant Cloud avec OpenAI (`rag/populate_qdrant.py`)

Pour une collection en **1536 dimensions (Distance: COSINE)** compatible avec OpenAI `text-embedding-3-small` :

```powershell
python rag/populate_qdrant.py --openai-key "sk-..."
```

---

## 📦 Payload Qdrant compatible n8n & LangChain

Chaque point stocké dans `car_catalog` dispose d'un payload normalisé :
- `page_content` : Description narrative fluide en français optimisée pour la synthèse vocale (TTS).
- `metadata` : Dictionnaire complet de l'objet véhicule ou de la règle d'agence.
- Attributs indexés de premier niveau (`categorie`, `motorisation`, `tarif_journalier_location`, `prix_achat`, `disponibilite`, `caution`) permettant des filtres déterministes.
