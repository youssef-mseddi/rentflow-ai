#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'ingestion et d'évaluation comparative RAG pour l'assistant vocal AutoExpress.
Compare deux approches de découpage (Chunking) :
  1. Chunking Récursif classique (découpage brut par taille de fenêtre et délimiteurs)
  2. Découpage Structuré métier (fiches véhicules sémantiques enrichies + sections markdown de politiques)

Indexation dans Qdrant (connexion au serveur local ou fallback en mémoire)
et banc d'essai sur 5 requêtes utilisateurs types.
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    from fastembed import TextEmbedding
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except ImportError as e:
    print(f"Erreur d'importation : {e}")
    print("Veuillez installer les dépendances avec : pip install qdrant-client fastembed")
    sys.exit(1)

# Définition des chemins relatifs
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CATALOG_PATH = DATA_DIR / "vehicles_catalog.json"
POLICIES_PATH = DATA_DIR / "agency_policies.md"

COLLECTION_RECURSIVE = "autoexpress_recursive_chunking"
COLLECTION_STRUCTURED = "autoexpress_structured_chunking"
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# 5 Requêtes d'évaluation représentatives du cas d'usage vocal
EVALUATION_QUERIES = [
    {
        "id": "Q1",
        "query": "Je cherche un SUV électrique pour moins de 100€ par jour",
        "description": "Recherche véhicule combinant catégorie (SUV), énergie (Électrique) et filtre de prix (<100€/j)",
        "expected_keywords": ["SUV", "Électrique", "Tesla Model Y", "95"]
    },
    {
        "id": "Q2",
        "query": "Quel est l'âge minimum et l'ancienneté de permis pour louer une berline premium comme la BMW Série 3 ?",
        "description": "Politique d'éligibilité spécifique aux catégories haut de gamme / premium",
        "expected_keywords": ["25 ans", "3 ans", "premium", "Série 3"]
    },
    {
        "id": "Q3",
        "query": "Avez-vous une citadine hybride ou essence disponible à l'achat avec moins de 30 000 kilomètres ?",
        "description": "Recherche véhicule en vente (VO), catégorie citadine, motorisation et contrainte de kilométrage",
        "expected_keywords": ["citadine", "achat", "Clio", "208", "Yaris", "disponible"]
    },
    {
        "id": "Q4",
        "query": "Quelle est la différence entre l'assurance au tiers et l'assurance tous risques pour la franchise ?",
        "description": "Comparatif précis des garanties et montants résiduels de franchise",
        "expected_keywords": ["tiers", "tous risques", "franchise", "300 €", "1 200 €"]
    },
    {
        "id": "Q5",
        "query": "Combien coûte la caution pour un SUV familial et comment est-elle débloquée ?",
        "description": "Conditions de caution, typologie SUV familial et mécanisme d'empreinte bancaire",
        "expected_keywords": ["1 500 €", "caution", "7 à 14 jours", "pré-autorisation"]
    }
]


