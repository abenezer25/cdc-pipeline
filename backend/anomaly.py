import numpy as np
from collections import deque
from datetime import datetime

class AnomalyDetector:
    def __init__(self, window_size: int = 100):
        self.history = deque(maxlen=window_size)
        self.spike_threshold = 50000.0
        self.z_threshold = 3.0

    def evaluate(self, event: dict) -> list:
        anomalies = []
        table = event.get("table")
        op = event.get("operation")
        before = event.get("before") or {}
        after = event.get("after") or {}

        # 1. High Monetary Value Spike & Z-Score Rule
        if table == "transactions" and after and "amount" in after:
            try:
                amount = float(after.get("amount", 0))
                if amount >= self.spike_threshold:
                    anomalies.append({
                        "anomaly_id": f"anom-{event.get('timestamp_ms')}-VALUE_SPIKE",
                        "rule_name": "VALUE_SPIKE_DETECTED",
                        "severity": "CRITICAL",
                        "description": f"Anomalous transaction value detected: ${amount:,.2f} exceeds ${self.spike_threshold:,.2f}",
                        "details": {"amount": amount, "transaction_id": after.get("transaction_id")},
                        "table": table,
                        "timestamp": event.get("iso_timestamp")
                    })
                
                past_amounts = [
                    float(e["after"].get("amount", 0))
                    for e in self.history
                    if e.get("table") == "transactions" and e.get("after") and "amount" in e["after"]
                ]
                if len(past_amounts) >= 5:
                    mean = np.mean(past_amounts)
                    std = np.std(past_amounts)
                    if std > 0:
                        z = (amount - mean) / std
                        if z >= self.z_threshold:
                            anomalies.append({
                                "anomaly_id": f"anom-{event.get('timestamp_ms')}-ZSCORE_SPIKE",
                                "rule_name": "STATISTICAL_ZSCORE_SPIKE",
                                "severity": "HIGH",
                                "description": f"Transaction amount ${amount:,.2f} is {z:.2f} std devs above mean (${mean:,.2f})",
                                "details": {"amount": amount, "z_score": round(z, 2)},
                                "table": table,
                                "timestamp": event.get("iso_timestamp")
                            })
            except Exception:
                pass

        # 2. High-Frequency Velocity Burst Rule
        key = event.get("key", {})
        entity_id = key.get("account_id") or key.get("transaction_id")
        if entity_id:
            current_ts = event.get("timestamp_ms", 0)
            recent_count = sum(
                1 for h in self.history
                if (h.get("key", {}).get("account_id") == entity_id or h.get("key", {}).get("transaction_id") == entity_id)
                and (current_ts - h.get("timestamp_ms", 0)) <= 5000
            )
            if recent_count >= 4:
                anomalies.append({
                    "anomaly_id": f"anom-{event.get('timestamp_ms')}-VELOCITY_BURST",
                    "rule_name": "HIGH_FREQUENCY_VELOCITY_BURST",
                    "severity": "HIGH",
                    "description": f"Entity '{entity_id}' modified {recent_count + 1} times within 5 seconds",
                    "details": {"entity_id": entity_id, "mutation_count": recent_count + 1},
                    "table": table,
                    "timestamp": event.get("iso_timestamp")
                })

        # 3. Status Clearance Bypass Rule
        if table == "accounts" and op == "UPDATE":
            prev_status = before.get("status")
            new_status = after.get("status")
            if prev_status in ["FLAGGED", "SUSPENDED"] and new_status == "ACTIVE":
                anomalies.append({
                    "anomaly_id": f"anom-{event.get('timestamp_ms')}-STATUS_BYPASS",
                    "rule_name": "UNAUTHORIZED_STATUS_BYPASS",
                    "severity": "CRITICAL",
                    "description": f"Account '{after.get('account_id')}' status changed from '{prev_status}' to '{new_status}' without audit clearance",
                    "details": {"account_id": after.get("account_id"), "prev": prev_status, "new": new_status},
                    "table": table,
                    "timestamp": event.get("iso_timestamp")
                })

        self.history.append(event)
        return anomalies

anomaly_engine = AnomalyDetector(window_size=100)
