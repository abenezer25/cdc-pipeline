i was just exploring **debezium** and found out it's used for cdc so i just build this project

---
it looks like this:

Postgres --- wal events ---> Debezuim --- FastAPI ---> MongoDB ---> Promethues

---
i deploy it on Github Codespaces

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

