import hashlib
import time
from mempool_block import cognitive_hash
import random
import os
import re
from llama_cpp import Llama
import logging
import sys # Import sys for exception handling

# --- Logging Configuration ---
# Configure logging to a file to capture errors even on silent exits
logging.basicConfig(filename='debug_log.txt', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)


# --- Deterministic LLM Abstraction ---
# In a production environment, this would interface with a locally run,
# deterministic open-source LLM (e.g., Llama-3 via llama-cpp-python or a local API).
# The 'seed' (derived from the previous block hash) is CRITICAL for deterministic output.

# Define the path to the GGUF model (the one we just downloaded)
LLM_MODEL_PATH = os.path.expanduser("~/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")

# Global LLM instance to avoid reloading the model on every call
_llm_instance = None

def get_llm_instance():
    global _llm_instance
    if _llm_instance is None:
        logging.info(f"[Deterministic LLM] Initializing Llama model from: {LLM_MODEL_PATH}")
        try:
            _llm_instance = Llama(
                model_path=LLM_MODEL_PATH,
                n_gpu_layers=-1,  # Offload all layers to the GPU
                n_ctx=512,        # Context window (adjust as needed for larger models)
                verbose=True      # Show detailed loading/inference info
            )
            logging.info("[Deterministic LLM] Llama model initialized successfully.")
        except Exception as e:
            logging.critical(f"[Deterministic LLM] Fatal error initializing Llama model: {e}", exc_info=True)
            sys.exit(1) # Exit with an error code if model fails to load
    return _llm_instance

def call_deterministic_llm(prompt, seed, temperature=0.7, max_tokens=60): # Reduced max_tokens for speed
    """
    Function to call a locally hosted, deterministic LLM using llama-cpp-python.
    The 'seed' parameter influences the LLM's generation to be consistent across nodes.
    """
    llm = get_llm_instance()
    
    logging.info(f"[Deterministic LLM] Calling real LLM for prompt: \"{prompt}\" (Seed: {seed})")
    
    try:
        output = llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,  # Pass the seed for deterministic generation
            echo=False
        )
        
        logging.debug(f"[Deterministic LLM] RAW LLM RESPONSE OBJECT: {output}") # Debug print
        semantic_variation = output["choices"][0]["text"]
        time.sleep(0.1) # Simulate some minimal inference latency
        return semantic_variation.strip()
    except Exception as e:
        logging.error(f"[Deterministic LLM] Error during LLM call: {e}", exc_info=True)
        return "" # Return empty string on error

def extract_sentence_from_llm_output(raw_llm_output):
    """
    Overhauled Extractor: Specifically targets the 'slop' found in Llama-3-8B mining attempts.
    """
    logging.debug(f"[Extractor] Cleaning raw output: '{raw_llm_output}'")

    # 1. Broadest initial cleanup
    # Remove common patterns: (Note: ...), (Grade: ...), Date strings (YYYY-MM-DD), Time strings (HH:MM:SS), [User Name], etc.
    cleaned = re.sub(r'\(.*?\)', '', raw_llm_output)  # Remove parentheticals
    cleaned = re.sub(r'\[.*?\]', '', cleaned)         # Remove brackets
    cleaned = re.sub(r'\d{4}-\d{2}-\d{2}', '', cleaned) # Remove dates
    cleaned = re.sub(r'\d{2}:\d{2}:\d{2}', '', cleaned) # Remove times
    cleaned = re.sub(r'\*\*.*?\*\*', '', cleaned)     # Remove bold headers
    cleaned = re.sub(r'#+.*?\n', '', cleaned)         # Remove markdown headers
    cleaned = re.sub(r'Challenge \d+.*', '', cleaned, flags=re.IGNORECASE|re.DOTALL) # Cut off trailing challenges
    
    # 2. Extract potential sentences
    # Split by common sentence terminators
    segments = re.split(r'[.!?\n]', cleaned)
    
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
            
        # Clean up leading/trailing non-alpha
        segment = re.sub(r'^[^a-zA-Z]+', '', segment)
        segment = re.sub(r'[^a-zA-Z]+$', '', segment)
        
        # Word check
        words = segment.split()
        
        # If it has at least one word, it's a candidate
        if len(words) >= 3: # Lower threshold for extraction, validation happens later
            logging.info(f"[Extractor] Candidate isolated: '{segment}'")
            return segment

    return ""


