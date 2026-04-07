#!/bin/bash
# Cognition Coin Testnet Stress Test Runner
# Spins up 3 local nodes on different ports.

# Cleanup function
cleanup() {
    echo "[Testnet] Stopping nodes..."
    fuser -k 8000/tcp 8001/tcp 8002/tcp
    exit
}
trap cleanup SIGINT

echo "[Testnet] Starting 3-node cluster..."
# Node 1
source venv_llama/bin/activate && python3 core_node.py node --port 8000 --mine > node_8000.log 2>&1 &
# Node 2 (Wait a bit for the first node to boot)
sleep 2
source venv_llama/bin/activate && python3 core_node.py node --port 8001 --mine > node_8001.log 2>&1 &
# Node 3
sleep 2
source venv_llama/bin/activate && python3 core_node.py node --port 8002 --mine > node_8002.log 2>&1 &

echo "[Testnet] Nodes 8000, 8001, 8002 started in background."
echo "[Testnet] Monitoring logs... (Press Ctrl+C to stop)"
tail -f node_8000.log node_8001.log node_8002.log
