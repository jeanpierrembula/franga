# Gestion Financière Personnelle – Version Congolaise

Ce projet est une application Streamlit pour gérer ses finances personnelles, adaptée aux réalités congolaises.  
Il permet de saisir des transactions (entrées et dépenses), d'appliquer des règles de budgétisation automatique et d'analyser les dépenses via des graphiques interactifs.

## Fonctionnalités

- **Entrées et Dépenses Flexibles** : Gestion des transactions en USD et CDF avec conversion dynamique.
- **Budgétisation Automatique** : Répartition automatique de montants le 10 et le 25 du mois.
- **Portefeuille Intelligent** : Suivi en temps réel du solde dans les deux devises.
- **Analyse et Visualisation** : Historique des transactions et graphiques pour visualiser la répartition des dépenses.
- **Stockage Persitant** : Sauvegarde des transactions dans une base de données SQLite via SQLAlchemy.

## Installation

1. Clonez le dépôt Git.
2. Installez l'environnement virtuel (si ce n'est pas déjà fait) et activez-le.
3. Installez les dépendances avec :
   ```bash
   pip install -r requirements.txt
   ```