def get_hash(text):
    """Generates a SHA-256 hash from the string."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

import json

def verify_network_rules(payload_dict, difficulty):
    """
    Verifies a block's hash based on the full header dictionary.
    """
    import re
    # 1. Semantic Check
    sentence = payload_dict.get("semantic_payload", "")
    words = re.sub(r'[^\w\s]', '', sentence.lower()).split()
    if len(words) < 5 or len(words) > 15:
        return False, "Failed: Word count"
    
    # Keyword check is dynamic, but for the prototype we'll look for common ones
    # In the full node, the validator handles this properly.
    
    # 2. Cryptographic Check
    block_string = json.dumps(payload_dict, sort_keys=True)
    h = cognitive_hash(block_string)
    
    if not h.startswith('0' * difficulty):
        return False, f"Failed: Difficulty {h}"
        
    return True, h

def ai_miner(prompt, seed, difficulty, block_template=None, abort_check=None):
    """
    AI Miner: Generates sentence, then grinds nonces against the FULL block template.
    """
    logging.info(f"[AI Miner] Received Prompt: '{prompt}'")
    
    start_time = time.time()
    ai_attempts = 0
    
    # If no template provided (standalone mode), create a dummy one
    if block_template is None:
        block_template = {
            "index": 1,
            "timestamp": time.time(),
            "transactions": [],
            "previous_hash": hex(seed),
            "difficulty": difficulty
        }

    import re
    kw_match = re.search(r"using the word '(\w+)'", prompt.lower())
    expected_keyword = kw_match.group(1) if kw_match else None

    while True:
        if abort_check and abort_check():
            logging.info("[AI Miner] Chain tip changed! Aborting before LLM call.")
            return None, None, None

        ai_attempts += 1
        
        # When temperature is 0, we can't just append a counter to the prompt and expect wildly different results,
        # so we also slightly mutate the prompt text on failures to force the LLM down a new attention path.
        if ai_attempts > 1:
            mining_prompt = f"{prompt} Try again, phrasing it differently. (Attempt: {ai_attempts})"
        else:
            mining_prompt = prompt

        semantic_guess = call_deterministic_llm(mining_prompt, seed, temperature=0.7, max_tokens=100)
        clean_guess = extract_sentence_from_llm_output(semantic_guess)
        
        if not clean_guess: continue

        import re
        words_check = re.sub(r'[^\w\s]', '', clean_guess.lower()).split()
        if len(words_check) < 5 or len(words_check) > 15:
            logging.info(f"[AI Miner] Word count ({len(words_check)}) out of bounds. Reprompting...")
            continue

        # Keyword check (allow plurals or inside quotes)
        if expected_keyword and expected_keyword.lower() not in clean_guess.lower():
            logging.info(f"[AI Miner] Missing keyword '{expected_keyword}' in payload. Reprompting...")
            continue

        logging.info(f"[AI Miner] Valid Base: '{clean_guess}'. Grinding...")

        # Update template with the new sentence
        block_template["semantic_payload"] = clean_guess

        # Increased nonce range to 4 billion (standard 32-bit limit) to prevent constant LLM interruptions
        for nonce in range(4294967295):
            if abort_check and nonce % 100 == 0:
                if abort_check():
                    logging.info("[AI Miner] Chain tip changed! Aborting current block grind.")
                    return None, None, None

            block_template["nonce"] = nonce
            
            # Use the CognitiveHash engine (MatMul ASIC-resistance)
            block_string = json.dumps(block_template, sort_keys=True)
            current_hash = cognitive_hash(block_string)
            
            if current_hash.startswith('0' * difficulty):
                elapsed = time.time() - start_time
                logging.info(f"\n[AI Miner] 💎 BLOCK FOUND in {elapsed:.4f}s!")
                return clean_guess, current_hash, nonce

if __name__ == "__main__":
    try:
        # In a real system, the prompt and seed would come from the blockchain (previous block hash).
        # For this prototype, we use a fixed seed for deterministic testing.
        test_seed = int(hashlib.sha256(b"initial_seed").hexdigest(), 16)
        prompt = "Write a single, grammatically correct sentence between 5 and 15 words describing the death of a star, using the word 'iron'. Provide ONLY the sentence."
        difficulty = 3 # Setting to 3 to test cryptographic scaling
        max_attempts = 100 # Add a practical limit for testing

        logging.info("==================================================")
        logging.info("  COGNITION COIN: V2 SEMANTIC PoW PROTOTYPE (LIVE LLM)")
        logging.info("==================================================\n")
        logging.info(f"NETWORK CONSTRAINT: \"{prompt}\"")
        logging.info(f"SEED: {test_seed}")
        logging.info(f"TARGET DIFFICULTY: {difficulty} leading zeros\n")

        logging.info("--- MINING PROCESS ---")
        # Note: ai_miner now returns (text, hash, nonce)
        winning_text, final_hash, winning_nonce = ai_miner(prompt, test_seed, difficulty)
        
        logging.info("\n--- NETWORK VERIFICATION ---")
        # The network takes the winning text and runs the cheap validation checks
        if winning_text and final_hash:
            is_valid, reason = verify_network_rules(winning_text, difficulty, winning_nonce)
            logging.info(f"[Network] Validating payload...")
            if is_valid:
                logging.info(f"[Network] ✅ Block Accepted! {reason}")
            else:
                logging.info(f"[Network] ❌ Block Rejected: {reason}")
        else:
            logging.info("[Network] ❌ No valid block found within test attempts.")
    except Exception as e:
        logging.critical(f"Unhandled exception in main execution: {e}", exc_info=True)
        sys.exit(1) # Exit with an error code for unhandled exceptions
