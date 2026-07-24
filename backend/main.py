import asyncio
import logging
import random
import time
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
from prometheus_client import Counter, Histogram, generate_latest

from config import settings
from anomaly import anomaly_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinel")

# Prometheus Metrics Definitions
CDC_EVENTS_TOTAL = Counter('sentinel_cdc_events_total', 'Total count of CDC events', ['table', 'operation'])
ANOMALIES_TOTAL = Counter('sentinel_anomalies_detected_total', 'Total anomalies detected', ['rule_name', 'severity'])
PROCESSING_LATENCY = Histogram('sentinel_cdc_processing_latency_seconds', 'Latency of CDC processing in seconds')

mongo_client: AsyncIOMotorClient = None
mongo_db = None
pg_pool = None

OPERATION_MAP = {'c': 'INSERT', 'u': 'UPDATE', 'd': 'DELETE', 'r': 'READ'}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, mongo_db, pg_pool
    logger.info("Connecting to MongoDB and PostgreSQL...")
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    mongo_db = mongo_client[settings.MONGODB_DB_NAME]
    
    try:
        pg_pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB
        )
        logger.info("Connected to PostgreSQL pool for simulation triggers.")
    except Exception as e:
        logger.warning(f"PostgreSQL connection warning: {e}")
        
    yield
    
    if mongo_client:
        mongo_client.close()
    if pg_pool:
        await pg_pool.close()

app = FastAPI(title="SentinelCDC Engine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "status": "ONLINE",
        "engine": "SentinelCDC Real-Time CDC & Anomaly Engine",
        "metrics_endpoint": "/metrics",
        "docs": "/docs",
        "prometheus_ui": "http://localhost:9090"
    }

@app.get("/metrics")
def metrics():
    """Prometheus Scrape Endpoint"""
    return Response(content=generate_latest(), media_type="text/plain")

@app.post("/api/cdc")
async def receive_debezium_webhook(request: Request):
    """Debezium Server HTTP Webhook Sink Endpoint"""
    start_time = time.time()
    try:
        body = await request.json()
        payload = body.get("payload", body)
        
        op_code = payload.get("op", "u")
        op = OPERATION_MAP.get(op_code, op_code.upper())
        source = payload.get("source", {})
        table = source.get("table", "unknown")
        before = payload.get("before")
        after = payload.get("after")
        ts_ms = payload.get("ts_ms") or int(datetime.utcnow().timestamp() * 1000)
        
        key = {}
        target_dict = after or before or {}
        for k in ["account_id", "transaction_id", "id"]:
            if k in target_dict:
                key[k] = target_dict[k]
                
        event = {
            "event_id": f"evt-{ts_ms}-{table}",
            "table": table,
            "operation": op,
            "before": before,
            "after": after,
            "key": key,
            "timestamp_ms": ts_ms,
            "iso_timestamp": datetime.fromtimestamp(ts_ms / 1000.0).isoformat() + "Z"
        }
        
        CDC_EVENTS_TOTAL.labels(table=table, operation=op).inc()
        anomalies = anomaly_engine.evaluate(event)
        
        for anom in anomalies:
            ANOMALIES_TOTAL.labels(rule_name=anom["rule_name"], severity=anom["severity"]).inc()
            logger.warning(f" ANOMALY: [{anom['severity']}] {anom['description']}")
            if mongo_db is not None:
                await mongo_db.anomalies.insert_one(anom)

        if mongo_db is not None:
            await mongo_db.cdc_events.insert_one(event)
            if after and key:
                primary_id = next(iter(key.values()))
                await mongo_db[f"sink_{table}"].replace_one({"_id": primary_id}, after, upsert=True)

        proc_time = time.time() - start_time
        PROCESSING_LATENCY.observe(proc_time)
        return {"status": "SUCCESS", "event_id": event["event_id"], "anomalies_count": len(anomalies)}

    except Exception as e:
        logger.error(f"Error processing Debezium webhook: {e}")
        return {"status": "ERROR", "message": str(e)}

@app.get("/api/events")
async def get_events(limit: int = 50):
    if mongo_db is None:
        return []
    cursor = mongo_db.cdc_events.find({}, {"_id": 0}).sort("timestamp_ms", -1).limit(limit)
    return await cursor.to_list(length=limit)

@app.get("/api/anomalies")
async def get_anomalies(limit: int = 50):
    if mongo_db is None:
        return []
    cursor = mongo_db.anomalies.find({}, {"_id": 0}).sort("timestamp_ms", -1).limit(limit)
    return await cursor.to_list(length=limit)

# Database Traffic Simulation Endpoints
@app.post("/api/simulate/normal")
async def simulate_normal():
    if not pg_pool:
        return {"status": "ERROR", "message": "PostgreSQL pool not available"}
    async with pg_pool.acquire() as conn:
        tx_id = f"TX-{random.randint(10000, 99999)}"
        src = "ACC-1001"
        dest = "ACC-1002"
        amt = round(random.uniform(20.0, 350.0), 2)
        await conn.execute(
            "INSERT INTO sentinel.transactions (transaction_id, source_account_id, destination_account_id, amount) VALUES ($1, $2, $3, $4)",
            tx_id, src, dest, amt
        )
        await conn.execute("UPDATE sentinel.accounts SET balance = balance - $1 WHERE account_id = $2", amt, src)
        return {"message": "Normal transaction generated", "tx_id": tx_id, "amount": amt}

@app.post("/api/simulate/spike")
async def simulate_spike():
    if not pg_pool:
        return {"status": "ERROR", "message": "PostgreSQL pool not available"}
    async with pg_pool.acquire() as conn:
        tx_id = f"TX-SPIKE-{random.randint(1000, 9999)}"
        src = "ACC-1004"
        dest = "ACC-1003"
        amt = round(random.uniform(95000.0, 200000.0), 2)
        await conn.execute(
            "INSERT INTO sentinel.transactions (transaction_id, source_account_id, destination_account_id, amount, transaction_type) VALUES ($1, $2, $3, $4, 'WIRE')",
            tx_id, src, dest, amt
        )
        return {"message": "Value spike anomaly generated", "tx_id": tx_id, "amount": amt}

@app.post("/api/simulate/velocity")
async def simulate_velocity():
    if not pg_pool:
        return {"status": "ERROR", "message": "PostgreSQL pool not available"}
    async with pg_pool.acquire() as conn:
        for _ in range(6):
            await conn.execute("UPDATE sentinel.accounts SET balance = balance + 5.0 WHERE account_id = 'ACC-1001'")
        return {"message": "Velocity burst updates generated", "account_id": "ACC-1001", "count": 6}

@app.post("/api/simulate/bypass")
async def simulate_bypass():
    if not pg_pool:
        return {"status": "ERROR", "message": "PostgreSQL pool not available"}
    async with pg_pool.acquire() as conn:
        await conn.execute("UPDATE sentinel.accounts SET status = 'ACTIVE', risk_score = 0 WHERE account_id = 'ACC-1004'")
        return {"message": "Status bypass updated for ACC-1004"}
