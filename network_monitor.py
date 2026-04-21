import time
import requests
import json
from datetime import datetime

# Node API Endpoint
# We query the actual blockchain.json on disk to do deep block math
BLOCKCHAIN_FILE = "blockchain.json"

def get_network_stats():
    import os
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling ledger state...")
    
    if not os.path.exists(BLOCKCHAIN_FILE):
        print("❌ Cannot find blockchain.json. Is the node synced?")
        return

    try:
        with open(BLOCKCHAIN_FILE, "r") as f:
            chain = json.load(f)
            
        height = len(chain)
        if height == 0:
            return
            
        current_block = chain[-1]
        difficulty = current_block.get("difficulty", 1)
        
        # Calculate Hashrate over the last 10 blocks
        if height > 10:
            lookback_block = chain[-10]
            time_diff = current_block["timestamp"] - lookback_block["timestamp"]
            avg_block_time = time_diff / 10
        else:
            avg_block_time = 0
            
        # Extract unique miners
        miners = set()
        for block in chain[-50:]: # Look at the last 50 blocks
            for tx in block.get("transactions", []):
                # If it's a coinbase TX (no inputs), the output is the miner
                if len(tx.get("inputs", [])) == 0:
                    for out in tx.get("outputs", []):
                        miners.add(out.get("recipient_address", "Unknown")[:12] + "...")

        print(f"==================================================")
        print(f"  COGNITION COIN NETWORK MONITOR")
        print(f"==================================================")
        print(f"  Current Block Height : {height}")
        print(f"  Network Difficulty   : {difficulty:,.2f}")
        print(f"  Avg Block Time (10b) : {avg_block_time:.1f} seconds")
        print(f"  Active Miners (50b)  : {len(miners)}")
        for i, miner in enumerate(list(miners)[:5]):
            print(f"    {i+1}. {miner}")
        if len(miners) > 5:
            print(f"    ... and {len(miners)-5} more.")
        print(f"==================================================\n")
    except Exception as e:
        print(f"⚠️ Error parsing ledger: {e}")

if __name__ == "__main__":
    while True:
        get_network_stats()
        time.sleep(30)
