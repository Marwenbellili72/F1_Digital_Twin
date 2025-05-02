
# 🚗 F1 Car Telemetry - FIWARE Integration Project

## 📌 Objectif

Ce projet simule des données de télémétrie d'une voiture de F1, les enrichit avec du contexte (position, temps, etc.), les envoie vers **Orion Context Broker**, et configure une **subscription** pour notifier **QuantumLeap**.

---

## 🧱 Architecture

![Architecture](https://github.com/ton-utilisateur/ton-repo/raw/main/img.png)

---

## ⚙️ Étapes pour démarrer le projet

1. **Cloner le dépôt GitHub**  
   ```bash
   git clone https://github.com/ton-utilisateur/ton-repo.git
   cd ton-repo
   ```

2. **Lancer les conteneurs Docker**  
   ```bash
   docker-compose up -d
   ```

3. **Créer une subscription vers QuantumLeap**  
   Exécute la commande suivante une fois que tous les conteneurs sont prêts (en particulier Orion et QuantumLeap) :

   ```bash
   curl -X POST      'http://localhost:1026/v2/subscriptions'      -H 'Content-Type: application/json'      -d '{
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

## 🛠 Fonctionnement général

1. **Génération de données**  
   Un simulateur envoie périodiquement des données de télémétrie (vitesse, régime moteur, etc.).

2. **Ajout de contexte**  
   Les données sont enrichies avec des attributs supplémentaires tels que la position `(x, y)`, le temps dans le tour, etc.

3. **Publication vers Orion Context Broker**  
   Les entités `Car` sont mises à jour dans Orion.

4. **Notification automatique vers QuantumLeap**  
   La subscription détecte les changements et envoie les mises à jour à QuantumLeap pour stockage temporel.
