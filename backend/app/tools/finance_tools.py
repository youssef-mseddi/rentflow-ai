#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Outils de calculs financiers et de tarification automobile pour AutoExpress.
Comprend :
  1. simulate_car_loan : Simulation de crédit auto (mensualité, coût d'intérêt, avertissement légal).
  2. calculate_rental_quote : Chiffrage déterministe de location (éligibilité, options, franchise, caution).
  3. search_catalog : Filtrage déterministe du catalogue selon budget, énergie, kilométrage.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


DISCLAIMER_LEGAL = "Un crédit vous engage et doit être remboursé. Vérifiez vos capacités de remboursement avant de vous engager."


def simulate_car_loan(
    car_price: float,
    down_payment: float = 0.0,
    loan_months: int = 48,
    annual_interest_rate: float = 0.049
) -> Dict[str, Any]:
    """
    Simule un crédit automobile amortissable standard.
    
    Formule mathématique :
      M = (P * r) / (1 - (1 + r)^(-n))
      où :
        P = car_price - down_payment (capital emprunté)
        r = annual_interest_rate / 12 (taux périodique mensuel)
        n = loan_months (durée en mois)
      Coût total des intérêts = (M * n) - P
    
    Args:
        car_price: Prix d'achat du véhicule en euros TTC.
        down_payment: Apport personnel initial en euros (défaut: 0.0).
        loan_months: Durée du prêt en mois (défaut: 48 mois, soit 4 ans).
        annual_interest_rate: Taux d'intérêt nominal annuel (défaut: 4.9% soit 0.049).
        
    Returns:
        Dictionnaire structuré avec le capital emprunté, mensualité, intérêts totaux,
        coût global, et le texte prêt pour la synthèse vocale (TTS).
    """
    if car_price <= 0:
        raise ValueError("Le prix du véhicule doit être strictement positif.")
    if loan_months <= 0:
        raise ValueError("La durée du prêt doit être d'au moins 1 mois.")
    if down_payment < 0:
        raise ValueError("L'apport personnel ne peut pas être négatif.")
    if down_payment >= car_price:
        # Paiement comptant intégral
        return {
            "car_price": round(car_price, 2),
            "down_payment": round(down_payment, 2),
            "borrowed_amount": 0.0,
            "monthly_payment": 0.0,
            "total_interest": 0.0,
            "total_cost": round(car_price, 2),
            "loan_months": loan_months,
            "annual_interest_rate": annual_interest_rate,
            "legal_disclaimer": DISCLAIMER_LEGAL,
            "voice_summary": f"Avec un apport intégral de {int(down_payment)} euros, aucun crédit n'est nécessaire pour ce véhicule de {int(car_price)} euros."
        }

    # Capital principal emprunté
    borrowed_amount = car_price - down_payment

    # Taux mensuel
    monthly_rate = annual_interest_rate / 12.0

    if monthly_rate == 0.0:
        # Prêt à taux zéro
        monthly_payment = borrowed_amount / loan_months
        total_interest = 0.0
    else:
        # Formule classique d'annuité constante
        # M = P * r / (1 - (1+r)^(-n))
        denominator = 1.0 - ((1.0 + monthly_rate) ** (-loan_months))
        monthly_payment = (borrowed_amount * monthly_rate) / denominator
        total_interest = (monthly_payment * loan_months) - borrowed_amount

    total_cost = borrowed_amount + total_interest

    # Synthèse orale concise et fluide (2 phrases adaptées au TTS vocal)
    voice_summary = (
        f"Pour un capital emprunté de {int(round(borrowed_amount))} euros sur {loan_months} mois avec {int(round(down_payment))} euros d'apport, "
        f"votre mensualité est de {round(monthly_payment, 2)} euros par mois au taux de {annual_interest_rate * 100:.1f} pour cent. "
        f"Le coût total des intérêts s'élève à {int(round(total_interest))} euros. {DISCLAIMER_LEGAL}"
    )

    return {
        "car_price": round(car_price, 2),
        "down_payment": round(down_payment, 2),
        "borrowed_amount": round(borrowed_amount, 2),
        "monthly_payment": round(monthly_payment, 2),
        "total_interest": round(total_interest, 2),
        "total_cost": round(total_cost, 2),
        "loan_months": int(loan_months),
        "annual_interest_rate": round(annual_interest_rate, 4),
        "legal_disclaimer": DISCLAIMER_LEGAL,
        "voice_summary": voice_summary
    }


def calculate_rental_quote(
    daily_rate: float,
    rental_days: int,
    driver_age: int = 25,
    license_years: int = 3,
    insurance_type: str = "tous_risques",
    is_premium: bool = False,
    category: str = "Citadine",
    extra_km: int = 0
) -> Dict[str, Any]:
    """
    Calcule un devis de location précis selon les politiques AutoExpress :
      - Vérification d'éligibilité (21 ans & 2 ans permis ; 25 ans & 3 ans si premium)
      - Supplément jeune conducteur (15 €/j si 21-24 ans, max 150 €)
      - Assurance Tiers (inclus) vs Tous Risques (18 €/j ou 28 €/j premium)
      - Caution selon catégorie
    """
    # 1. Validation de l'éligibilité
    min_age = 25 if is_premium else 21
    min_license = 3 if is_premium else 2

    if driver_age < min_age or license_years < min_license:
        rejection_reason = (
            f"Conditions non remplies : {min_age} ans révolus et {min_license} ans de permis "
            f"requis pour cette catégorie (vous avez {driver_age} ans et {license_years} ans de permis)."
        )
        return {
            "eligible": False,
            "rejection_reason": rejection_reason,
            "total_price": 0.0,
            "voice_summary": f"Nous ne pouvons malheureusement pas valider cette location : nos conditions exigent au minimum {min_age} ans et {min_license} ans de permis."
        }

    # 2. Calcul du tarif de base
    base_cost = daily_rate * rental_days

    # 3. Supplément jeune conducteur (21 à 24 ans inclus)
    young_driver_fee = 0.0
    if 21 <= driver_age <= 24:
        young_driver_fee = min(15.0 * rental_days, 150.0)

    # 4. Formule d'assurance
    ins_lower = insurance_type.lower()
    is_full_coverage = ("tous" in ins_lower or "tout" in ins_lower or "risque" in ins_lower or "touriste" in ins_lower)
    
    if is_full_coverage:
        daily_insurance = 28.0 if is_premium else 18.0
        insurance_cost = daily_insurance * rental_days
        franchise_amount = 500.0 if (is_premium or "suv" in category.lower() or "berline" in category.lower()) else 300.0
        insurance_label = "Tous Risques (franchise réduite)"
    else:
        insurance_cost = 0.0
        franchise_amount = 2500.0 if is_premium else (1800.0 if "suv" in category.lower() else 1200.0)
        insurance_label = "Au Tiers (formule de base)"

    # 5. Caution obligatoire selon catégorie
    cat_lower = category.lower()
    if is_premium:
        caution_amount = 2000.0
    elif "citadine" in cat_lower:
        caution_amount = 800.0
    elif "suv" in cat_lower:
        caution_amount = 1500.0 if "hybride" in cat_lower or "familial" in cat_lower else 1000.0
    elif "berline" in cat_lower:
        caution_amount = 1200.0
    else:
        caution_amount = 1200.0

    # 6. Dépassement kilométrique éventuel
    km_cost = extra_km * (0.40 if is_premium else 0.25)

    total_price = base_cost + young_driver_fee + insurance_cost + km_cost

    voice_summary = (
        f"Pour {rental_days} jours de location avec la formule {insurance_label}, "
        f"le tarif total est de {int(round(total_price))} euros. "
        f"Une caution de {int(caution_amount)} euros sous forme d'empreinte bancaire non débitée sera demandée. "
        f"Votre franchise résiduelle est de {int(franchise_amount)} euros."
    )

    return {
        "eligible": True,
        "rental_days": rental_days,
        "daily_rate": daily_rate,
        "base_cost": round(base_cost, 2),
        "young_driver_fee": round(young_driver_fee, 2),
        "insurance_type": insurance_label,
        "insurance_cost": round(insurance_cost, 2),
        "franchise_amount": round(franchise_amount, 2),
        "caution_amount": round(caution_amount, 2),
        "total_price": round(total_price, 2),
        "voice_summary": voice_summary
    }


def search_catalog(
    budget: Optional[float] = None,
    category: Optional[str] = None,
    motorisation: Optional[str] = None,
    max_km: Optional[int] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Recherche déterministe dans le catalogue AutoExpress de véhicules.
    Permet à l'agent commercial de matcher précisément les critères de l'utilisateur.
    """
    catalog_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "vehicles_catalog.json"
    if not catalog_path.exists():
        return []

    with open(catalog_path, "r", encoding="utf-8") as f:
        vehicles = json.load(f)

    results = []
    for v in vehicles:
        # Filtre Catégorie
        if category and category.lower() not in v.get("categorie", "").lower():
            continue
        # Filtre Motorisation
        if motorisation and motorisation.lower() not in v.get("motorisation", "").lower():
            continue
        # Filtre Kilométrage
        if max_km and v.get("kilometrage", 0) > max_km:
            continue
        # Filtre Budget Achat
        if budget and v.get("prix_achat", 0) > budget:
            continue
        
        results.append(v)
        if len(results) >= limit:
            break

    return results


if __name__ == "__main__":
    # Tests unitaires de validation
    print("--- Test simulate_car_loan ---")
    loan = simulate_car_loan(car_price=22000, down_payment=3000, loan_months=48, annual_interest_rate=0.049)
    print(f"Capital: {loan['borrowed_amount']}€ | Mensualité: {loan['monthly_payment']}€/mois | Intérêts: {loan['total_interest']}€")
    print(f"Synthèse vocale: {loan['voice_summary']}")

    print("\n--- Test calculate_rental_quote ---")
    quote = calculate_rental_quote(daily_rate=42, rental_days=3, driver_age=23, license_years=3, insurance_type="tous_risques")
    print(f"Total: {quote['total_price']}€ | Caution: {quote['caution_amount']}€ | Franchise: {quote['franchise_amount']}€")
    print(f"Synthèse vocale: {quote['voice_summary']}")
