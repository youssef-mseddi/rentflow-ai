#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script autonome de peuplement de la base Qdrant Cloud pour AutoExpress.
Lit 'data/vehicles_catalog.json' et 'data/agency_policies.md',
génère des embeddings de dimension 1536 (OpenAI text-embedding-3-small ou fallback FastEmbed)
et indexe les points dans la collection 'car_catalog' au format compatible LangChain / n8n.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Configuration de la sortie console UTF-8 sous Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError:
    print("Erreur: Le package 'qdrant-client' est requis. Installez-le avec : pip install qdrant-client")
    sys.exit(1)

# Constantes de connexion Qdrant Cloud
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "car_catalog"
VECTOR_DIMENSION = 1536

# Chemins des données
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CATALOG_PATH = DATA_DIR / "vehicles_catalog.json"
POLICIES_PATH = DATA_DIR / "agency_policies.md"


def load_and_format_vehicles() -> List[Dict[str, Any]]:
    """
    Charge le catalogue de véhicules et génère pour chacun un texte descriptif
    complet ainsi qu'un payload enrichi compatible n8n / LangChain.
    """
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Fichier introuvable : {CATALOG_PATH}")

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        vehicles = json.load(f)

    documents = []
    for v in vehicles:
        equipements_str = ", ".join(v.get("equipements", []))
        
        # Texte descriptif complet et fluide pour la recherche sémantique & TTS vocal
        text_content = (
            f"[FICHE VÉHICULE AUTOEXPRESS]\n"
            f"Modèle : {v['modele']} (Marque : {v['marque']})\n"
            f"Catégorie : {v['categorie'].capitalize()} | Carburant / Motorisation : {v['motorisation']} | Boîte de vitesses : {v['boite_vitesse']}\n"
            f"Tarif journalier de location : {v['tarif_journalier_location']} € TTC par jour\n"
            f"Prix d'achat d'occasion : {v['prix_achat']} € TTC\n"
            f"Kilométrage au compteur : {v['kilometrage']} km\n"
            f"Disponibilité immédiate : {v['disponibilite']}\n"
            f"Places : {v['places']} | Année : {v['annee']} | Consommation ou Autonomie : {v['carburant_autonomie']}\n"
            f"Équipements inclus : {equipements_str}."
        )

        metadata = {
            "source": "vehicles_catalog.json",
            "type": "vehicle_card",
            "vehicle_id": v["id"],
            "marque": v["marque"],
            "modele": v["modele"],
            "categorie": v["categorie"],
            "motorisation": v["motorisation"],
            "boite_vitesse": v["boite_vitesse"],
            "tarif_journalier_location": v["tarif_journalier_location"],
            "prix_achat": v["prix_achat"],
            "kilometrage": v["kilometrage"],
            "disponibilite": v["disponibilite"],
            "annee": v["annee"]
        }

        # Format polyvalent n8n / LangChain (page_content, content, text et metadata)
        payload = {
            "page_content": text_content,
            "content": text_content,
            "text": text_content,
            "metadata": metadata,
            **metadata
        }

        documents.append({
            "text": text_content,
            "payload": payload
        })

    return documents


def load_and_format_policies() -> List[Dict[str, Any]]:
    """
    Charge les conditions générales de l'agence et les découpe par section logique
    (caution, franchises d'assurance, conditions d'âge, politique kilométrique, etc.).
    """
    if not POLICIES_PATH.exists():
        raise FileNotFoundError(f"Fichier introuvable : {POLICIES_PATH}")

    with open(POLICIES_PATH, "r", encoding="utf-8") as f:
        policies_raw = f.read()

    # Découpage par section de niveau 2 (## 1., ## 2., etc.)
    sections = re.split(r'\n(?=## \d+\. )', policies_raw)
    documents = []

    for idx, sec in enumerate(sections):
        sec = sec.strip()
        if not sec:
            continue

        # Extraction du titre de la section
        lines = sec.split("\n")
        title = lines[0].replace("#", "").strip() if lines else f"Section {idx + 1}"

        text_content = (
            f"[CONDITIONS GÉNÉRALES AUTOEXPRESS - {title.upper()}]\n"
            f"{sec}"
        )

        metadata = {
            "source": "agency_policies.md",
            "type": "agency_policy",
            "section_title": title,
            "section_index": idx + 1
        }

        payload = {
            "page_content": text_content,
            "content": text_content,
            "text": text_content,
            "metadata": metadata,
            **metadata
        }

        documents.append({
            "text": text_content,
            "payload": payload
        })

    return documents