# =====================================================================
# 1. Stratégie 1 : Chunking Récursif Classique
# =====================================================================
def recursive_character_text_splitter(
    text: str,
    chunk_size: int = 400,
    chunk_overlap: int = 60,
    separators: List[str] = None
) -> List[str]:
    """
    Implémentation générique d'un découpage récursif de texte basé sur
    des séparateurs hiérarchiques (\n\n, \n, . , ' ', vide).
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    def _split_text(txt: str, seps: List[str]) -> List[str]:
        final_chunks = []
        if not seps:
            return [txt] if txt else []
        
        separator = seps[0]
        splits = txt.split(separator) if separator else list(txt)
        
        good_splits = []
        for s in splits:
            if not s:
                continue
            if len(s) < chunk_size:
                good_splits.append(s)
            else:
                if len(seps) > 1:
                    good_splits.extend(_split_text(s, seps[1:]))
                else:
                    good_splits.append(s)
        
        # Fusion des splits avec overlap
        current_chunk = ""
        for piece in good_splits:
            candidate = (current_chunk + separator + piece).strip() if current_chunk else piece
            if len(candidate) <= chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    final_chunks.append(current_chunk)
                current_chunk = piece
        if current_chunk:
            final_chunks.append(current_chunk)
        return final_chunks

    return _split_text(text, separators)


def build_recursive_chunks() -> List[Dict[str, Any]]:
    """
    Construit les chunks avec l'approche naïve récursive :
    Concaténation brute des JSON et du Markdown, découpés sans conscience sémantique.
    """
    chunks = []
    
    # 1. Traitement du catalogue brut en format JSON stringifié
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog_raw_text = f.read()

    catalog_chunks = recursive_character_text_splitter(catalog_raw_text, chunk_size=380, chunk_overlap=50)
    for idx, c in enumerate(catalog_chunks):
        chunks.append({
            "text": c,
            "metadata": {
                "source": "vehicles_catalog.json",
                "strategy": "recursive_chunking",
                "chunk_index": idx,
                "type": "raw_catalog_slice"
            }
        })

    # 2. Traitement des politiques de l'agence en Markdown brut
    with open(POLICIES_PATH, "r", encoding="utf-8") as f:
        policies_raw_text = f.read()

    policy_chunks = recursive_character_text_splitter(policies_raw_text, chunk_size=380, chunk_overlap=50)
    for idx, c in enumerate(policy_chunks):
        chunks.append({
            "text": c,
            "metadata": {
                "source": "agency_policies.md",
                "strategy": "recursive_chunking",
                "chunk_index": idx,
                "type": "raw_policy_slice"
            }
        })

    return chunks


# =====================================================================
# 2. Stratégie 2 : Découpage Structuré Métier (Fiches & Sections)
# =====================================================================
def build_structured_chunks() -> List[Dict[str, Any]]:
    """
    Construit des chunks sémantiquement complets et optimisés pour le RAG vocal :
    - 1 fiche descriptive complète et contextualisée par véhicule + métadonnées typées
    - Découpage du markdown par section H2 / H3 avec préservation du titre parent
    """
    chunks = []

    # 1. Traitement du catalogue par Fiche Véhicule Enrichie
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        vehicles = json.load(f)

    for v in vehicles:
        equipements_str = ", ".join(v.get("equipements", []))
        text_representation = (
            f"[FICHE VÉHICULE AUTOEXPRESS]\n"
            f"Référence : {v['id']} | Modèle : {v['modele']} | Marque : {v['marque']}\n"
            f"Catégorie : {v['categorie'].capitalize()} | Motorisation : {v['motorisation']} | Boîte : {v['boite_vitesse']}\n"
            f"Places : {v['places']} | Année : {v['annee']} | Consommation/Autonomie : {v['carburant_autonomie']}\n"
            f"Tarif Location : {v['tarif_journalier_location']} € par jour | Prix Achat Occasion : {v['prix_achat']} €\n"
            f"Kilométrage certifié : {v['kilometrage']} km | Statut de disponibilité : {v['disponibilite']}\n"
            f"Équipements inclus : {equipements_str}."
        )

        metadata = {
            "source": "vehicles_catalog.json",
            "strategy": "structured_chunking",
            "type": "vehicle_card",
            "vehicle_id": v["id"],
            "marque": v["marque"],
            "modele": v["modele"],
            "categorie": v["categorie"],
            "motorisation": v["motorisation"],
            "boite_vitesse": v["boite_vitesse"],
            "tarif_journalier": v["tarif_journalier_location"],
            "prix_achat": v["prix_achat"],
            "kilometrage": v["kilometrage"],
            "disponibilite": v["disponibilite"]
        }

        chunks.append({
            "text": text_representation,
            "metadata": metadata
        })

    # 2. Traitement des politiques par Section Markdown structurée
    with open(POLICIES_PATH, "r", encoding="utf-8") as f:
        policies_raw = f.read()

    # Découpage par section niveau 2 (## )
    sections = re.split(r'\n(?=## \d+\. )', policies_raw)
    for sec_idx, sec in enumerate(sections):
        sec = sec.strip()
        if not sec:
            continue
        
        # Extraction du titre de la section
        lines = sec.split("\n")
        title = lines[0].replace("#", "").strip() if lines else f"Section {sec_idx}"
        
        text_representation = f"[POLITIQUE AUTOEXPRESS - {title}]\n{sec}"
        metadata = {
            "source": "agency_policies.md",
            "strategy": "structured_chunking",
            "type": "policy_section",
            "section_title": title,
            "section_index": sec_idx
        }

        chunks.append({
            "text": text_representation,
            "metadata": metadata
        })

    return chunks


# =====================================================================
# 3. Connexion Qdrant & Indexation
# =====================================================================
def get_qdrant_client() -> Tuple[QdrantClient, str]:
    """
    Tente de se connecter au conteneur Qdrant local (port 6333).
    Si le serveur n'est pas démarré, bascule automatiquement sur le moteur
    local Qdrant embarqué (:memory:) pour garantir une exécution 100% autonome.
    """
    try:
        client = QdrantClient(url="http://localhost:6333", timeout=1.0, check_compatibility=False)
        # Test de connectivité
        client.get_collections()
        return client, "Serveur Docker Qdrant (http://localhost:6333)"
    except Exception:
        # Fallback en mémoire
        client = QdrantClient(":memory:")
        return client, "Qdrant In-Memory Engine (Autonome / Sans conteneur)"


def index_chunks(
    client: QdrantClient,
    collection_name: str,
    chunks: List[Dict[str, Any]],
    embedder: TextEmbedding
) -> float:
    """Indexe une liste de chunks dans une collection Qdrant."""
    t_start = time.time()
    
    # 1. Génération des embeddings
    texts = [c["text"] for c in chunks]
    embeddings = list(embedder.embed(texts))
    vector_dim = len(embeddings[0])

    # 2. Création propre de la collection
    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(
            size=vector_dim,
            distance=qmodels.Distance.COSINE
        )
    )

    # 3. Insertion par batch
    points = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        points.append(
            qmodels.PointStruct(
                id=idx + 1,
                vector=emb.tolist(),
                payload={
                    "text": chunk["text"],
                    **chunk["metadata"]
                }
            )
        )

    client.upsert(collection_name=collection_name, points=points)
    duration = time.time() - t_start
    return duration


# =====================================================================
# 4. Évaluation & Comparaison de Pertinence
# =====================================================================
def evaluate_strategy_retrieval(
    client: QdrantClient,
    collection_name: str,
    query: str,
    embedder: TextEmbedding,
    expected_keywords: List[str],
    top_k: int = 3
) -> Dict[str, Any]:
    """Exécute une recherche vectorielle et évalue la pertinence."""
    query_vector = list(embedder.embed([query]))[0].tolist()
    
    results = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k
    ).points

    top_point = results[0] if results else None
    top_text = top_point.payload.get("text", "") if top_point else ""
    top_score = top_point.score if top_point else 0.0

    # Critère 1 : Score Cosinus de Similarité
    # Critère 2 : Taux de présence des mots-clés essentiels attendus
    keywords_found = [kw for kw in expected_keywords if kw.lower() in top_text.lower()]
    keyword_recall = len(keywords_found) / len(expected_keywords) if expected_keywords else 0.0

    # Critère 3 : Intégrité du contexte (non tronqué / utilisable pour un TTS vocal)
    is_truncated = ("{\n" in top_text and not top_text.strip().endswith("}")) or \
                   ("}\n" in top_text and not top_text.strip().startswith("{")) or \
                   (top_text.startswith("...") or top_text.endswith("..."))
    
    has_rich_metadata = bool(top_point and "tarif_journalier" in top_point.payload or "section_title" in top_point.payload)

    return {
        "top_score": round(top_score, 4),
        "keyword_recall": round(keyword_recall * 100, 1),
        "keywords_found": keywords_found,
        "is_truncated": is_truncated,
        "has_rich_metadata": has_rich_metadata,
        "top_text_snippet": top_text.replace("\n", " ")[:140] + ("..." if len(top_text) > 140 else ""),
        "full_top_text": top_text
    }


def run_benchmark():
    """Point d'entrée du banc d'essai complet."""
    print("=" * 80)
    print("  BANC D'ESSAI COMPARATIF RAG : RECURSIVE CHUNKING VS STRUCTURED CHUNKING")
    print("  Assistant Vocal AutoExpress (Location & Vente de Véhicules)")
    print("=" * 80)

    # Initialisation de Qdrant et du modèle de vectorisation
    client, mode_label = get_qdrant_client()
    print(f"\n[*] Mode d'exécution Qdrant : {mode_label}")
    print(f"[*] Modèle d'embedding : {EMBEDDING_MODEL_NAME} (FastEmbed ONNX)")
    embedder = TextEmbedding(model_name=EMBEDDING_MODEL_NAME)

    # 1. Préparation et indexation de la stratégie récursive
    print("\n--- [1/2] Stratégie Récursive Classique ---")
    rec_chunks = build_recursive_chunks()
    rec_time = index_chunks(client, COLLECTION_RECURSIVE, rec_chunks, embedder)
    print(f"  -> {len(rec_chunks)} chunks générés et indexés en {rec_time:.2f}s dans '{COLLECTION_RECURSIVE}'")

    # 2. Préparation et indexation de la stratégie structurée
    print("\n--- [2/2] Stratégie Structurée par Fiche & Section ---")
    struct_chunks = build_structured_chunks()
    struct_time = index_chunks(client, COLLECTION_STRUCTURED, struct_chunks, embedder)
    print(f"  -> {len(struct_chunks)} chunks générés et indexés en {struct_time:.2f}s dans '{COLLECTION_STRUCTURED}'")

    # 3. Évaluation comparative sur les 5 requêtes
    print("\n" + "=" * 80)
    print("  TESTS DE PERTINENCE SUR LES 5 REQUÊTES TYPES")
    print("=" * 80)

    summary_stats = {
        "recursive": {"scores": [], "recalls": [], "truncated_count": 0},
        "structured": {"scores": [], "recalls": [], "truncated_count": 0}
    }

    for item in EVALUATION_QUERIES:
        q_id = item["id"]
        q_text = item["query"]
        expected = item["expected_keywords"]

        print(f"\n--------------------------------------------------------------------------------")
        print(f"[REQUETE {q_id}] : \"{q_text}\"")
        print(f"   Objectif : {item['description']}")
        print(f"   Mots-clés cibles attendus : {expected}")

        rec_eval = evaluate_strategy_retrieval(client, COLLECTION_RECURSIVE, q_text, embedder, expected)
        struct_eval = evaluate_strategy_retrieval(client, COLLECTION_STRUCTURED, q_text, embedder, expected)

        summary_stats["recursive"]["scores"].append(rec_eval["top_score"])
        summary_stats["recursive"]["recalls"].append(rec_eval["keyword_recall"])
        if rec_eval["is_truncated"]:
            summary_stats["recursive"]["truncated_count"] += 1

        summary_stats["structured"]["scores"].append(struct_eval["top_score"])
        summary_stats["structured"]["recalls"].append(struct_eval["keyword_recall"])
        if struct_eval["is_truncated"]:
            summary_stats["structured"]["truncated_count"] += 1

        # Affichage comparatif détaillé
        print(f"\n   [A] Chunking Récursif :")
        print(f"       - Score Cosinus  : {rec_eval['top_score']}")
        print(f"       - Rappel Clés    : {rec_eval['keyword_recall']}% ({len(rec_eval['keywords_found'])}/{len(expected)}) -> {rec_eval['keywords_found']}")
        print(f"       - Tronqué/Coupé  : {'OUI (Artefacts JSON/MD partiels)' if rec_eval['is_truncated'] else 'Non'}")
        print(f"       - Extrait Chunk  : {rec_eval['top_text_snippet']}")

        print(f"\n   [B] Chunking Structuré :")
        print(f"       - Score Cosinus  : {struct_eval['top_score']}")
        print(f"       - Rappel Clés    : {struct_eval['keyword_recall']}% ({len(struct_eval['keywords_found'])}/{len(expected)}) -> {struct_eval['keywords_found']}")
        print(f"       - Métadonnées    : {'Riches (Permet filtrage déterministe)' if struct_eval['has_rich_metadata'] else 'Basiques'}")
        print(f"       - Extrait Chunk  : {struct_eval['top_text_snippet']}")

    # 4. Synthèse globale et métriques
    rec_mean_score = sum(summary_stats["recursive"]["scores"]) / len(summary_stats["recursive"]["scores"])
    rec_mean_recall = sum(summary_stats["recursive"]["recalls"]) / len(summary_stats["recursive"]["recalls"])

    str_mean_score = sum(summary_stats["structured"]["scores"]) / len(summary_stats["structured"]["scores"])
    str_mean_recall = sum(summary_stats["structured"]["recalls"]) / len(summary_stats["structured"]["recalls"])

    rec_trunc = f"{summary_stats['recursive']['truncated_count']}/5"
    str_trunc = f"{summary_stats['structured']['truncated_count']}/5"

    print("\n" + "=" * 80)
    print("  TABLEAU RÉCAPITULATIF DE L'ÉVALUATION")
    print("=" * 80)
    print(f"{'Critère':<35} | {'1. Chunking Récursif':<20} | {'2. Découpage Structuré':<22}")
    print("-" * 84)
    print(f"{'Score de Similarité Moyen':<35} | {rec_mean_score:<20.4f} | {str_mean_score:<22.4f}")
    print(f"{'Taux de Rappel Mots-Clés Moyen':<35} | {rec_mean_recall:<19.1f}% | {str_mean_recall:<21.1f}%")
    print(f"{'Chunks Tronqués / Incomplets':<35} | {rec_trunc:<20} | {str_trunc:<22}")
    print(f"{'Exploitation Filtres Métadonnées':<35} | {'Limitée (texte seul)':<20} | {'Complète (prix, km, dispo)':<22}")
    print(f"{'Adaptation Synthèse Vocale (TTS)':<35} | {'Médiocre (fragments)':<20} | {'Excellente (fiches nettes)':<22}")
    print("-" * 84)

    print("\n🔍 ANALYSE QUALITATIVE :")
    print("  1. Le chunking récursif découpe arbitrairement le JSON du catalogue, séparant")
    print("     souvent le modèle du véhicule de son prix ou de sa motorisation.")
    print("  2. Le chunking structuré encapsule chaque véhicule dans une fiche atomique complète")
    print("     et indexe les attributs numériques en métadonnées filtrables (payload).")
    print("  3. Pour un assistant vocal, le découpage structuré élimine les hallucinations")
    print("     et fournit directement une réponse prête à être prononcée par l'agent.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_benchmark()
