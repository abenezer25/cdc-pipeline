#!/usr/bin/env bash
# SentinelCDC Simulation Script for GitHub Codespaces

BASE_URL=${1:-"http://localhost:8000"}

echo " SentinelCDC Simulation Runner"
echo "Targeting: $BASE_URL"
echo "----------------------------------------"

echo "1️⃣ Triggering Normal Transaction..."
curl -s -X POST "$BASE_URL/api/simulate/normal" | grep message
echo ""

echo "2️⃣ Triggering Monetary Spike Anomaly ($150K Wire)..."
curl -s -X POST "$BASE_URL/api/simulate/spike" | grep message
echo ""

echo "3️⃣ Triggering High-Frequency Velocity Burst..."
curl -s -X POST "$BASE_URL/api/simulate/velocity" | grep message
echo ""

echo "4️⃣ Triggering Status Bypass Anomaly..."
curl -s -X POST "$BASE_URL/api/simulate/bypass" | grep message
echo ""

echo "----------------------------------------"
echo " Done! Check Prometheus UI at http://localhost:9090 or view metrics at $BASE_URL/metrics"
