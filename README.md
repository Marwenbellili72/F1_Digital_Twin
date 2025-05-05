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

![Vodafone McLaren Mercedes Dashboard](https://i.pinimg.com/originals/76/1c/49/761c49de4a7e57d64d5cbb9b15e9c80f.jpg)

> *Source: McLaren Technology Centre*

---

## 🏗️ How the Digital Twin is Built

This project emulates the behavior of an F1 car with:

- A **Python-based data generator** that sends telemetry to FIWARE’s **Orion Context Broker**
- A **subscription** to **QuantumLeap** which forwards data to **CrateDB**
- **Grafana** dashboards for time-series analysis and visualization

---

## 🧱 System Architecture

```

+----------------+     NGSI     +---------------+     time-series     +------------+
\| Data Generator | -----------> | Orion Broker  | ------------------> | QuantumLeap|
+----------------+              +---------------+                     +-----+------+
|
writes to CrateDB
|
Grafana

````

---

## 📦 docker-compose.yml Overview

The `docker-compose.yml` launches the following services:

- **orion**: Context Broker for receiving telemetry (port `1026`)
- **mongo**: Required by Orion for context metadata
- **quantumleap**: Translates context to time-series (port `8668`)
- **crate**: Stores telemetry data (port `4200`)
- **grafana**: Visualizes metrics (port `3000`)
- **f1_data_generator**: Simulates the F1 telemetry stream

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

### 3️⃣ Check running containers

```bash
docker ps
```

Services will be available at:

* Orion: `http://localhost:1026`
* QuantumLeap: `http://localhost:8668`
* CrateDB Admin UI: `http://localhost:4200`
* Grafana UI: `http://localhost:3000` (default: admin/admin)

---

## 🚗 F1 Car Entity (NGSI Format)

An example F1 entity sent to Orion:

```json
{
  "id": "car001",
  "type": "F1_Car",
  "speed": { "type": "Number", "value": 310 },
  "rpm": { "type": "Number", "value": 14200 },
  "gear": { "type": "Number", "value": 7 },
  "drs": { "type": "Boolean", "value": true },
  "driverCode": { "type": "Text", "value": "VER" },
  "timeWithinLap": { "type": "Number", "value": 34.2 }
}
```

---

## 🔁 Subscription to QuantumLeap

`subscription.py` sets up a subscription to send all updates from `F1_Car` entities to QuantumLeap:

```json
{
  "description": "Notify QuantumLeap",
  "subject": {
    "entities": [{ "idPattern": ".*", "type": "F1_Car" }]
  },
  "notification": {
    "http": { "url": "http://quantumleap:8668/v2/notify" },
    "attrsFormat": "normalized"
  },
  "throttling": 1
}
```

---

## 📊 Grafana Dashboard

* Grafana uses CrateDB as a data source (via PostgreSQL plugin).
* The dashboard displays **real-time graphs** for speed, RPM, gear, and lap time.
* Use `grafana.json` to import the default dashboard layout.

### 👀 Example Screenshot

![Dashboard](img.png)

---

## 🗂️ Project Structure

```
F1_Digital_Twin/
├── f1_data_generator/
│   ├── generator.py         # Generates and sends F1 data to Orion
│   └── subscription.py      # Registers the subscription to QuantumLeap
├── grafana.json             # Preconfigured dashboard export
├── docker-compose.yml       # Main orchestration file
├── img.png                  # Screenshot of Grafana dashboard
└── README.md
```

---

## 🧪 Testing & Querying

Test Orion from the host machine:

```bash
curl http://localhost:1026/v2/entities
```

Access CrateDB web UI:

* Visit `http://localhost:4200`
* Example SQL query:

  ```sql
  SELECT * FROM et_f1_car;
  ```

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## 📬 Contact

> **Marwen Bellili**
> 📧 [marwenbellili72@gmail.com](mailto:marwenbellili72@gmail.com)
> 🐙 GitHub: [Marwenbellili72](https://github.com/Marwenbellili72)

---
