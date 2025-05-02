# F1 Digital Twin - Jumeau Numérique F1 avec FIWARE

Ce projet vise à créer un jumeau numérique d'une voiture de Formule 1 en utilisant les données de télémétrie en temps réel (simulées ou provenant d'un jeu) et la plateforme FIWARE. Il démontre comment capturer, gérer, historiser et potentiellement visualiser les données d'un système dynamique complexe.

**Dépôt:** [https://github.com/Marwenbellili72/F1_Digital_Twin.git](https://github.com/Marwenbellili72/F1_Digital_Twin.git)

## Table des Matières

- [Description](#description)
- [Motivation](#motivation)
- [Fonctionnalités Clés](#fonctionnalités-clés)
- [Stack Technologique](#stack-technologique)
- [Architecture (Simplifiée)](#architecture-simplifiée)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Intégration FIWARE : Souscription Orion vers QuantumLeap](#intégration-fiware--souscription-orion-vers-quantumleap)
- [Configuration](#configuration)
- [Contribuer](#contribuer)
- [Licence](#licence)

## Description

Le projet `F1_Digital_Twin` met en place une architecture basée sur FIWARE pour :
1.  Recevoir des données de télémétrie d'une voiture F1 (vitesse, RPM, position, etc.). **[VÉRIFIER/ADAPTER : Source des données, ex: via le flux UDP du jeu F1 202x, ou un script de simulation Python inclus].**
2.  Modéliser la voiture comme une entité NGSI (`type: Car`) dans l'Orion Context Broker.
3.  Stocker l'historique des données de télémétrie dans QuantumLeap pour analyse ultérieure.
4.  (Optionnel) Permettre la visualisation de ces données via Grafana. **[VÉRIFIER/ADAPTER : Confirmer si Grafana est inclus et configuré].**

## Motivation

L'objectif est d'explorer le concept de jumeau numérique appliqué au sport automobile, en utilisant des technologies IoT ouvertes comme FIWARE pour gérer le flux de données en temps réel et leur persistence, permettant des analyses de performance et de comportement.

## Fonctionnalités Clés

*   Ingestion de données de télémétrie F1 en temps réel ou simulées.
*   Représentation de la voiture en tant qu'entité dynamique dans FIWARE Orion.
*   Historisation automatique des changements d'attributs (vitesse, RPM, position X/Y, etc.) grâce à QuantumLeap.
*   Architecture basée sur Docker pour un déploiement facile des composants FIWARE et de l'application.
*   (Optionnel) Tableaux de bord pré-configurés dans Grafana pour la visualisation.

## Stack Technologique

*   **FIWARE Orion Context Broker:** Gestion des entités et de leur contexte en temps réel.
*   **FIWARE QuantumLeap:** Historisation des données de contexte vers une base de données temporelle.
*   **[VÉRIFIER/ADAPTER : Langage Principal, ex: Python 3.9+]** : Pour le script d'ingestion/simulation des données.
*   **[VÉRIFIER/ADAPTER : Source des données, ex: Client UDP pour F1 202x / Script de simulation `f1_simulator.py`]**
*   **Docker & Docker Compose:** Pour orchestrer les services FIWARE et l'application.
*   **Base de données pour QuantumLeap:** Typiquement CrateDB ou TimescaleDB (PostgreSQL). **[VÉRIFIER/ADAPTER : Préciser la BDD utilisée dans votre `docker-compose.yml`]**
*   **(Optionnel) Grafana:** Pour la visualisation des données historiques.

## Architecture (Simplifiée)

[Source Données F1 (Jeu UDP / Simulateur Python)] --> [Script Ingestion/Simu (Python)] --(NGSI API)--> [Orion Context Broker]
|
(Notification)
|
V
[QuantumLeap] --> [Base de Données (CrateDB/TimescaleDB)] --> (Optionnel) [Grafana]


## Prérequis

Avant de commencer, assurez-vous d'avoir installé :

*   [Docker](https://docs.docker.com/get-docker/) (Version X.Y ou supérieure)
*   [Docker Compose](https://docs.docker.com/compose/install/) (Version X.Y ou supérieure)
*   [Git](https://git-scm.com/)
*   **[VÉRIFIER/ADAPTER : Autres dépendances si le script tourne hors Docker, ex: Python 3.9+, pip]**

## Installation

1.  **Clonez le dépôt :**
    ```bash
    git clone https://github.com/Marwenbellili72/F1_Digital_Twin.git
    cd F1_Digital_Twin
    ```

2.  **[VÉRIFIER/ADAPTER : Si des étapes de configuration initiales sont nécessaires, ex: créer un fichier `.env` à partir de `.env.example`]**
    ```bash
    # Exemple: cp .env.example .env
    # Puis éditer le fichier .env si besoin
    ```

3.  **Lancez les services FIWARE et l'application via Docker Compose :**
    ```bash
    docker-compose up -d
    ```
    *Note : La première fois, Docker peut avoir besoin de télécharger/construire les images, ce qui peut prendre quelques minutes. Vérifiez les logs avec `docker-compose logs -f` pour vous assurer que tout démarre correctement.*

4.  **[VÉRIFIER/ADAPTER : Si des dépendances Python sont nécessaires hors Docker]**
    ```bash
    # Exemple (si nécessaire):
    # python -m venv venv
    # source venv/bin/activate  # ou .\venv\Scripts\activate sur Windows
    # pip install -r requirements.txt
    ```

## Utilisation

1.  **Démarrez la source de données / le script d'ingestion :**
    **[VÉRIFIER/ADAPTER : Choisir l'option correcte et donner la commande exacte]**
    *   **Option A (Si le script démarre avec Docker Compose):** Le service d'ingestion (ex: `f1-data-injector`) devrait déjà être en cours d'exécution. Vérifiez avec `docker-compose ps`.
    *   **Option B (Si le script doit être lancé manuellement):**
        ```bash
        # Assurez-vous d'être dans le bon répertoire et que l'environnement virtuel est activé si nécessaire
        python f1_data_injector.py # Remplacer par le nom réel de votre script
        ```
    *   **Option C (Si vous utilisez un jeu F1):** Configurez le jeu pour envoyer les données télémétriques UDP à l'adresse IP de votre machine hôte et au port écouté par votre script d'ingestion (ex: `20777`). Assurez-vous que votre script d'ingestion écoute sur ce port.

2.  **Vérifiez les données dans Orion Context Broker :**
    Une fois que les données sont envoyées, vous pouvez interroger Orion. Remplacez `Car:001` par l'ID réel de votre entité si différent.
    ```bash
    curl -X GET 'http://localhost:1026/v2/entities/Car:001?options=keyValues' -H 'Accept: application/json' | jq .
    ```
    *(L'utilisation de `jq` permet de formater joliment la sortie JSON)*

3.  **Vérifiez les données historiques dans QuantumLeap :**
    QuantumLeap stocke l'historique. Exemple pour récupérer les 5 dernières valeurs de vitesse et position pour `Car:001`:
    ```bash
    curl -X GET 'http://localhost:8668/v2/entities/Car:001/attrs/speed,x,y?lastN=5' \
         -H 'Accept: application/json' \
         -H 'fiware-service: openiot' \ # [VÉRIFIER/ADAPTER: Si vous utilisez des headers Fiware-Service/ServicePath]
         -H 'fiware-servicepath: /' | jq . # [VÉRIFIER/ADAPTER: Si vous utilisez des headers Fiware-Service/ServicePath]
    ```

4.  **(Optionnel) Accédez à la visualisation Grafana :**
    **[VÉRIFIER/ADAPTER : Confirmer si Grafana est inclus et donner l'URL]**
    *   Ouvrez votre navigateur et allez à `http://localhost:3000`.
    *   Connectez-vous avec les identifiants par défaut (souvent `admin`/`admin`, à vérifier dans votre configuration Grafana ou `docker-compose.yml`).
    *   Cherchez un tableau de bord pré-configuré pour la F1.

## Intégration FIWARE : Souscription Orion vers QuantumLeap

Pour que QuantumLeap historise automatiquement les données de télémétrie de la voiture F1 gérées par Orion, une **souscription** est nécessaire dans Orion. Elle lui demande de notifier QuantumLeap lors des mises à jour des attributs de l'entité `Car`.

**[VÉRIFIER/ADAPTER : Expliquer COMMENT cette souscription est créée dans VOTRE projet]**

*   **Option 1 : Création Manuelle (si l'utilisateur doit le faire)**
    Après avoir lancé `docker-compose up -d`, exécutez la commande `curl` suivante une seule fois :
    ```bash
    curl -X POST \
      'http://localhost:1026/v2/subscriptions' \
      -H 'Content-Type: application/json' \
      -H 'fiware-service: openiot' \ # [VÉRIFIER/ADAPTER: Ajouter si nécessaire]
      -H 'fiware-servicepath: /' \  # [VÉRIFIER/ADAPTER: Ajouter si nécessaire]
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
    Vous devriez recevoir une réponse HTTP `201 Created`.

*   **Option 2 : Création Automatisée (si un script/service le fait)**
    La souscription est créée automatiquement au démarrage par le service `[Nom du service, ex: init-subscriptions]` ou par le script `[Nom du script, ex: setup_fiware.py]`. Aucune action manuelle n'est requise pour cela.

**Explication de la souscription :**

*   **`description`**: "Notify QuantumLeap of F1 Car Telemetry Changes including position" - Description humaine de l'objectif.
*   **`subject`**: Définit le déclencheur.
    *   `entities`: Concerne toutes (`idPattern: ".*"`) les entités de type `Car`.
    *   `condition.attrs`: Se déclenche si l'un des attributs listés (vitesse, rpm, position x/y, etc.) est mis à jour.
*   **`notification`**: Définit la charge utile et la destination.
    *   `http.url`: Envoie la notification à QuantumLeap (`http://quantumleap:8668/v2/notify`). Notez l'utilisation du nom de service Docker `quantumleap`.
    *   `attrs`: Liste complète des attributs de la voiture à inclure dans la notification pour l'historisation (y compris ceux qui ne déclenchent pas forcément la notification comme `driverCode`).
    *   `metadata`: Inclut les métadonnées standard comme `dateObserved`.
    *   `attrsFormat: "normalized"`: Format NGSIv2 standard requis par QuantumLeap.
    *   `throttling: 1`: Limite les notifications à 1 par seconde par entité pour éviter de surcharger QuantumLeap lors de changements très rapides.
*   **`expires`**: Date d'expiration lointaine pour que la souscription reste active.
*   **Headers `fiware-service` / `fiware-servicepath`**: **[VÉRIFIER/ADAPTER]** Si vous utilisez la multi-tenancy FIWARE, ces headers sont essentiels et doivent correspondre à la configuration de vos services et à la manière dont les entités sont créées. Adaptez les exemples `curl` dans ce README si vous les utilisez.

## Configuration

**[VÉRIFIER/ADAPTER : Expliquer où se trouve la configuration]**

*   La configuration des services Docker (ports, volumes, etc.) se trouve dans `docker-compose.yml`.
*   Les paramètres spécifiques à l'application (ex: ID de voiture par défaut, port d'écoute UDP, adresses des services FIWARE si non-standard) peuvent se trouver dans :
    *   Un fichier `.env` (utilisé par `docker-compose.yml`).
    *   Un fichier de configuration Python (ex: `config.py`).
    *   Des variables d'environnement passées aux conteneurs dans `docker-compose.yml`.
*   La configuration de Grafana (datasources, dashboards) est généralement provisionnée via des fichiers dans un volume monté (voir `docker-compose.yml`).

## Contribuer

Les contributions sont les bienvenues ! Si vous souhaitez contribuer, veuillez ouvrir une "Issue" pour discuter de votre idée ou soumettre une "Pull Request" avec vos changements.

## Licence

**[VÉRIFIER/ADAPTER : Choisir une licence]**
Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails. (Assurez-vous d'avoir un fichier LICENSE dans votre dépôt si vous spécifiez une licence).
