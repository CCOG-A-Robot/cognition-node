import time
import hashlib
import random
import os

# In production, we'd use the official SDKs (e.g., google-generativeai, openai, or local llama-cpp-python)
# For the prototype, we simulate the network call structure to show the architecture.

class SemanticMiner:
    def __init__(self, mode="local", api_key=None, model_path=None):
        """
        The Miner needs an LLM to solve the Open-Ended Semantic Constraints.
        mode: 'api' (Gemini/OpenAI/Claude) or 'local' (Llama-3/Mistral on GPU)
        """
        self.mode = mode
        self.api_key = api_key
        self.model_path = model_path
        
        if self.mode == "api" and not self.api_key:
            raise ValueError("API mode requires an API key!")
        if self.mode == "local" and not self.model_path:
            raise ValueError("Local mode requires a path to the model weights (e.g., .gguf file)!")
            
        print(f"🔧 Miner initialized in [{self.mode.upper()}] mode.")

    def _call_llm(self, prompt, temperature=0.9):
        """
        Abstracted LLM call. This is the engine of the mining rig.
        We use high temperature to guarantee diverse semantic variations (the 'Semantic Nonce').
        """
        if self.mode == "api":
            # REALITY: requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent", ...)
            # MOCK:
            time.sleep(0.5) # Simulate API latency
            variations = [
                "Heavy iron crushes the stellar core until the body detonates.",
                "The star creates iron, loses internal pressure, and violently erupts.",
                "A dense iron heart forms, triggering the ultimate cosmic blast."
            ]
            return random.choice(variations) + " " * random.randint(0, 3)
            
        elif self.mode == "local":
            # REALITY: llm = Llama(model_path=self.model_path); llm(prompt, temperature=temperature)
            # MOCK:
            time.sleep(0.1) # Local inference is often faster/cheaper but requires heavy hardware
            variations = [
                "Burning iron fuses rapidly before the ancient sun finally dies.",
                "The massive iron core collapses, and the dying star explodes."
            ]
            return random.choice(variations) + " " * random.randint(0, 3)

    def _verify_hash(self, text, difficulty):
        """Standard SHA-256 validation."""
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return h.startswith('0' * difficulty), h

    def mine_block(self, constraint_prompt, difficulty):
        """
        The main mining loop. 
        Instead of hashing a number trillions of times, we query an LLM 
        hundreds of times until we hit the cryptographic target.
        """
        print(f"\n[Mining Rig] Target Difficulty: {difficulty} leading zeros.")
        print(f"[Mining Rig] Constraint: '{constraint_prompt}'\n")
        
        attempts = 0
        start_time = time.time()
        
        while True:
            attempts += 1
            # 1. Generate the Semantic Nonce (The Guess)
            semantic_guess = self._call_llm(constraint_prompt, temperature=1.0)
            clean_guess = semantic_guess.strip()
            
            # 2. Check the cryptographics
            is_valid, current_hash = self._verify_hash(clean_guess, difficulty)
            
            # Logging progress (throttle printing so we don't spam the console)
            if attempts % 5 == 0:
                print(f"   ...Attempt {attempts}: Hash={current_hash[:8]}... (Miss)")
                
            if is_valid:
                elapsed = time.time() - start_time
                print(f"\n💎 SUCCESS! Block Solved in {elapsed:.2f}s after {attempts} inference calls.")
                print(f"   -> Winning Payload: '{clean_guess}'")
                print(f"   -> Block Hash:      {current_hash}")
                return clean_guess, current_hash

if __name__ == "__main__":
    print("==================================================")
    print("  COGNITION COIN: MINER HARDWARE INTEGRATION")
    print("==================================================\n")

    # The network dictates the puzzle (determined by the previous block's hash)
    network_puzzle = "Write a grammatically correct, 10-word sentence describing the death of a star, using the word 'iron'."
    network_difficulty = 1 # Kept low so the prototype solves quickly

    # User A: A rich guy using the Gemini API (Pays $ per million tokens)
    print("--- STARTING API MINER (Cloud Compute) ---")
    cloud_miner = SemanticMiner(mode="api", api_key="GEMINI_MOCK_KEY_123")
    cloud_miner.mine_block(network_puzzle, network_difficulty)
    
    # User B: A hacker running Llama-3 locally on an RTX 4090 (Pays electricity)
    print("\n--- STARTING LOCAL MINER (GPU Compute) ---")
    local_miner = SemanticMiner(mode="local", model_path="/models/llama-3-8b.gguf")
    local_miner.mine_block(network_puzzle, network_difficulty)
