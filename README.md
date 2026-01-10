# 🏍️ BikerSentinel

BikerSentinel est une intégration pour **Home Assistant** conçue pour les motards. 
Elle calcule un score de sortie de 0 à 10 en fonction de la météo (température, vent, pluie) et de la morphologie du pilote.

## ✨ Fonctionnalités
- **Score Dynamique :** Calcul basé sur le Windchill (ressenti) et la protection de la moto.
- **Morphologie :** Prise en compte de la taille et du poids pour la surface de prise au vent.
- **Sécurité :** Vétos automatiques en cas de neige, grêle ou tempête.

## 🛠️ Installation (Manuel)
1. Copiez le dossier `custom_components/bikersentinel` dans votre dossier `/config/custom_components/`.
2. Redémarrez Home Assistant.
3. Allez dans Paramètres > Appareils et Services > Ajouter l'intégration.
