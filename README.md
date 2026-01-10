# 🏍️ BikerSentinel

BikerSentinel est un moteur d'analyse de données pour **Home Assistant** dédié à la pratique de la moto. Il croise les paramètres physiques du pilote, les caractéristiques de la machine et les données météorologiques pour générer un **"Biker Score"** (0-10) et des indicateurs de sécurité.

---

## 📋 Spécifications Techniques

### 1. Paramètres d'Entrée (Configuration Pilote & Machine)
* **Morphologie (SCx) :** Calcul de la surface frontale via **taille (cm)** et **poids (kg)** pour l'analyse des échanges thermiques.
* **Sensibilité Thermique :** Curseur de **frilosité** personnelle (ajuste les seuils de malus froid).
* **Équipement (3 niveaux) :** Standard, Hiver ou Chauffant (modulateur d'indice de confort).
* **Type de Machine :** Roadster, Sportive, GT, Trail, Custom (impact sur la protection aérodynamique).
* **Cylindrée :** Mode spécifique **125cc** (ajustement des seuils de vent et vitesse moyenne).

### 2. Algorithme de Calcul (Analyse en 3 Couches)
1. **Couche de Sécurité (Veto) :** Blocage immédiat du score à **0/10** si :
   - Risque de Verglas (Température sol + Humidité).
   - Vent violent (Rafales > 80 km/h).
   - Phénomènes sévères (Orage, Grêle, Neige).
2. **Couche de Confort Dynamique :** Calcul du **Windchill** (refroidissement éolien) combinant vent météo et vitesse de trajet (Urbain/Route/Autoroute), pondéré par le SCx et l'équipement.
3. **Couche de Risque Chaussée :** Analyse de l'historique de pluie (24h) pour détecter les "routes grasses" ou l'aquaplaning.

### 3. Intelligence Embarquée & Notifications
* **Gestion Lumineuse :** Malus de vigilance automatique (Mode Nuit) et alerte d'éblouissement (**Solar Blindness**) selon l'azimut du soleil.
* **Alerte "Retour du Taf" :** Notification prédictive avant l'heure de départ du travail pour anticiper le trajet retour.
* **Gear Advisor :** Suggestion de l'équipement optimal (doublure, type de gants, visière) avant le départ.

---

## 🚀 Roadmap de Développement

### ✅ Phase 1 : Fondations (Version 1.0.0)
- [x] Architecture du `custom_component`.
- [x] Formulaire de configuration (Config Flow) & Entités `Score`/`Statut`.

### 🛠️ Phase 2 : Développement de l'Algorithme (En cours)
- [ ] **Malus de Stabilité :** Impact du vent latéral selon la machine.
- [ ] **Intégration Frilosité/Équipement :** Nouvelles options de calcul dans le moteur.
- [ ] **Mode Nuit & Azimut :** Calcul de visibilité basé sur la position solaire.
- [ ] **Historique Précipitations :** Corrélation avec l'état de la chaussée.

### 🌟 Phase 3 : Fonctionnalités Avancées ("Paroxysme")
- [ ] **Maintenance :** Rappel de graissage de chaîne après pluie et suivi entretien prédictif.
- [ ] **Machine Learning :** Auto-ajustement de la frilosité selon les données réelles de roulage.
- [ ] **Analyse de Coût :** Comparatif financier trajet Moto vs Voiture.
- [ ] **Checklist Roadtrip :** Assistant de préparation dynamique.

---

## 🛠️ Installation
1. Copier le dossier `custom_components/bikersentinel` dans `/config/custom_components/`.
2. Redémarrer Home Assistant.
3. Ajouter l'intégration via l'interface utilisateur.
