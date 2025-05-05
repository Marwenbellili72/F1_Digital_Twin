# 🏎️ F1 Digital Twin – Real-Time Telemetry System with FIWARE & Grafana

## 📘 Introduction

This project implements a **Digital Twin** of a Formula 1 (F1) car using a modern IoT and data visualization stack based on **FIWARE**, **CrateDB**, and **Grafana**.

### 🔍 What is a Digital Twin?

A **Digital Twin** is a virtual replica of a physical system. In our case, it's a **virtual F1 car** that mirrors the behavior and telemetry of a real racing car, using simulated data in real-time. The twin can be used for:

- Monitoring performance and component status
- Predictive maintenance or analytics
- Racing strategy simulation
- Learning and experimentation in smart mobility and IoT contexts

---

## ⚙️ How the Digital Twin is Built

- A **Python script simulates telemetry** data from a Formula 1 car.
- This data is sent in **NGSI v2 format** to the **FIWARE Orion Context Broker**.
- A **subscription** is created to forward updates to **QuantumLeap**, which stores them as **time series** in **CrateDB**.
- **Grafana** is connected to CrateDB to visualize speed, RPM, gear, and more—live.

---

## 🧱 System Architecture

The architecture consists of **Dockerized microservices**, communicating over a virtual network.

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

This file launches all required services:

- `orion`: Receives context data (NGSI)
- `mongo`: MongoDB for Orion metadata
- `quantumleap`: Time-series processor
- `crate`: Time-series DB
- `grafana`: Visualization
- `f1_data_generator`: Sends simulated data

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

You can verify the services are running:

```bash
docker ps
```

Expected ports:

* Orion: `localhost:1026`
* QuantumLeap: `localhost:8668`
* CrateDB UI: `localhost:4200`
* Grafana: `localhost:3000`

---

## 🚦 NGSI Entity Model

Each F1 car is modeled as an `F1_Car` entity in Orion:

```json
{
  "id": "car001",
  "type": "F1_Car",
  "speed": { "type": "Number", "value": 270 },
  "rpm": { "type": "Number", "value": 15000 },
  "gear": { "type": "Number", "value": 6 },
  "drs": { "type": "Boolean", "value": true },
  "driverCode": { "type": "Text", "value": "HAM" },
  "timeWithinLap": { "type": "Number", "value": 42.7 }
}
```

---

## 🔁 Subscription to QuantumLeap

The script `subscription.py` registers a subscription to QuantumLeap:

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

All updates are forwarded to QuantumLeap for storage in CrateDB.

---

## 📊 Grafana Visualization

* Grafana connects to CrateDB using PostgreSQL protocol.
* Use the provided dashboard file `grafana.json` to import a preconfigured layout.
* Data is visualized as graphs over time (Speed, RPM, Gear, etc.)

### 👀 Example Dashboard

![Dashboard](img.png)

---

## 🗂️ Project Structure

```bash
F1_Digital_Twin/
├── f1_data_generator/       # Telemetry simulator
│   ├── generator.py         # Main loop
│   └── subscription.py      # Creates Orion subscription
├── grafana/                 # Volume mount for Grafana data
├── grafana.json             # Dashboard export file
├── docker-compose.yml       # Service definitions
├── img.png                  # Screenshot
└── README.md
```

---

## 🧪 Manual Testing

You can use curl to test the context:

```bash
curl http://localhost:1026/v2/entities
```

Or connect to CrateDB at `http://localhost:4200`:

```sql
SELECT * FROM et_f1_car;
```

---

## 📄 License

MIT License – see [LICENSE](LICENSE) for full text.

---

## 📬 Contact

> ✉️ Marwen Bellili – [marwenbellili72@gmail.com](mailto:marwenbellili72@gmail.com)
> GitHub: [Marwenbellili72](https://github.com/Marwenbellili72)

---

```
