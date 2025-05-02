# F1 Data Generator

Ce projet génère des données de télémétrie F1 en temps réel basées sur des données historiques et les envoie à un système FIWARE.

## Prérequis

- Docker
- Docker Compose
- Python 3.10+

## Configuration

1. Copiez le fichier `.env.example` vers `.env` et configurez vos variables:
```bash
cp f1_data_generator/.env.example f1_data_generator/.env
```

2. Modifiez le fichier `.env` pour définir votre pilote cible:
```bash
TARGET_DRIVER_CODE=NOR  # ou PIA pour Piastri
```

## Démarrage

1. Construire et démarrer les services:
```bash
docker-compose up -d
```

2. Créer les souscriptions QuantumLeap:
```bash
./create_subscriptions.sh
```

3. Accéder aux interfaces:
- Grafana: http://localhost:3000 (admin/admin)
- API F1 Generator: http://localhost:8000/docs

## Architecture

- FastAPI: Générateur de données F1
- Orion Context Broker: Broker NGSI-v2
- QuantumLeap: Persistance temporelle
- CrateDB: Base de données temporelle
- Grafana: Visualisation

## Références

- [Documentation FastF1](https://theoehrly.github.io/Fast-F1/)
- [Documentation FIWARE](https://fiware-tutorials.readthedocs.io/)