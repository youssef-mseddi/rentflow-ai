#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de catalogue de véhicules réaliste pour le marché français (525+ véhicules).
Respecte strictement les quotas :
  - Citadines (25% -> 132 véhicules)
  - SUV (35% -> 184 véhicules)
  - Berlines (25% -> 132 véhicules)
  - Utilitaires / Monospaces (15% -> 79 véhicules)
Total : 527 véhicules.

Chaque entrée respecte rigoureusement la structure demandée :
  id, modele, categorie, motorisation, boite, annee, kilometrage,
  tarif_journalier_location, prix_achat, disponibilite, consommation,
  equipements, caution.
"""

import json
import random
from pathlib import Path

random.seed(42)  # Reproductibilité

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "vehicles_catalog.json"

# Listes d'équipements disponibles
ALL_EQUIPMENTS = [
    "Apple CarPlay & Android Auto", "Caméra de recul", "Climatisation automatique",
    "Régulateur de vitesse adaptatif", "Aide au stationnement 360°", "Sièges chauffants",
    "Navigation GPS connectée", "Phares Full LED", "Toit ouvrant panoramique",
    "Accès et démarrage mains libres", "Alerte de franchissement de ligne",
    "Freinage d'urgence autonome", "Chargeur smartphone par induction",
    "Système audio Premium", "Hayon motorisé mains libres", "Volant cuir multifonctions",
    "Attelage de remorque", "Détecteur d'angle mort", "Jantes alliage 17 pouces",
    "Affichage tête haute", "Suspension pilotée", "Vitres arrière surteintées"
]

# Définition des profils de modèles par catégorie
CITADINES_CONFIGS = [
    # Économique
    ("Peugeot 208 1.2 PureTech 75 Like", "Citadine", "Essence", "Manuelle", 5.1, (35, 42), (12500, 15500), 800),
    ("Peugeot 208 1.2 PureTech 100 Allure", "Citadine", "Essence", "Manuelle", 5.2, (40, 46), (15000, 18500), 800),
    ("Peugeot 208 1.2 PureTech 100 EAT8 GT", "Citadine", "Essence", "Automatique", 5.4, (45, 52), (17500, 21000), 800),
    ("Peugeot 208 1.5 BlueHDi 100 Allure", "Citadine", "Diesel", "Manuelle", 4.2, (42, 48), (15500, 19000), 800),
    ("Peugeot 208 Hybrid 100 e-DCS6 Allure", "Citadine", "Hybride", "Automatique", 4.5, (46, 54), (18000, 22000), 800),
    ("Peugeot e-208 136ch GT", "Citadine", "100% Électrique", "Automatique", "15.4 kWh/100km (362 km WLTP)", (50, 60), (20000, 25000), 800),
    ("Renault Clio V 1.0 SCe 65 Authentic", "Citadine", "Essence", "Manuelle", 5.1, (34, 40), (11800, 14500), 800),
    ("Renault Clio V 1.0 TCe 90 Evolution", "Citadine", "Essence", "Manuelle", 5.2, (38, 45), (13800, 16800), 800),
    ("Renault Clio V 1.0 TCe 100 GPL Techno", "Citadine", "Essence", "Manuelle", 6.8, (39, 45), (14500, 17500), 800),
    ("Renault Clio V 1.5 Blue dCi 100 Techno", "Citadine", "Diesel", "Manuelle", 4.1, (42, 48), (15200, 18800), 800),
    ("Renault Clio V E-Tech Hybride 145 Esprit Alpine", "Citadine", "Hybride", "Automatique", 4.2, (48, 56), (18500, 23000), 800),
    ("Dacia Sandero III 1.0 SCe 65 Essential", "Citadine", "Essence", "Manuelle", 5.3, (30, 36), (10500, 13000), 800),
    ("Dacia Sandero III 1.0 TCe 90 Expression", "Citadine", "Essence", "Manuelle", 5.2, (33, 39), (12000, 14800), 800),
    ("Dacia Sandero Stepway Eco-G 100 Expression", "Citadine", "Essence", "Manuelle", 6.5, (36, 42), (13500, 16500), 800),
    ("Toyota Yaris 1.0 VVT-i 70 Dynamic", "Citadine", "Essence", "Manuelle", 5.0, (36, 42), (13000, 16000), 800),
    ("Toyota Yaris 1.5 Hybride 116h Dynamic", "Citadine", "Hybride", "Automatique", 3.8, (45, 52), (17000, 20500), 800),
    ("Toyota Yaris 1.5 Hybride 130h Collection", "Citadine", "Hybride", "Automatique", 4.0, (50, 58), (19500, 23500), 800),
    ("Citroën C3 1.2 PureTech 83 Feel", "Citadine", "Essence", "Manuelle", 5.4, (33, 39), (11500, 14200), 800),
    ("Citroën C3 1.2 PureTech 110 Shine EAT6", "Citadine", "Essence", "Automatique", 5.6, (40, 47), (14500, 17800), 800),
    ("Citroën ë-C3 Électrique 113ch You", "Citadine", "100% Électrique", "Automatique", "16.0 kWh/100km (320 km WLTP)", (42, 50), (17500, 21500), 800),
    ("Renault Twingo III 1.0 SCe 65 Zen", "Citadine", "Essence", "Manuelle", 5.2, (30, 36), (9800, 12500), 800),
    ("Renault Twingo E-Tech Électrique 82ch", "Citadine", "100% Électrique", "Automatique", "15.0 kWh/100km (190 km WLTP)", (38, 45), (14000, 17500), 800),
    ("Fiat 500 1.0 Hybrid 70 Dolcevita", "Citadine", "Hybride", "Manuelle", 4.6, (36, 43), (12800, 15800), 800),
    ("Fiat 500e Électrique 95ch Action", "Citadine", "100% Électrique", "Automatique", "13.0 kWh/100km (190 km WLTP)", (42, 49), (16000, 19500), 800),
    ("Fiat 500e Électrique 118ch La Prima", "Citadine", "100% Électrique", "Automatique", "14.4 kWh/100km (320 km WLTP)", (49, 58), (19500, 24000), 800),
    ("Volkswagen Polo 1.0 TSI 95 Life DSG7", "Citadine", "Essence", "Automatique", 5.3, (44, 52), (16800, 20500), 800),
    ("Volkswagen Polo 1.0 TSI 110 R-Line DSG7", "Citadine", "Essence", "Automatique", 5.5, (48, 56), (19000, 23000), 800),
    ("Opel Corsa 1.2 75ch Edition", "Citadine", "Essence", "Manuelle", 5.3, (34, 40), (12000, 14500), 800),
    ("Opel Corsa Hybrid 100 e-DCT GS", "Citadine", "Hybride", "Automatique", 4.6, (44, 51), (17000, 20800), 800),
    ("Opel Corsa-e 136ch Elegance", "Citadine", "100% Électrique", "Automatique", "15.5 kWh/100km (357 km WLTP)", (48, 56), (19000, 23500), 800),
    ("Seat Ibiza 1.0 TSI 110 FR", "Citadine", "Essence", "Manuelle", 5.2, (41, 48), (15000, 18500), 800),
    ("Skoda Fabia 1.0 TSI 95 Ambition", "Citadine", "Essence", "Manuelle", 5.1, (36, 43), (13500, 16800), 800),
    ("Mini Cooper 1.5 136ch Classic", "Citadine", "Essence", "Automatique", 5.7, (52, 62), (21000, 26000), 800),
    ("Mini Cooper SE Électrique 184ch Resolute", "Citadine", "100% Électrique", "Automatique", "15.8 kWh/100km (234 km WLTP)", (58, 68), (23000, 28500), 800),
    ("Dacia Spring 65 Extreme", "Citadine", "100% Électrique", "Automatique", "13.9 kWh/100km (220 km WLTP)", (32, 38), (11500, 14500), 800),
    ("Hyundai i20 1.0 T-GDi 100 Hybrid 48V N Line", "Citadine", "Hybride", "Manuelle", 4.9, (42, 49), (15500, 19200), 800),
    ("Kia Rio 1.0 T-GDi 100 MHEV GT Line", "Citadine", "Hybride", "Automatique", 4.8, (42, 49), (15200, 18900), 800),
]

SUV_CONFIGS = [
    # Économique & Compact
    ("Dacia Duster 1.0 Eco-G 100 Expression", "SUV", "Essence", "Manuelle", 6.8, (39, 46), (14500, 17800), 1000),
    ("Dacia Duster 1.5 dCi 115 4x4 Journey", "SUV", "Diesel", "Manuelle", 5.3, (46, 54), (17000, 21500), 1000),
    ("Dacia Duster 1.3 TCe 130 4x2 Extreme", "SUV", "Essence", "Manuelle", 6.2, (44, 52), (16500, 20500), 1000),
    ("Dacia Duster Hybrid 140 Journey", "SUV", "Hybride", "Automatique", 4.9, (52, 60), (20000, 24500), 1000),
    ("Renault Captur 1.0 TCe 90 Equilibre", "SUV", "Essence", "Manuelle", 5.8, (42, 50), (16000, 19500), 1000),
    ("Renault Captur TCe 140 MHEV Techno", "SUV", "Hybride", "Manuelle", 5.7, (48, 56), (18500, 22500), 1000),
    ("Renault Captur E-Tech Hybride 145 Esprit Alpine", "SUV", "Hybride", "Automatique", 4.7, (55, 64), (21500, 26000), 1000),
    ("Renault Captur E-Tech Plug-in 160 Intens", "SUV", "Hybride Rechargeable", "Automatique", "1.4L/100km (50 km élec)", (62, 72), (23000, 28000), 1500),
    ("Peugeot 2008 1.2 PureTech 100 Active", "SUV", "Essence", "Manuelle", 5.5, (44, 52), (16500, 20000), 1000),
    ("Peugeot 2008 1.2 PureTech 130 EAT8 Allure", "SUV", "Essence", "Automatique", 5.9, (52, 60), (19500, 24000), 1000),
    ("Peugeot 2008 1.5 BlueHDi 130 EAT8 GT", "SUV", "Diesel", "Automatique", 4.9, (56, 65), (21000, 25500), 1000),
    ("Peugeot 2008 Hybrid 136 e-DCS6 Allure", "SUV", "Hybride", "Automatique", 4.9, (58, 67), (22500, 27000), 1000),
    ("Peugeot e-2008 156ch GT", "SUV", "100% Électrique", "Automatique", "15.3 kWh/100km (406 km WLTP)", (65, 76), (25000, 31000), 1500),
    ("Toyota Yaris Cross 1.5 Hybride 116h Dynamic", "SUV", "Hybride", "Automatique", 4.4, (49, 58), (19000, 23500), 1000),
    ("Toyota Yaris Cross 1.5 Hybride 130h GR Sport AWD-i", "SUV", "Hybride", "Automatique", 4.8, (58, 68), (23500, 28500), 1000),
    ("Citroën C3 Aircross 1.2 PureTech 110 Shine", "SUV", "Essence", "Manuelle", 6.0, (42, 50), (15000, 18500), 1000),
    ("Volkswagen T-Cross 1.0 TSI 95 Life", "SUV", "Essence", "Manuelle", 5.6, (45, 53), (16800, 20500), 1000),
    ("Volkswagen T-Roc 1.5 TSI 150 DSG7 R-Line", "SUV", "Essence", "Automatique", 6.1, (62, 72), (24000, 29500), 1000),
    ("Volkswagen T-Roc 2.0 TDI 150 DSG7 Lounge", "SUV", "Diesel", "Automatique", 5.0, (59, 69), (22500, 28000), 1000),
    ("Hyundai Kona 1.0 T-GDi 120 Intuitive", "SUV", "Essence", "Manuelle", 5.8, (46, 54), (17500, 21500), 1000),
    ("Hyundai Kona Hybrid 141 N Line Executive", "SUV", "Hybride", "Automatique", 4.7, (58, 68), (23500, 29000), 1000),
    ("Hyundai Kona Electric 65 kWh 217ch", "SUV", "100% Électrique", "Automatique", "14.9 kWh/100km (514 km WLTP)", (68, 78), (27000, 34000), 1500),
    ("Nissan Juke 1.0 DIG-T 114 N-Connecta", "SUV", "Essence", "Manuelle", 5.8, (43, 51), (16500, 20200), 1000),
    ("Ford Puma 1.0 EcoBoost 125 mHEV Titanium", "SUV", "Hybride", "Manuelle", 5.4, (45, 53), (17000, 21000), 1000),
    # Milieu de gamme
    ("Peugeot 3008 1.2 PureTech 130 EAT8 Allure", "SUV", "Essence", "Automatique", 6.4, (60, 70), (22000, 27500), 1500),
    ("Peugeot 3008 1.5 BlueHDi 130 EAT8 GT", "SUV", "Diesel", "Automatique", 5.2, (64, 75), (23500, 29000), 1500),
    ("Peugeot 3008 Hybrid 136 e-DCS6 Allure", "SUV", "Hybride", "Automatique", 5.5, (66, 76), (25000, 31000), 1500),
    ("Peugeot 3008 PHEV 225 e-EAT8 GT", "SUV", "Hybride Rechargeable", "Automatique", "1.5L/100km (56 km élec)", (74, 86), (27500, 34500), 1500),
    ("Peugeot e-3008 210ch Allure 73 kWh", "SUV", "100% Électrique", "Automatique", "16.8 kWh/100km (527 km WLTP)", (85, 98), (34000, 42000), 1500),
    ("Renault Austral E-Tech Hybride 200 Iconic", "SUV", "Hybride", "Automatique", 4.6, (72, 84), (28000, 35000), 1500),
    ("Renault Arkana E-Tech Hybride 145 RS Line", "SUV", "Hybride", "Automatique", 4.8, (59, 69), (22500, 28000), 1500),
    ("Nissan Qashqai 1.3 DIG-T 158 Xtronic N-Connecta", "SUV", "Hybride", "Automatique", 6.3, (58, 68), (22000, 27500), 1500),
    ("Nissan Qashqai e-Power 190 Tekna", "SUV", "Hybride", "Automatique", 5.3, (68, 79), (26500, 33000), 1500),
    ("Hyundai Tucson 1.6 T-GDi Hybrid 230 N Line", "SUV", "Hybride", "Automatique", 5.6, (75, 88), (29000, 36000), 1500),
    ("Hyundai Tucson 1.6 Plug-in 265 HTRAC Executive", "SUV", "Hybride Rechargeable", "Automatique", "1.4L/100km (62 km élec)", (86, 99), (34000, 42000), 1500),
    ("Kia Sportage 1.6 T-GDi Hybrid 230 GT-line", "SUV", "Hybride", "Automatique", 5.7, (74, 86), (28500, 35500), 1500),
    ("Citroën C5 Aircross Plug-in Hybrid 225 Shine", "SUV", "Hybride Rechargeable", "Automatique", "1.5L/100km (55 km élec)", (72, 84), (26000, 33000), 1500),
    ("Toyota RAV4 2.5 Hybride 218h Dynamic", "SUV", "Hybride", "Automatique", 5.6, (75, 88), (29000, 36500), 1500),
    ("Toyota RAV4 Plug-in 306h AWD Collection", "SUV", "Hybride Rechargeable", "Automatique", "1.0L/100km (75 km élec)", (95, 110), (37000, 46000), 1500),
    ("Volkswagen Tiguan 2.0 TDI 150 DSG7 Elegance", "SUV", "Diesel", "Automatique", 5.5, (76, 89), (29500, 37000), 1500),
    ("Volkswagen Tiguan eHybrid 204 DSG6 R-Line", "SUV", "Hybride Rechargeable", "Automatique", "1.6L/100km (50 km élec)", (88, 102), (35000, 44000), 1500),
    # Premium
    ("Audi Q3 35 TFSI S tronic S line", "SUV", "Essence", "Automatique", 6.6, (82, 95), (32000, 40000), 2000),
    ("Audi Q3 45 TFSIe PHEV 245 S line", "SUV", "Hybride Rechargeable", "Automatique", "1.6L/100km (51 km élec)", (95, 112), (37000, 47000), 2000),
    ("Audi Q5 40 TDI 204 quattro S tronic", "SUV", "Diesel", "Automatique", 6.4, (105, 125), (42000, 54000), 2000),
    ("BMW X1 sDrive18d 150ch M Sport", "SUV", "Diesel", "Automatique", 5.0, (84, 98), (34000, 42500), 2000),
    ("BMW X1 xDrive25e 245ch PHEV xLine", "SUV", "Hybride Rechargeable", "Automatique", "1.1L/100km (80 km élec)", (98, 115), (39000, 49000), 2000),
    ("BMW iX1 xDrive30 313ch M Sport", "SUV", "100% Électrique", "Automatique", "17.2 kWh/100km (438 km WLTP)", (108, 128), (44000, 55000), 2000),
    ("BMW X3 xDrive20d 190ch M Sport", "SUV", "Diesel", "Automatique", 6.2, (110, 132), (45000, 58000), 2000),
    ("Mercedes GLA 200d AMG Line 8G-DCT", "SUV", "Diesel", "Automatique", 5.3, (88, 104), (35000, 44000), 2000),
    ("Mercedes GLA 250e PHEV 218ch AMG Line", "SUV", "Hybride Rechargeable", "Automatique", "1.3L/100km (63 km élec)", (98, 116), (39500, 50000), 2000),
    ("Mercedes GLC 220d 4MATIC AMG Line", "SUV", "Diesel", "Automatique", 5.8, (120, 145), (49000, 64000), 2000),
    ("Mercedes GLC 300de PHEV 4MATIC AMG Line", "SUV", "Hybride Rechargeable", "Automatique", "0.6L/100km (120 km élec)", (135, 160), (56000, 72000), 2000),
    ("Tesla Model Y Propulsion", "SUV", "100% Électrique", "Automatique", "15.7 kWh/100km (455 km WLTP)", (85, 98), (35000, 43000), 1500),
    ("Tesla Model Y Grande Autonomie AWD", "SUV", "100% Électrique", "Automatique", "16.9 kWh/100km (533 km WLTP)", (98, 118), (42000, 52000), 2000),
    ("Porsche Macan 2.0 PDK 265ch", "SUV", "Essence", "Automatique", 10.1, (160, 195), (62000, 78000), 2000),
    ("Porsche Macan Électrique 4 408ch", "SUV", "100% Électrique", "Automatique", "18.5 kWh/100km (613 km WLTP)", (190, 230), (78000, 96000), 2000),
    ("Volvo XC40 B4 197ch Ultimate", "SUV", "Hybride", "Automatique", 6.8, (82, 96), (33000, 41000), 2000),
    ("Volvo XC60 T6 Recharge PHEV 350ch Inscription", "SUV", "Hybride Rechargeable", "Automatique", "1.2L/100km (78 km élec)", (115, 138), (47000, 60000), 2000),
]

BERLINES_CONFIGS = [
    # Économique & Compacte
    ("Renault Megane IV 1.3 TCe 140 Techno", "Berline", "Essence", "Manuelle", 5.7, (48, 56), (17000, 21500), 1200),
    ("Renault Megane IV 1.5 Blue dCi 115 EDC", "Berline", "Diesel", "Automatique", 4.6, (52, 60), (18500, 23000), 1200),
    ("Renault Megane E-Tech EV60 220ch Iconic", "Berline", "100% Électrique", "Automatique", "16.1 kWh/100km (450 km WLTP)", (68, 79), (28000, 35000), 1200),
    ("Peugeot 308 1.2 PureTech 130 Allure", "Berline", "Essence", "Manuelle", 5.5, (50, 58), (19000, 24000), 1200),
    ("Peugeot 308 1.5 BlueHDi 130 EAT8 GT", "Berline", "Diesel", "Automatique", 4.7, (58, 67), (22000, 27500), 1200),
    ("Peugeot 308 PHEV 180 e-EAT8 GT", "Berline", "Hybride Rechargeable", "Automatique", "1.2L/100km (60 km élec)", (66, 77), (25000, 31500), 1200),
    ("Peugeot e-308 156ch GT 54 kWh", "Berline", "100% Électrique", "Automatique", "15.0 kWh/100km (413 km WLTP)", (70, 82), (27500, 34500), 1200),
    ("Citroën C4 1.2 PureTech 130 EAT8 Shine", "Berline", "Essence", "Automatique", 5.8, (48, 56), (17500, 22000), 1200),
    ("Citroën ë-C4 Électrique 136ch Shine", "Berline", "100% Électrique", "Automatique", "15.3 kWh/100km (357 km WLTP)", (55, 64), (20500, 26000), 1200),
    ("Volkswagen Golf 8 1.5 eTSI 150 DSG7 Life", "Berline", "Hybride", "Automatique", 5.5, (59, 69), (22500, 28000), 1200),
    ("Volkswagen Golf 8 2.0 TDI 150 DSG7 R-Line", "Berline", "Diesel", "Automatique", 4.7, (64, 75), (24500, 31000), 1200),
    ("Volkswagen Golf 8 GTE 245ch PHEV", "Berline", "Hybride Rechargeable", "Automatique", "1.2L/100km (62 km élec)", (76, 89), (29000, 37000), 1200),
    ("Toyota Corolla 1.8 Hybride 140h Design", "Berline", "Hybride", "Automatique", 4.4, (54, 62), (20500, 25500), 1200),
    ("Toyota Corolla 2.0 Hybride 196h GR Sport", "Berline", "Hybride", "Automatique", 4.6, (62, 72), (24000, 30000), 1200),
    ("Seat Leon 1.5 eTSI 150 DSG7 FR", "Berline", "Hybride", "Automatique", 5.6, (52, 61), (19500, 24500), 1200),
    ("Skoda Octavia 2.0 TDI 150 DSG7 Style", "Berline", "Diesel", "Automatique", 4.6, (58, 68), (22000, 28000), 1200),
    ("MG4 Electric 64 kWh 204ch Luxury", "Berline", "100% Électrique", "Automatique", "16.0 kWh/100km (435 km WLTP)", (52, 60), (19000, 24500), 1200),
    # Familiale & Routière
    ("Peugeot 508 1.5 BlueHDi 130 EAT8 GT", "Berline", "Diesel", "Automatique", 4.9, (65, 76), (24000, 30500), 1200),
    ("Peugeot 508 PHEV 225 e-EAT8 Allure", "Berline", "Hybride Rechargeable", "Automatique", "1.4L/100km (55 km élec)", (75, 88), (28000, 36000), 1200),
    ("Citroën C5 X Plug-in Hybrid 225 Shine Pack", "Berline", "Hybride Rechargeable", "Automatique", "1.3L/100km (60 km élec)", (78, 92), (29000, 38000), 1200),
    ("Skoda Superb 2.0 TDI 150 DSG7 Laurin & Klement", "Berline", "Diesel", "Automatique", 4.9, (74, 88), (28500, 37000), 1200),
    # Premium
    ("BMW Série 1 118i 136ch M Sport", "Berline", "Essence", "Automatique", 6.0, (68, 79), (25500, 32500), 2000),
    ("BMW Série 1 118d 150ch M Sport", "Berline", "Diesel", "Automatique", 4.9, (72, 84), (27000, 34500), 2000),
    ("BMW Série 3 320d 190ch M Sport", "Berline", "Diesel", "Automatique", 5.1, (89, 105), (36000, 46000), 2000),
    ("BMW Série 3 330e PHEV 292ch M Sport", "Berline", "Hybride Rechargeable", "Automatique", "1.4L/100km (60 km élec)", (98, 118), (41000, 52000), 2000),
    ("BMW i4 eDrive40 340ch M Sport", "Berline", "100% Électrique", "Automatique", "16.8 kWh/100km (590 km WLTP)", (120, 142), (49000, 62000), 2000),
    ("BMW Série 5 520d 197ch M Sport", "Berline", "Diesel", "Automatique", 5.3, (125, 148), (52000, 67000), 2000),
    ("Mercedes Classe A 200 Progressive Line", "Berline", "Essence", "Automatique", 6.0, (68, 79), (26000, 33000), 2000),
    ("Mercedes Classe A 250e PHEV 218ch AMG Line", "Berline", "Hybride Rechargeable", "Automatique", "1.1L/100km (74 km élec)", (80, 94), (31000, 39500), 2000),
    ("Mercedes Classe CLA 220d AMG Line 8G-DCT", "Berline", "Diesel", "Automatique", 5.1, (86, 102), (34000, 43000), 2000),
    ("Mercedes Classe C 200 EQ Boost AMG Line", "Berline", "Hybride", "Automatique", 6.4, (98, 116), (41000, 52000), 2000),
    ("Mercedes Classe C 220d AMG Line 9G-Tronic", "Berline", "Diesel", "Automatique", 4.9, (102, 120), (43000, 54000), 2000),
    ("Mercedes Classe C 300e PHEV 313ch AMG Line", "Berline", "Hybride Rechargeable", "Automatique", "0.6L/100km (115 km élec)", (115, 136), (48000, 61000), 2000),
    ("Audi A3 Sportback 35 TFSI 150 S tronic S line", "Berline", "Hybride", "Automatique", 5.6, (72, 85), (28000, 35500), 2000),
    ("Audi A3 Sportback 40 TFSIe PHEV 204 S line", "Berline", "Hybride Rechargeable", "Automatique", "1.2L/100km (65 km élec)", (82, 96), (32000, 41000), 2000),
    ("Audi A4 35 TDI 163 S tronic S line", "Berline", "Diesel", "Automatique", 5.0, (85, 100), (33000, 42000), 2000),
    ("Audi A4 40 TDI 204 quattro S line", "Berline", "Diesel", "Automatique", 5.4, (96, 114), (38000, 48000), 2000),
    ("Audi A6 40 TDI 204 S tronic Avus", "Berline", "Diesel", "Automatique", 5.6, (120, 145), (49000, 63000), 2000),
    ("Tesla Model 3 Propulsion", "Berline", "100% Électrique", "Automatique", "14.4 kWh/100km (491 km WLTP)", (75, 88), (31000, 38500), 1500),
    ("Tesla Model 3 Grande Autonomie AWD", "Berline", "100% Électrique", "Automatique", "15.2 kWh/100km (629 km WLTP)", (92, 110), (38000, 48000), 2000),
    ("Polestar 2 Long Range Single Motor", "Berline", "100% Électrique", "Automatique", "15.8 kWh/100km (655 km WLTP)", (95, 112), (39000, 49000), 2000),
]

UTILITAIRES_CONFIGS = [
    # Monospaces & Ludospaces
    ("Renault Kangoo 1.3 TCe 100 Equilibre", "Utilitaire", "Essence", "Manuelle", 6.8, (46, 54), (17500, 22000), 1200),
    ("Renault Kangoo 1.5 Blue dCi 95 Techno", "Utilitaire", "Diesel", "Manuelle", 5.2, (52, 60), (19500, 24500), 1200),
    ("Citroën Berlingo 1.5 BlueHDi 100 Feel", "Utilitaire", "Diesel", "Manuelle", 5.3, (50, 58), (18500, 23500), 1200),
    ("Citroën ë-Berlingo 136ch Shine 50 kWh", "Utilitaire", "100% Électrique", "Automatique", "19.5 kWh/100km (280 km WLTP)", (60, 72), (23000, 29000), 1200),
    ("Peugeot Rifter 1.5 BlueHDi 130 EAT8 GT", "Utilitaire", "Diesel", "Automatique", 5.5, (59, 69), (22500, 28000), 1200),
    ("Dacia Jogger Eco-G 100 7 places Expression", "Utilitaire", "Essence", "Manuelle", 7.6, (44, 52), (16000, 19800), 1000),
    ("Dacia Jogger Hybrid 140 Extreme 7 places", "Utilitaire", "Hybride", "Automatique", 4.9, (55, 64), (21000, 25800), 1200),
    ("Volkswagen Caddy 2.0 TDI 122 DSG7 Life", "Utilitaire", "Diesel", "Automatique", 5.4, (64, 75), (25000, 31500), 1200),
    ("Renault Grand Scenic IV 1.3 TCe 140 Zen", "Utilitaire", "Essence", "Manuelle", 6.6, (52, 60), (18000, 23000), 1200),
    ("Citroën Grand C4 Spacetourer 1.5 BlueHDi 130 Shine", "Utilitaire", "Diesel", "Automatique", 5.2, (58, 68), (21000, 26500), 1200),
    # Fourgons & Utilitaires professionnels
    ("Renault Kangoo Van 1.5 Blue dCi 95 Grand Confort", "Utilitaire", "Diesel", "Manuelle", 5.1, (48, 56), (16500, 21000), 1200),
    ("Renault Kangoo Van E-Tech 120ch Électrique", "Utilitaire", "100% Électrique", "Automatique", "18.2 kWh/100km (300 km WLTP)", (58, 68), (22000, 27500), 1200),
    ("Renault Trafic III 2.0 Blue dCi 130 L1H1 Grand Confort", "Utilitaire", "Diesel", "Manuelle", 6.8, (68, 80), (24500, 31000), 1500),
    ("Renault Trafic III 2.0 Blue dCi 150 EDC L2H1", "Utilitaire", "Diesel", "Automatique", 7.1, (78, 92), (28000, 35500), 1500),
    ("Renault Master III 2.3 dCi 135 L2H2 Grand Confort", "Utilitaire", "Diesel", "Manuelle", 8.4, (85, 102), (27000, 35000), 1500),
    ("Peugeot Partner 1.5 BlueHDi 100 Premium Standard", "Utilitaire", "Diesel", "Manuelle", 5.2, (49, 57), (16800, 21500), 1200),
    ("Peugeot Expert 2.0 BlueHDi 145 Standard Premium Pack", "Utilitaire", "Diesel", "Manuelle", 6.9, (72, 85), (26000, 33000), 1500),
    ("Peugeot e-Expert 75 kWh 136ch Standard", "Utilitaire", "100% Électrique", "Automatique", "23.5 kWh/100km (330 km WLTP)", (85, 102), (31000, 39500), 1500),
    ("Peugeot Boxer 2.2 BlueHDi 140 335 L2H2 Pro", "Utilitaire", "Diesel", "Manuelle", 8.6, (88, 105), (28500, 36500), 1500),
    ("Citroën Jumpy 2.0 BlueHDi 145 M Club", "Utilitaire", "Diesel", "Manuelle", 6.8, (70, 83), (25500, 32500), 1500),
    ("Ford Transit Custom 2.0 EcoBlue 136ch L1H1 Trend", "Utilitaire", "Diesel", "Manuelle", 7.2, (74, 88), (27000, 34500), 1500),
    ("Ford Transit Custom PHEV 232ch L1H1 Titanium", "Utilitaire", "Hybride Rechargeable", "Automatique", "2.1L/100km (54 km élec)", (89, 105), (34000, 43000), 1500),
    ("Mercedes Vito 114 CDI Long Pro 9G-Tronic", "Utilitaire", "Diesel", "Automatique", 7.0, (88, 106), (32000, 41000), 1500),
    ("Mercedes Sprinter 315 CDI Fourgon Moyen Toit Haut", "Utilitaire", "Diesel", "Manuelle", 8.9, (105, 128), (38000, 49000), 1500),
    ("Volkswagen Transporter 2.0 TDI 150 DSG7 L1H1 Business", "Utilitaire", "Diesel", "Automatique", 7.3, (85, 102), (31000, 39500), 1500),
    ("Fiat Ducato 2.2 Multijet 140 35 L2H2 Easy Pro", "Utilitaire", "Diesel", "Manuelle", 8.5, (86, 104), (27500, 35500), 1500),
]


def generate_vehicle_instances(category_name: str, configs: list, count: int, start_idx: int) -> list:
    """Génère un nombre précis d'instances variées et réalistes à partir d'une liste de configurations."""
    instances = []
    
    # Répétition cyclique avec variation réaliste
    for i in range(count):
        idx = start_idx + i
        config = configs[i % len(configs)]
        (name, cat, motorisation, boite, conso, (min_rent, max_rent), (min_buy, max_buy), base_caution) = config
        
        # Année récente (2020-2024)
        annee = random.choices([2020, 2021, 2022, 2023, 2024], weights=[10, 15, 30, 30, 15])[0]
        
        # Kilométrage réaliste en fonction de l'âge
        age = 2024 - annee
        base_km = age * random.randint(10000, 18000) + random.randint(2000, 8000)
        km = min(max(base_km, 4500), 115000)
        # Arrondi aux 100 km les plus proches
        km = round(km / 100) * 100
        
        # Tarif journalier avec légère variation
        rent_rate = random.randint(min_rent, max_rent)
        
        # Prix d'achat d'occasion corrélé à l'âge et au kilométrage
        discount_factor = 1.0 - (age * 0.08) - (km / 250000 * 0.15)
        discount_factor = max(discount_factor, 0.60)
        buy_price = int(random.randint(min_buy, max_buy) * discount_factor)
        buy_price = round(buy_price / 100) * 100

        # Disponibilité réaliste
        dispo = random.choices(["disponible", "loué", "réservé"], weights=[75, 15, 10])[0]

        # Consommation sous forme de chaîne
        if isinstance(conso, (int, float)):
            conso_str = f"{conso:.1f}L/100km"
        else:
            conso_str = str(conso)

        # 3 à 5 équipements sélectionnés
        k_equip = random.randint(3, 5)
        equipements = random.sample(ALL_EQUIPMENTS, k_equip)

        # ID formaté VEH-001, VEH-002...
        veh_id = f"VEH-{idx:03d}"

        instances.append({
            "id": veh_id,
            "modele": name,
            "categorie": cat,
            "motorisation": motorisation,
            "boite": boite,
            "annee": annee,
            "kilometrage": km,
            "tarif_journalier_location": rent_rate,
            "prix_achat": buy_price,
            "disponibilite": dispo,
            "consommation": conso_str,
            "equipements": equipements,
            "caution": base_caution
        })

    return instances


def main():
    # Quotas demandés : Citadines 25%, SUV 35%, Berlines 25%, Utilitaires 15%
    # Total = 527 véhicules
    count_citadines = 132    # ~25.0%
    count_suv = 184          # ~34.9%
    count_berlines = 132     # ~25.0%
    count_utilitaires = 79   # ~15.0%

    total_target = count_citadines + count_suv + count_berlines + count_utilitaires
    print(f"Génération de {total_target} véhicules équilibrés...")

    citadines = generate_vehicle_instances("Citadine", CITADINES_CONFIGS, count_citadines, 1)
    suvs = generate_vehicle_instances("SUV", SUV_CONFIGS, count_suv, 1 + count_citadines)
    berlines = generate_vehicle_instances("Berline", BERLINES_CONFIGS, count_berlines, 1 + count_citadines + count_suv)
    utilitaires = generate_vehicle_instances("Utilitaire", UTILITAIRES_CONFIGS, count_utilitaires, 1 + count_citadines + count_suv + count_berlines)

    all_vehicles = citadines + suvs + berlines + utilitaires

    # Mélange contrôlé pour éviter que tous les modèles identiques soient consécutifs
    # tout en réattribuant les IDs dans l'ordre séquentiel
    random.shuffle(all_vehicles)
    for idx, v in enumerate(all_vehicles, start=1):
        v["id"] = f"VEH-{idx:03d}"

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_vehicles, f, indent=2, ensure_ascii=False)

    print(f"[+] Catalogue enregistré avec succès dans {OUTPUT_FILE}")
    print(f"[+] Total véhicules : {len(all_vehicles)}")

    # Vérification des proportions
    cat_counts = {}
    mot_counts = {}
    for v in all_vehicles:
        cat_counts[v["categorie"]] = cat_counts.get(v["categorie"], 0) + 1
        mot_counts[v["motorisation"]] = mot_counts.get(v["motorisation"], 0) + 1

    print("\nRépartition par Catégorie :")
    for cat, c in cat_counts.items():
        print(f"  - {cat:<22}: {c:>3} ({c / len(all_vehicles) * 100:.1f}%)")

    print("\nRépartition par Motorisation :")
    for mot, c in mot_counts.items():
        print(f"  - {mot:<22}: {c:>3} ({c / len(all_vehicles) * 100:.1f}%)")


if __name__ == "__main__":
    main()
