import hashlib
import time
import random

# A mock dictionary to simulate the "Weights" of our Genesis Model.
# In production, this would be an actual LLM (like Llama-3) running deterministically.
MOCK_GENESIS_WEIGHTS = [
    {"prompt": "I am the invisible force that binds the universe, yet I cannot be seen. I accelerate galaxies apart.", "answer": "dark energy"},
    {"prompt": "A biological catalyst that accelerates chemical reactions without being consumed.", "answer": "enzyme"},
    {"prompt": "The point of no return around a singularity, where escape velocity exceeds the speed of light.", "answer": "event horizon"},
    {"prompt": "I am a metal that is liquid at room temperature, often used in old thermometers.", "answer": "mercury"},
    {"prompt": "The theoretical bridge through space-time that connects two distant points.", "answer": "wormhole"}
]

def get_hash(data):
    """Standard SHA-256 hashing."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def generate_puzzle(previous_block_hash):
    """
    THE ORACLE PROBLEM SOLVED: Deterministic Puzzle Generation.
    Every node uses the previous block's hash as the seed. 
    Because the seed is identical, every node generates the EXACT SAME puzzle 
    without communicating with a central server.
    """
    # Convert the hex hash into an integer seed for the deterministic PRNG
    seed = int(previous_block_hash, 16)
    random.seed(seed)
    
    # Simulate an LLM generating a semantic puzzle deterministically
    puzzle_data = random.choice(MOCK_GENESIS_WEIGHTS)
    return puzzle_data["prompt"], puzzle_data["answer"]

def verify_block(previous_block_hash, ai_guess, nonce, difficulty):
    """Mathematically trivial network verification."""
    block_data = f"{previous_block_hash}|{ai_guess}|{nonce}"
    h = get_hash(block_data)
    return h.startswith('0' * difficulty), h

def ai_miner(previous_block_hash, prompt, actual_answer, difficulty):
    """
    The AI Miner reads the prompt, uses semantic intuition to guess the answer,
    and then brute-forces the nonce to satisfy the network difficulty.
    """
    print(f"  [AI Miner] Analyzing prompt: '{prompt}'")
    print(f"  [AI Miner] Semantic intuition lock: '{actual_answer}'")
    
    nonce = 0
    start_time = time.time()
    
    while True:
        is_valid, current_hash = verify_block(previous_block_hash, actual_answer, nonce, difficulty)
        if is_valid:
            elapsed = time.time() - start_time
            print(f"  [AI Miner] 💎 BLOCK MINED in {elapsed:.4f}s! (Nonce: {nonce})")
            return actual_answer, nonce, current_hash
        nonce += 1

def simulate_blockchain(num_blocks=3, difficulty=4):
    print("==================================================")
    print("  COGNITION COIN: GENESIS LOOP PROTOTYPE (V2)")
    print("==================================================\n")
    
    # Block 0: The Genesis Block (Hardcoded seed)
    current_block_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    print(f"Genesis Block [0] Hash: {current_block_hash}\n")
    
    for i in range(1, num_blocks + 1):
        print(f"--- MINING BLOCK [{i}] ---")
        
        # 1. The Network deterministically generates the puzzle
        print(f"[Network] Feeding Block [{i-1}] hash into Genesis Model...")
        prompt, answer = generate_puzzle(current_block_hash)
        print(f"[Network] Generated Puzzle: \"{prompt}\"")
        
        # 2. The AI Miner solves it
        _, winning_nonce, winning_hash = ai_miner(current_block_hash, prompt, answer, difficulty)
        
        # 3. Network verifies and appends to chain
        is_valid, _ = verify_block(current_block_hash, answer, winning_nonce, difficulty)
        if is_valid:
            print(f"[Network] Block [{i}] Verified! Hash appended to chain.")
            current_block_hash = winning_hash
            print(f"Block [{i}] Final Hash: {current_block_hash}\n")
        else:
            print(f"[Network] Block [{i}] REJECTED.\n")

if __name__ == "__main__":
    simulate_blockchain(num_blocks=4, difficulty=4)
