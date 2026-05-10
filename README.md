# Network Anomaly Detection IDS

Real-time intrusion detection system using machine learning (Isolation Forest).

## Architecture

```
sensor  →  backend (Spring Boot :8080)  →  frontend (React :3000)
               ↕
           ai service (FastAPI :5000)
```

## Components

| Component | Stack | Port |
|-----------|-------|------|
| Backend   | Spring Boot 3.4, Java 17, H2 | 8080 |
| AI Service| Python, FastAPI, scikit-learn | 5000 |
| Sensor    | Python, Scapy | — |
| Frontend  | React 18, Vite | 3000 |

## Quick Start

### 1. AI Service
```bash
cd ai
pip install -r requirements.txt
python main.py
```
Trains Isolation Forest on first run, then serves at http://localhost:5000.

### 2. Backend
```bash
cd backend/backend_licenta
./gradlew bootRun
```
Runs at http://localhost:8080. H2 console at http://localhost:8080/h2-console.

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Opens at http://localhost:3000.

### 4. Sensor (requires admin/root for real capture)
```bash
cd sensor
pip install -r requirements.txt

# Real capture (admin):
python main.py --iface eth0 --backend http://localhost:8080 --interval 5

# Simulation mode (no admin needed):
python main.py --backend http://localhost:8080 --interval 5
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/traffic/analyze | Submit a flow for ML analysis |
| GET  | /api/traffic/recent?minutes=10 | Recent traffic flows |
| GET  | /api/traffic/results | All analysis results |
| GET  | /api/alerts | All alerts |
| GET  | /api/alerts/active | Unresolved alerts |
| PUT  | /api/alerts/{id}/resolve | Resolve an alert |
| GET  | /api/statistics/dashboard | Dashboard stats |
| POST | /api/monitoring/start | Start monitoring session |
| POST | /api/monitoring/stop | Stop monitoring session |
| GET  | /api/monitoring/active | Get active session |

## AI Service Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /predict | Predict anomaly for a flow |
| GET  | /health | Service health check |
| GET  | /model/info | Model metadata |
| POST | /train | Retrain the model |

### /predict payload example
```json
{
  "packetCount": 150,
  "byteCount": 75000,
  "duration": 2.5,
  "protocol": 6,
  "destinationPort": 80,
  "connectionsPerSecond": 1.2
}
```

## Testing Anomaly Detection

Send a port-scan-like flow directly to the backend:
```bash
curl -X POST http://localhost:8080/api/traffic/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sourceIp": "10.0.0.99",
    "destinationIp": "192.168.1.1",
    "sourcePort": 54321,
    "destinationPort": 22,
    "protocol": "TCP",
    "packetCount": 5,
    "byteCount": 320,
    "duration": 0.05,
    "connectionsPerSecond": 450.0
  }'
```
