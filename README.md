# SentinelCDC: Real-Time CDC & Anomaly Monitoring Engine

A minimal, high-performance Change Data Capture (CDC) streaming pipeline and anomaly monitoring engine built using **PostgreSQL**, **Debezium Server**, **FastAPI**, **MongoDB**, and **Prometheus**.

Designed specifically to be lightweight, clean, and 100% compatible with **GitHub Codespaces** and local Docker environments.

---

## Minimal Portfolio Architecture

```
[ PostgreSQL 16 ] ──(WAL CDC Events)──► [ Debezium Server (HTTP Sink) ]
                                                   │
                                          (Direct HTTP Webhook POST)
                                                   ▼
[ Prometheus 9090 ] ◄──(/metrics)──── [ FastAPI Engine 8000 ] ──► [ MongoDB 27017 ]
 (Built-in Graph UI)                   (Built-in HTML / Webhook)    (Sink & Audit Logs)
```

---

## Tech Stack & Port Mappings

1. **PostgreSQL 16** (`Port 5432`): Source DB with logical decoding enabled (`wal_level = logical`).
2. **Debezium Server**: Standalone CDC engine reading Postgres WAL and posting change events directly to FastAPI via HTTP Webhooks.
3. **FastAPI (Python 3.11)** (`Port 8000`):
   - Interactive HTML status page at `GET /`.
   - Debezium HTTP Webhook receiver (`POST /api/cdc`).
   - Real-time Anomaly Engine (Z-Score spike, frequency burst, status bypass).
   - MongoDB motor driver persisting events & anomaly logs.
   - Prometheus metrics exporter (`GET /metrics`).
   - Simulation endpoints (`POST /api/simulate/{scenario}`).
4. **MongoDB 7.0** (`Port 27017`): Target document store for CDC changes and anomaly records.
5. **Prometheus** (`Port 9090`): Built-in Expression Browser & Graph UI for metric visualization without Grafana.

---

## Deploying on GitHub Codespaces

1. **Launch Codespace**: Click **Code → Open with Codespaces** in GitHub.
2. **Start Docker Containers**:
   ```bash
   docker-compose up -d --build
   ```
3. **Open Application**:
   - VS Code / Codespaces will automatically forward ports `8000` (FastAPI) and `9090` (Prometheus).
   - Click **Open in Browser** on port `8000` to view the interactive status page & trigger simulation attacks.
   - Click **Open in Browser** on port `9090` to view the built-in Prometheus Graph UI.

---

## Quick Simulation Testing

Inside the Codespaces terminal or locally, run:

```bash
# Run 1-click bash simulation script
chmod +x scripts/simulate.sh
./scripts/simulate.sh
```

Or trigger individually via `curl`:
```bash
# Standard CDC Transaction
curl -X POST http://localhost:8000/api/simulate/normal

# $150K Monetary Spike Anomaly
curl -X POST http://localhost:8000/api/simulate/spike

# High-Frequency Velocity Burst
curl -X POST http://localhost:8000/api/simulate/velocity

# Compliance Status Bypass
curl -X POST http://localhost:8000/api/simulate/bypass
```