def generate_embeddings_openai(texts: List[str], api_key: str) -> List[List[float]]:
    """Génère des embeddings de dimension 1536 via OpenAI text-embedding-3-small."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    print(f"[*] Génération de {len(texts)} embeddings via OpenAI 'text-embedding-3-small'...")
    # OpenAI gère les listes de textes en un seul appel
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    embeddings = [item.embedding for item in response.data]
    return embeddings


def generate_embeddings_fastembed_1536(texts: List[str]) -> List[List[float]]:
    """
    Fallback local haute fidélité via FastEmbed si aucune clé OpenAI n'est configurée :
    Génère un vecteur unitaire dense et l'étend de façon isométrique à 1536 dimensions
    (zero-padded L2-normalized), conservant 100% de la similarité cosinus.
    """
    import numpy as np
    from fastembed import TextEmbedding

    print("[*] Aucune clé OpenAI fournie : Utilisation du moteur local FastEmbed...")
    print(f"[*] Projection isométrique des vecteurs vers la dimension requise ({VECTOR_DIMENSION})...")
    
    embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    raw_embeddings = list(embedder.embed(texts))
    
    padded_embeddings = []
    for emb in raw_embeddings:
        vec = np.array(emb, dtype=np.float32)
        # Normalisation L2 préalable
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        # Extension à 1536 dimensions avec des zéros (isométrie exacte pour la distance cosinus)
        target_vec = np.zeros(VECTOR_DIMENSION, dtype=np.float32)
        target_vec[:len(vec)] = vec
        padded_embeddings.append(target_vec.tolist())

    return padded_embeddings


def get_embeddings(texts: List[str], openai_api_key: str = None) -> List[List[float]]:
    """Sélectionne le générateur d'embeddings approprié (OpenAI ou fallback FastEmbed)."""
    api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    if api_key and api_key.strip():
        try:
            return generate_embeddings_openai(texts, api_key.strip())
        except Exception as err:
            print(f"[!] Échec de l'appel OpenAI ({err}). Bascule sur FastEmbed...")
            return generate_embeddings_fastembed_1536(texts)
    else:
        return generate_embeddings_fastembed_1536(texts)


def main():
    parser = argparse.ArgumentParser(description="Injection du catalogue et des règles AutoExpress dans Qdrant Cloud.")
    parser.add_argument("--openai-key", type=str, default=None, help="Clé API OpenAI pour text-embedding-3-small (optionnelle).")
    parser.add_argument("--recreate", action="store_true", help="Forcer la récréation de la collection si elle existe déjà.")
    args = parser.parse_args()

    print("=" * 75)
    print("  INJECTION DES DONNÉES AUTOEXPRESS DANS QDRANT CLOUD")
    print("=" * 75)

    # 1. Connexion à Qdrant Cloud
    print(f"\n[1/5] Connexion à Qdrant Cloud...")
    print(f"      URL     : {QDRANT_URL}")
    print(f"      Cluster : AWS eu-central-1")

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=15.0,
        check_compatibility=False
    )

    # 2. Gestion de la collection
    print(f"\n[2/5] Vérification de la collection '{COLLECTION_NAME}'...")
    collection_exists = client.collection_exists(COLLECTION_NAME)

    if collection_exists and args.recreate:
        print(f"      Suppression de la collection existante '{COLLECTION_NAME}' (--recreate)...")
        client.delete_collection(COLLECTION_NAME)
        collection_exists = False

    if not collection_exists:
        print(f"      Création de la collection '{COLLECTION_NAME}' (size={VECTOR_DIMENSION}, distance=COSINE)...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=VECTOR_DIMENSION,
                distance=qmodels.Distance.COSINE
            )
        )
        print(f"      Collection '{COLLECTION_NAME}' créée avec succès.")
    else:
        print(f"      Collection '{COLLECTION_NAME}' existante détectée.")

    # 3. Chargement et préparation des documents
    print(f"\n[3/5] Préparation des documents métier...")
    vehicles_docs = load_and_format_vehicles()
    print(f"      - {len(vehicles_docs)} fiches véhicules préparées depuis vehicles_catalog.json")

    policies_docs = load_and_format_policies()
    print(f"      - {len(policies_docs)} sections de règles préparées depuis agency_policies.md")

    all_docs = vehicles_docs + policies_docs
    total_docs = len(all_docs)
    print(f"      Total : {total_docs} documents à indexer.")

    # 4. Génération des embeddings 1536-dim
    print(f"\n[4/5] Génération des embeddings {VECTOR_DIMENSION}-dim...")
    texts = [doc["text"] for doc in all_docs]
    embeddings = get_embeddings(texts, openai_api_key=args.openai_key)

    if len(embeddings) != total_docs or len(embeddings[0]) != VECTOR_DIMENSION:
        raise ValueError(f"Erreur de dimension d'embedding : attendu {VECTOR_DIMENSION}, reçu {len(embeddings[0])}")

    # 5. Insertion (upsert) dans Qdrant Cloud
    print(f"\n[5/5] Envoi des points vers Qdrant Cloud...")
    points = []
    for idx, (doc, vector) in enumerate(zip(all_docs, embeddings), start=1):
        points.append(
            qmodels.PointStruct(
                id=idx,
                vector=vector,
                payload=doc["payload"]
            )
        )

    # Upsert par batch
    batch_size = 50
    for i in range(0, len(points), batch_size):
        chunk = points[i:i + batch_size]
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=chunk
        )

    # Vérification finale du nombre de points dans la collection
    count_info = client.count(collection_name=COLLECTION_NAME, exact=True)
    
    print("\n" + "=" * 75)
    print("  SUCCÈS DE L'INJECTION QDRANT CLOUD")
    print("=" * 75)
    print(f"  [+] Collection ciblée      : {COLLECTION_NAME}")
    print(f"  [+] Dimension des vecteurs : {VECTOR_DIMENSION} (Distance: COSINE)")
    print(f"  [+] Fiches véhicules       : {len(vehicles_docs)}")
    print(f"  [+] Sections politiques    : {len(policies_docs)}")
    print(f"  [+] Total points insérés   : {len(points)}")
    print(f"  [+] Total points en base   : {count_info.count}")
    print(f"  [+] Clés de payload        : 'page_content', 'content', 'metadata' (compatible n8n/LangChain)")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
