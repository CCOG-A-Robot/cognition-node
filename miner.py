import os
import time
import hashlib
import json
import urllib.request
import urllib.error

# ==============================================================================
# COGNITION COIN - OFFICIAL API MINER (v0.1-alpha)
# ==============================================================================
# WARNING: This script burns API credits to solve semantic PoW puzzles. 
# Difficulty is currently low (Bootstrap Phase). Mine at your own risk.
# ==============================================================================

# --- CONFIGURATION ---
# Set your OpenAI API key here, or use the OPENAI_API_KEY environment variable.
API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY_HERE")
WALLET_ADDRESS = "0xYourWalletAddressHere" # Where your COG rewards go

# Mock Network Constants (To be replaced with actual RPC endpoints)
NETWORK_RPC_URL = "http://localhost:8545/cognition" # Placeholder
CURRENT_DIFFICULTY = 4 # Number of leading zeros required

def get_network_puzzle():
    """Simulates fetching the current unmined block and puzzle from the network."""
    # In production, this makes an HTTP GET to the blockchain RPC
    return {
        "block_index": 101,
        "previous_hash": "0000c673f2a9bbd0259b5bf64e1202f6fe5ae26d9c8a6fb6f16d3f5f36d0e65a",
        "puzzle": "A biological catalyst that accelerates chemical reactions without being consumed.",
        "difficulty": CURRENT_DIFFICULTY
    }

def ask_llm(puzzle_text):
    """Calls the OpenAI API to solve the semantic puzzle."""
    print(f"[*] Querying OpenAI API for semantic solution...")
    
    if API_KEY == "YOUR_OPENAI_API_KEY_HERE":
        print("[!] ERROR: No API key provided. Edit miner.py or set OPENAI_API_KEY.")
        exit(1)

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # We instruct the model to be extremely concise. Extra words ruin the hash.
    data = {
        "model": "gpt-4o-mini", # Fast, cheap, perfect for early blocks
        "messages": [
            {"role": "system", "content": "You are a cryptographic solver. Answer the riddle with ONE concise word or standard phrase. No punctuation. Lowercase."},
            {"role": "user", "content": puzzle_text}
        ],
        "temperature": 0.0 # Deterministic answers
    }
    
    try:
        req = urllib.request.Request(url, json.dumps(data).encode('utf-8'), headers)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            answer = result['choices'][0]['message']['content'].strip().lower()
            return answer
    except urllib.error.URLError as e:
        print(f"[!] API Error: {e}")
        return "error"

def mine_block(block_data, semantic_answer):
    """The local CPU hashing loop. Brute forces the nonce."""
    print(f"[*] Commencing local hashing loop (Difficulty: {block_data['difficulty']})")
    target = '0' * block_data['difficulty']
    nonce = 0
    start_time = time.time()
    
    while True:
        # The PoW Hash: PreviousHash + SemanticAnswer + Nonce
        payload = f"{block_data['previous_hash']}|{semantic_answer}|{nonce}".encode('utf-8')
        h = hashlib.sha256(payload).hexdigest()
        
        if h.startswith(target):
            elapsed = time.time() - start_time
            hash_rate = nonce / elapsed if elapsed > 0 else 0
            print(f"\n[+] 💎 BLOCK MINED! 💎")
            print(f"    Hash:  {h}")
            print(f"    Nonce: {nonce}")
            print(f"    Time:  {elapsed:.2f}s ({hash_rate:,.0f} hashes/sec)")
            return nonce, h
            
        nonce += 1
        
        if nonce % 500000 == 0:
            print(f"    ... still hashing (Nonce: {nonce:,})")

def submit_block(block_index, nonce, semantic_answer, wallet):
    """Simulates submitting the mined block to the network."""
    print(f"[*] Broadcasting Block {block_index} to network...")
    # In production, this makes an HTTP POST to the blockchain RPC
    time.sleep(0.5)
    print(f"[+] Block Accepted! Reward routed to {wallet}\n")

if __name__ == "__main__":
    print("""
   ____                  _ __  _               ____      _     
  / ___|___   __ _ _ __ (_) /_(_) ___  _ __   / ___|___ (_)_ __ 
 | |   / _ \ / _` | '_ \| | __| |/ _ \| '_ \ | |   / _ \| | '_ \\
 | |__| (_) | (_| | | | | | |_| | (_) | | | || |__| (_) | | | | |
  \____\___/ \__, |_| |_|_|\__|_|\___/|_| |_| \____\___/|_|_| |_|
             |___/                                               
    """)
    print("Initializing Semantic Proof-of-Work Miner...")
    print(f"Wallet Address: {WALLET_ADDRESS}")
    print("-" * 60)
    
    while True:
        try:
            # 1. Get the puzzle
            block_data = get_network_puzzle()
            print(f"[*] Received Block {block_data['block_index']} - Puzzle: \"{block_data['puzzle']}\"")
            
            # 2. Let the AI solve the semantic riddle (Costs API credits)
            answer = ask_llm(block_data['puzzle'])
            print(f"[+] AI Intuition Lock: '{answer}'")
            
            if answer == "error":
                print("[!] Skipping block due to API failure.\n")
                time.sleep(5)
                continue
                
            # 3. CPU Brute Force the Nonce (Costs Electricity)
            winning_nonce, winning_hash = mine_block(block_data, answer)
            
            # 4. Claim the reward
            submit_block(block_data['block_index'], winning_nonce, answer, WALLET_ADDRESS)
            
            # Pause before the next block
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n[*] Mining manually stopped by user.")
            break
