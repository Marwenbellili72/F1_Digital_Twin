
# Formula 1 Telemetry with FIWARE, QuantumLeap, and Grafana

This project demonstrates how to simulate Formula 1 car telemetry data, send it to Orion Context Broker, persist it with QuantumLeap, and visualize it using Grafana connected to CrateDB.

---

## 📦 Project Setup

### 1. Cloner le dépôt

```bash
git clone https://github.com/Marwenbellili72/F1_Digital_Twin.git
cd F1_Digital_Twin
```

### 2. Lancer les conteneurs avec Docker

```bash
docker-compose up -d
```

---

## 🏎️ Données de télémétrie simulées

Les données de télémétrie générées incluent :

- `speed`, `rpm`, `gear`, `throttle`, `brake`, `drs`, `distance`
- `driverCode`, `lapNumber`, `timeWithinLap`, `simulatedElapsedTime`
- `x`, `y` (position)
- `simulationSessionKey`

Ces données sont envoyées vers **Orion Context Broker**.

---

## 🔔 Créer une Subscription de Notification

Une fois Orion actif, exécutez cette commande pour notifier QuantumLeap :

```bash
curl -X POST \
  'http://localhost:1026/v2/subscriptions' \
  -H 'Content-Type: application/json' \
  -d '{
  "description": "Notify QuantumLeap of F1 Car Telemetry Changes including position",
  "subject": {
    "entities": [
      {
        "idPattern": ".*",
        "type": "Car"
      }
    ],
    "condition": {
      "attrs": [ "speed", "rpm", "gear", "throttle", "brake", "drs", "distance", "lapNumber", "timeWithinLap", "simulatedElapsedTime", "x", "y" ]
    }
  },
  "notification": {
    "http": {
      "url": "http://quantumleap:8668/v2/notify"
    },
    "attrs": [ "speed", "rpm", "gear", "throttle", "brake", "drs", "distance", "driverCode", "lapNumber", "timeWithinLap", "simulatedElapsedTime", "simulationSessionKey", "x", "y" ],
    "metadata": [ "dateObserved" ],
    "attrsFormat": "normalized",
    "throttling": 1
  },
  "expires": "2030-01-01T00:00:00.00Z"
}'
```

---

## 🗺️ Architecture du projet

![Architecture](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/img.png)

---

## 📊 Configuration de Grafana

### 1. Ajouter une source de données PostgreSQL

- **Name:** `formula1`
- **Host:** `crate-db:5432`
- **Database:** `doc`
- **User:** `crate`
- **TLS/SSL Mode:** `disable`

### 2. Importer le tableau de bord

Dans Grafana :

1. Aller dans **Dashboards > Import**.
2. Importer le fichier `grafana.json` fourni dans ce projet.

---

## ✅ Résultat

Les données de simulation sont visualisables en temps réel dans le tableau de bord Grafana, persistées dans CrateDB via QuantumLeap.

---

## 📁 Fichiers utiles

- `grafana.json` – dashboard Grafana
- `docker-compose.yml` – configuration des services
