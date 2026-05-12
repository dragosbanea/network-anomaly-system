# Network Anomaly Detection IDS

Real-time intrusion detection system using Isolation Forest trained on CICIDS2017.

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

## Feature Set (12 CICIDS2017-aligned features)

| Feature | Description |
|---------|-------------|
| destination_port | Destination port number |
| protocol | Protocol number (6=TCP, 17=UDP, 1=ICMP) |
| flow_duration | Flow duration in seconds |
| total_fwd_packets | Packets sent in forward direction |
| total_bwd_packets | Packets sent in backward direction |
| total_fwd_bytes | Bytes sent in forward direction |
| total_bwd_bytes | Bytes sent in backward direction |
| flow_bytes_per_sec | Total bytes / duration |
| flow_packets_per_sec | Total packets / duration |
| syn_flag_count | Number of packets with SYN flag |
| rst_flag_count | Number of packets with RST flag |
| avg_packet_size | Mean packet size across all packets |

## Quick Start

### 1. AI Service

**Without CICIDS2017** (uses synthetic data):
```bash
cd ai
pip install -r requirements.txt
python main.py
```

**With CICIDS2017** (recommended for thesis):
```bash
cd ai
# Download CSV files from https://www.unb.ca/cic/datasets/ids-2017.html
# Place them in ai/data/  (any subdirectory structure works)
mkdir data
# copy Monday-WorkingHours.pcap_ISCX.csv, Tuesday-... etc. into data/
pip install -r requirements.txt
python main.py
# To force retrain after adding new CSVs:
python main.py --retrain
```

The model trains on **BENIGN traffic only** to learn normal behaviour.
Contamination is set to 1% (vs 8% for synthetic), giving fewer false positives.

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

# Real capture:
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

## Testing Anomaly Detection

**Normal traffic:**
```bash
curl -X POST http://localhost:8080/api/traffic/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sourceIp": "192.168.1.10", "destinationIp": "8.8.8.8",
    "sourcePort": 52000, "destinationPort": 443, "protocol": "TCP",
    "totalFwdPackets": 12, "totalBwdPackets": 10,
    "totalFwdBytes": 4800, "totalBwdBytes": 8200,
    "flowDuration": 1.5, "flowBytesPerSec": 8666.7, "flowPacketsPerSec": 14.7,
    "synFlagCount": 1, "rstFlagCount": 0, "avgPacketSize": 594.5
  }'
```

**Port scan (should trigger ANOMALY):**
```bash
curl -X POST http://localhost:8080/api/traffic/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "sourceIp": "10.0.0.99", "destinationIp": "192.168.1.1",
    "sourcePort": 54321, "destinationPort": 445, "protocol": "TCP",
    "totalFwdPackets": 2, "totalBwdPackets": 0,
    "totalFwdBytes": 128, "totalBwdBytes": 0,
    "flowDuration": 0.008, "flowBytesPerSec": 16000.0, "flowPacketsPerSec": 250.0,
    "synFlagCount": 2, "rstFlagCount": 1, "avgPacketSize": 64.0
  }'
```
