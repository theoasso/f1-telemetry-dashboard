# F1 Telemetry Dashboard

Dashboard d'analyse de performance F1 basé sur des données réelles (télémétrie,
timing) via la librairie [FastF1](https://docs.fastf1.dev/).

Projet pensé comme démonstrateur technique pour candidature côté performance /
race strategy dans une écurie de F1.

## Fonctionnalités

- **Comparaison de tours** : delta de temps, vitesse et freinage entre deux
  pilotes sur leur meilleur tour d'une session.
- **Dégradation des pneus** : évolution du temps au tour en fonction de l'âge
  du train de pneus, par type de composé.
- **Rythme de course** : distribution des temps au tour par pilote sur toute
  la session (identifie régularité et rythme réel hors trafic/safety car).

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

Le premier chargement d'une session télécharge les données depuis les serveurs
FastF1 (nécessite une connexion internet) puis les met en cache localement
dans le dossier `f1_cache/` — les chargements suivants sont quasi instantanés.

## Roadmap possible

- Ajout d'une carte du circuit colorée par vitesse/freinage (`session.laps`)
- Détection automatique des relances de safety car / phases de VSC
- Simulateur de stratégie de pit stop (Monte Carlo) branché sur ces mêmes
  données réelles pour valider le modèle sur des courses passées
- Export d'un rapport PDF automatique par Grand Prix
