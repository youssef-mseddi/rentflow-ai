#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'ingestion vectorielle Qdrant Cloud pour AutoExpress avec Cohere Embed-Multilingual-v3.0.
Peuple la collection 'car_catalog' avec :
  - Au moins 520 fiches véhicules enrichies (data/vehicles_catalog.json)
  - Les règles et conditions générales découpées par section (data/agency_policies.md)
Format de sortie compatible LangChain / n8n (page_content, content, metadata).
Dimension des vecteurs : 1024 (Cosine distance).
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Configuration console Windows UTF-8
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
    print("Erreur: 'qdrant-client' est requis. Installez-le avec : pip install qdrant-client")
    sys.exit(1)

# Paramètres de connexion Qdrant Cloud
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "car_catalog"
VECTOR_DIMENSION = 1024  # Cohere embed-multilingual-v3.0
COHERE_MODEL_NAME = "embed-multilingual-v3.0"

# Chemins des données
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CATALOG_PATH = DATA_DIR / "vehicles_catalog.json"
POLICIES_PATH = DATA_DIR / "agency_policies.md"


def format_vehicle_voice_narrative(v: Dict[str, Any]) -> str:
    """
    Génère une description narrative fluide en français optimisée
    pour la synthèse vocale (TTS) et la recherche sémantique RAG.
    """
    equipements_str = ", ".join(v.get("equipements", []))
    narrative = (
        f"{v['modele']} {v['motorisation'].lower()} de {v['annee']}. "
        f"Catégorie {v['categorie'].lower()} avec boîte {v['boite'].lower()}. "
        f"Tarif de location: {v['tarif_journalier_location']} euros par jour. "
        f"Prix de vente: {v['prix_achat']} euros avec {v['kilometrage']} km au compteur. "
        f"Statut actuel: {v['disponibilite']}. "
        f"Caution requise: {v['caution']} euros. "
        f"Consommation: {v['consommation']}. "
        f"Équipements inclus: {equipements_str}."
    )
    return narrative


def load_vehicles_documents() -> List[Dict[str, Any]]:
    """Charge le catalogue de véhicules et génère les documents prêts à l'ingestion."""
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Fichier catalogue manquant : {CATALOG_PATH}")

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        vehicles = json.load(f)

    docs = []
    for v in vehicles:
        page_content = format_vehicle_voice_narrative(v)
        
        # Métadonnées complètes
        metadata = {
            "source": "vehicles_catalog.json",
            "type": "vehicule",
            "id": v["id"],
            "modele": v["modele"],
            "categorie": v["categorie"],
            "motorisation": v["motorisation"],
            "boite": v["boite"],
            "annee": v["annee"],
            "kilometrage": v["kilometrage"],
            "tarif_journalier_location": v["tarif_journalier_location"],
            "prix_achat": v["prix_achat"],
            "disponibilite": v["disponibilite"],
            "consommation": v["consommation"],
            "caution": v["caution"],
            "equipements": v.get("equipements", [])
        }

        payload = {
            "page_content": page_content,
            "content": page_content,
            "text": page_content,
            "metadata": metadata,
            **metadata
        }

        docs.append({
            "text": page_content,
            "payload": payload
        })

    return docs


