# 🏎️ F1 Digital Twin – Real-Time Telemetry System with FIWARE & Grafana

## 📘 Introduction

This project implements a **Digital Twin** of a Formula 1 (F1) car using an IoT and data visualization stack based on **FIWARE**, **CrateDB**, and **Grafana**.

### 🔍 What is a Digital Twin?

A **Digital Twin** is a real-time virtual representation of a physical system—in this case, an F1 car. It mirrors telemetry data such as speed, RPM, gear, and more. The Digital Twin enables:

- Continuous monitoring of the car’s performance
- Real-time data visualization
- Simulation for testing strategies or behaviors
- Demonstration of smart mobility/IoT frameworks

---

## 🧠 State of the Art – Real F1 Telemetry Systems

Digital Twin technology is used heavily in Formula 1.

### 🏁 Vodafone McLaren Mercedes Telemetry Dashboard (Reference)

The Vodafone McLaren Mercedes team built a telemetry system capable of showing:

- Live speed, RPM, gear state
- Sector/lap timing and progress
- Tyre pressure, brake temps, fuel levels
- Engine diagnostics and GPS position

📷 Example:

![Vodafone McLaren Mercedes Dashboard](https://miro.medium.com/v2/resize:fit:1100/format:webp/0*PkrUnSBX4-In-_gw)

> *Source: McLaren Technology Centre*

---

## 🏗️ How the Digital Twin is Built

This project emulates the behavior of a Formula 1 car by combining real telemetry from past races with real-time IoT architecture.

### 🧪 Data Generation using FastF1

We use the **[FastF1](https://theoehrly.github.io/Fast-F1/)** API to simulate a real F1 race session. This powerful Python library allows us to extract:

- Speed
- RPM
- Gear
- Driver code
- DRS state
- Time within the lap

from actual telemetry logs (e.g., 2022 Monza Grand Prix). These values are updated in real time and **transformed into NGSI v2-compliant entities**, representing the virtual state of the car.

Each entity is structured as an `F1_Car` object and sent to the **FIWARE Orion Context Broker**, which acts as the central receiver of all contextual information.
![fastf1](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img9.png)

### 🔁 Subscription to QuantumLeap

A **subscription** is created between Orion and **QuantumLeap** (a time-series translator). This subscription allows every update on F1_Car entities to be forwarded automatically and stored in **CrateDB**, which acts as a time-series database.

This creates a historical log of car behavior—exactly like in real F1 data telemetry centers.

### 📊 Visualization (Grafana + Streamlit + 3D)

We use a **hybrid visualization** approach:

#### 📈 Grafana Dashboards

- A dashboard in Grafana fetches data from CrateDB (via PostgreSQL plugin).
- It visualizes time-series metrics: speed, RPM, gear shifts, and lap timing.
- We use the `htmlgraphics` plugin to **embed custom HTML views** inside Grafana.

#### 🖼️ Streamlit Simulation

To simulate the race visually:
- A **Streamlit app** runs alongside the backend and uses the **FastF1 API** to draw the circuit layout.
- The **driver’s current position** is plotted live on the track.
- A **3D McLaren car model** is served via **NGINX**, and displayed inside Grafana using the `HTMLGraphics` panel.

This combination allows Grafana to act not only as a metrics dashboard, but as a **real-time cockpit**, mixing charts and 3D visualization.

---
## 🧩 System Architecture Overview

The following diagram illustrates the end-to-end architecture of the F1 Digital Twin platform, integrating telemetry ingestion, data storage, visualization, and simulation components—all containerized using Docker.

### 🔁 1. Telemetry Ingestion

- **FastF1** is used to extract real-world race telemetry (e.g., Italian GP 2023).
- Data is injected into the system via a **FastAPI service** (`f1_data_generator`).
- This service communicates with the **FIWARE Orion Context Broker** via port `8000:8000`.
- Manual queries can also be sent using `curl` or **Postman** on port `1026:1026`.

### 📡 2. Context Management (FIWARE)

- The **Orion Context Broker** receives NGSI-v2 entities and forwards them:
  - To **MongoDB** (port `27017`) for temporary storage.
  - To **QuantumLeap** (port `8668`) for time-series processing.
  - Finally, to **CrateDB** (port `4200`) for long-term historical storage.

### 💾 3. Time-Series Database

- **MongoDB** is used for internal FIWARE context persistence.
- **CrateDB** is the main time-series database queried for dashboards and analytics.
- It holds all telemetry data (speed, RPM, gear, location, lap times, etc.).

### 📊 4. Grafana Visualization

- **Grafana** is connected to CrateDB and visualizes real-time metrics:
  - 🚀 Speed, RPM, Gear
  - 🧭 Car position on track (x, y)
  - 🦶 Throttle & Brake pressure
  - ⏱️ Lap numbers and time
- Accessible at [`http://localhost:3000`](http://localhost:3000)

### 🧭 5. Race Tracker (Streamlit)

- A custom **Streamlit app** simulates the car’s position during a real race session.
- Uses FastF1 API to track the driver in real time.
- Accessible at [`http://localhost:8501`](http://localhost:8501)

### 🚗 6. 3D Car Model Simulation (NGINX)

- A realistic 3D **McLaren F1** model is rendered using **Three.js**.
- Hosted on an **NGINX** server and embedded into Grafana via an `<iframe>`.
- Accessible at [`http://localhost:8081`](http://localhost:8081)

### 🐳 7. Dockerized Deployment

- All components are containerized using **Docker** and orchestrated via **Docker Compose**.
- Each service runs on its own port, enabling modular and scalable integration.

### 🔌 Ports Summary

| Component         | Port         | Purpose                                 |
|------------------|---------------|------------------------------------------|
| Orion Context Broker | `1026`    | Receives NGSI-v2 data                   |
| FastAPI (Data Generator) | `8000`| Sends FastF1 telemetry to Orion         |
| MongoDB          | `27017`       | Context data persistence                 |
| QuantumLeap      | `8668`        | Time-series forwarding to CrateDB        |
| CrateDB          | `4200`        | Time-series database                     |
| Grafana          | `3000`        | Dashboards and real-time metrics         |
| NGINX (3D Car)   | `8081`        | 3D model visualization                   |
| Streamlit Tracker| `8501`        | Live race tracking                       |

![docker-compose](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img2.png)
---

## 🔧 Installation & Startup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Marwenbellili72/F1_Digital_Twin.git
cd F1_Digital_Twin
````

### 2️⃣ Build and start services

```bash
docker-compose up --build -d
```

### 3️⃣ Create a Notification Subscription

To enable real-time updates from the Orion Context Broker to QuantumLeap (or any consumer), a **notification subscription** must be created.

This is done by sending a `POST` request to Orion's `/v2/subscriptions` endpoint. Below is an example using `curl`:

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

Services will be available at:

* Orion: `http://localhost:1026`
* QuantumLeap: `http://localhost:8668`
* CrateDB Admin UI: `http://localhost:4200`
* Grafana UI: `http://localhost:3000` (default: admin/admin)

---

## 📡 Retrieve Data from Orion
Once the data is being generated, you can retrieve the current state of a specific car with:
```bash
curl -X GET \
  'http://localhost:1026/v2/entities/urn:ngsi-v2:Car:NOR:20240115' \
  -H 'Accept: application/json'
```
![postman](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img3.png)
This will return real-time data like:

* Speed (km/h)
* RPM
* Gear
* Position (x, y)
* Throttle, Brake, DRS
* Lap number
* Observed date/time

---
## 🚗 F1 Car Entity (NGSI Format)
This is an example of an NGSI v2 entity representing the state of a Formula 1 car (driverCode = NOR). It includes attributes like speed, RPM, throttle, gear, position, and contextual information about the race session.

To better understand and visualize the structure, the following JSON was formatted using JSON Crack:

![jsoncrack](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img4.png)

---

## 📊 Results and Visualizations

This section highlights the outcomes of the Digital Twin simulation pipeline and how each component contributes to visualizing the virtual F1 experience.


### 🛠️ 1. Real-Time Telemetry in CrateDB

All telemetry data (speed, RPM, gear, location, lap time, etc.) sent to **FIWARE Orion Context Broker** is forwarded via **QuantumLeap** to **CrateDB**.

You can query CrateDB directly to inspect the recorded time-series data:

```sql
SELECT entity_id, entity_type, time_index, fiware_servicepath, __original_ngsi_entity__, instanceid, speed, rpm, gear, throttle, brake, drs, distance, drivercode, lapnumber, timewithinlap, simulatedelapsedtime, simulationsessionkey, x, y
FROM "doc"."etcar"
LIMIT 100;
```
![cratedb](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img5.png)

The CrateDB web interface is accessible via:  [http://localhost:4200](http://localhost:4200)

### 🏎️ 2. 3D Car Model Simulation (via NGINX)

A realistic **3D model of the McLaren F1 car** is rendered inside the Grafana dashboard using the **HTMLGraphics plugin**.

* The 3D object is built using **Three.js**, a JavaScript library for 3D graphics in the browser.
* It is served via **NGINX**, accessible at: [http://localhost:8081](http://localhost:8081)
* The model is embedded into Grafana using an `<iframe>` within the **HTML panel plugin**
![3dmodel](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img6.png)

### 📍 3. Race Tracker Simulation with Streamlit

A custom **Streamlit** application simulates the position of the F1 car on the racing circuit using the **FastF1 API**.

* Replays a real F1 session (Italian GP 2023 - Race)
* Displays real-time movement of the driver (`NOR`) on the track
* Enhances digital twin realism by combining actual race data and simulation

The Streamlit interface is accessible via: [http://localhost:8501](http://localhost:8501)

![racetracker](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img7.png)


### 📈 4. Grafana Dashboards

**Real-time Grafana dashboards** visualize key performance indicators of the virtual F1 car throughout the simulation:

- 🚀 Speed, RPM, and Gear
- 🧭 Driver position on the track (coordinates `x`, `y`)
- 🦶 Throttle and Brake pressure
- ⏱️ Lap number and lap timing

These dashboards are connected to **CrateDB**, receiving live updates via **QuantumLeap** as data is published by the Orion Context Broker.

The Grafana interface is accessible via: [http://localhost:3000](http://localhost:3000)

![grafana](https://github.com/Marwenbellili72/F1_Digital_Twin/blob/main/assets/img8.png)

---