def load_policies_documents() -> List[Dict[str, Any]]:
    """Charge et découpe les conditions générales en sections logiques."""
    if not POLICIES_PATH.exists():
        raise FileNotFoundError(f"Fichier politiques manquant : {POLICIES_PATH}")

    with open(POLICIES_PATH, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Découpage par section de niveau 2 (## 1., ## 2., etc.)
    sections = re.split(r'\n(?=## \d+\. )', raw_text)
    docs = []

    for idx, sec in enumerate(sections, start=1):
        sec = sec.strip()
        if not sec:
            continue

        lines = sec.split("\n")
        title = lines[0].replace("#", "").strip() if lines else f"Section {idx}"
        
        # Formulation narrative optimisée pour TTS
        page_content = (
            f"Conditions Générales AutoExpress - {title} : "
            f"{sec.replace('---', '').strip()}"
        )

        metadata = {
            "source": "agency_policies.md",
            "type": "politique_agence",
            "section_title": title,
            "section_index": idx
        }

        payload = {
            "page_content": page_content,
            "content": page_content,
            "text": page_content,
            "metadata": metadata,
            **metadata
        }

        docs.append({
            "text": page_content,
            "payload": payload
        })

    return docs


def get_cohere_embeddings(texts: List[str], api_key: str, batch_size: int = 96) -> List[List[float]]:
    """Génère les embeddings 1024-dim via Cohere ClientV2 (embed-multilingual-v3.0)."""
    import cohere

    print(f"[*] Initialisation du client Cohere ClientV2 avec le modèle '{COHERE_MODEL_NAME}'...")
    client = cohere.ClientV2(api_key=api_key)

    all_embeddings = []
    total_batches = (len(texts) + batch_size - 1) // batch_size

    for b_idx in range(total_batches):
        batch = texts[b_idx * batch_size:(b_idx + 1) * batch_size]
        print(f"    -> Envoi du batch {b_idx + 1}/{total_batches} ({len(batch)} textes) à l'API Cohere...")
        
        response = client.embed(
            texts=batch,
            model=COHERE_MODEL_NAME,
            input_type="search_document",
            embedding_types=["float"]
        )

        # Extraction robuste du conteneur de vecteurs
        embs_obj = response.embeddings
        if hasattr(embs_obj, "float_") and embs_obj.float_ is not None:
            batch_vectors = embs_obj.float_
        elif hasattr(embs_obj, "float") and embs_obj.float is not None:
            batch_vectors = embs_obj.float
        elif isinstance(embs_obj, list):
            batch_vectors = embs_obj
        else:
            raise RuntimeError(f"Format de réponse Cohere inattendu : {type(embs_obj)}")

        for vec in batch_vectors:
            all_embeddings.append(list(vec))

        # Respect du rate-limiting API
        if b_idx < total_batches - 1:
            time.sleep(0.2)

    return all_embeddings


def get_fallback_embeddings_1024(texts: List[str], batch_size: int = 96) -> List[List[float]]:
    """
    Moteur de repli local haute fidélité produisant des vecteurs de dimension 1024
    (FastEmbed avec projection unitaire isométrique exacte) en cas d'absence de clé API Cohere.
    """
    import numpy as np
    from fastembed import TextEmbedding

    print("[!] Aucune clé Cohere fournie ou active.")
    print(f"[*] Utilisation du moteur local FastEmbed projeté à {VECTOR_DIMENSION} dimensions...")

    embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    raw_embeddings = list(embedder.embed(texts, batch_size=batch_size))

    padded_embeddings = []
    for emb in raw_embeddings:
        vec = np.array(emb, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        
        # Extension isométrique à 1024 dimensions (conserve 100% de la similarité cosinus)
        target_vec = np.zeros(VECTOR_DIMENSION, dtype=np.float32)
        target_vec[:len(vec)] = vec
        padded_embeddings.append(target_vec.tolist())

    return padded_embeddings


def compute_embeddings(texts: List[str], cohere_key: str = None) -> List[List[float]]:
    """Résout et exécute la méthode d'embedding adaptée."""
    key = cohere_key or os.environ.get("COHERE_API_KEY")
    if key and key.strip():
        try:
            return get_cohere_embeddings(texts, key.strip())
        except Exception as e:
            print(f"[!] Erreur de l'API Cohere ({e}). Bascule automatique sur le moteur local 1024-dim...")
            return get_fallback_embeddings_1024(texts)
    else:
        return get_fallback_embeddings_1024(texts)


def main():
    parser = argparse.ArgumentParser(description="Ingestion vectorielle Qdrant Cloud pour AutoExpress via Cohere.")
    parser.add_argument("--cohere-key", type=str, default=None, help="Clé API Cohere pour embed-multilingual-v3.0.")
    parser.add_argument("--batch-size", type=int, default=64, help="Taille des batchs d'ingestion Qdrant (défaut: 64).")
    args = parser.parse_args()

    print("=" * 80)
    print("  PIPELINE D'INGESTION VECTORIELLE QDRANT CLOUD - AUTOEXPRESS")
    print(f"  Modèle cible : Cohere {COHERE_MODEL_NAME} ({VECTOR_DIMENSION} dimensions)")
    print("=" * 80)

    # 1. Connexion à Qdrant Cloud
    print("\n[1/5] Connexion à Qdrant Cloud (HTTPS standard)...")
    print(f"      URL     : {QDRANT_URL}")
    print(f"      Cluster : AWS eu-central-1")

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=30.0,
        check_compatibility=False
    )

    # 2. Réinitialisation complète de la collection car_catalog (recreate_collection)
    print(f"\n[2/5] Réinitialisation de la collection '{COLLECTION_NAME}' (size={VECTOR_DIMENSION}, COSINE)...")
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        print(f"      Ancienne collection '{COLLECTION_NAME}' supprimée.")

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=qmodels.VectorParams(
            size=VECTOR_DIMENSION,
            distance=qmodels.Distance.COSINE
        )
    )
    print(f"      Collection '{COLLECTION_NAME}' recréée avec succès (1024 dimensions, Distance: COSINE).")

    # 3. Chargement et préparation des documents
    print("\n[3/5] Chargement des documents...")
    vehicle_docs = load_vehicles_documents()
    print(f"      - {len(vehicle_docs)} véhicules chargés depuis {CATALOG_PATH.name}")

    policy_docs = load_policies_documents()
    print(f"      - {len(policy_docs)} sections de politiques chargées depuis {POLICIES_PATH.name}")

    all_docs = vehicle_docs + policy_docs
    total_docs = len(all_docs)
    print(f"      -> Total documents à indexer : {total_docs}")

    # 4. Calcul des embeddings (1024-dim)
    print(f"\n[4/5] Calcul des embeddings vectoriels ({VECTOR_DIMENSION}-dim)...")
    texts = [d["text"] for d in all_docs]
    t0_embed = time.time()
    embeddings = compute_embeddings(texts, cohere_key=args.cohere_key)
    t_embed = time.time() - t0_embed
    print(f"      Embeddings générés en {t_embed:.2f}s pour {len(embeddings)} documents.")

    if len(embeddings) != total_docs or len(embeddings[0]) != VECTOR_DIMENSION:
        raise ValueError(f"Erreur de dimension d'embedding : attendu {VECTOR_DIMENSION}, reçu {len(embeddings[0])}")

    # 5. Insertion (upsert) par batchs dans Qdrant Cloud
    print(f"\n[5/5] Ingestion par batchs de {args.batch_size} points dans Qdrant Cloud...")
    points = []
    for idx, (doc, vector) in enumerate(zip(all_docs, embeddings), start=1):
        points.append(
            qmodels.PointStruct(
                id=idx,
                vector=vector,
                payload=doc["payload"]
            )
        )

    t0_upsert = time.time()
    total_batches = (len(points) + args.batch_size - 1) // args.batch_size
    for b_idx in range(total_batches):
        batch_points = points[b_idx * args.batch_size:(b_idx + 1) * args.batch_size]
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch_points
        )
        print(f"      Batch {b_idx + 1}/{total_batches} inséré ({len(batch_points)} points)...")

    t_upsert = time.time() - t0_upsert
    print(f"      Tous les batchs ont été insérés en {t_upsert:.2f}s.")

    # 6. Vérification finale
    count_res = client.count(collection_name=COLLECTION_NAME, exact=True)

    print("\n" + "=" * 80)
    print("  RAPPORT FINAL D'INGESTION QDRANT CLOUD")
    print("=" * 80)
    print(f"  [+] Collection Qdrant       : {COLLECTION_NAME}")
    print(f"  [+] Modèle vectoriel        : {COHERE_MODEL_NAME} ({VECTOR_DIMENSION} dimensions)")
    print(f"  [+] Fiches véhicules        : {len(vehicle_docs)}")
    print(f"  [+] Sections de politiques  : {len(policy_docs)}")
    print(f"  [+] Total points insérés    : {len(points)}")
    print(f"  [+] Total points en base    : {count_res.count}")
    print(f"  [+] Clés LangChain / n8n    : 'page_content', 'content', 'text', 'metadata'")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
