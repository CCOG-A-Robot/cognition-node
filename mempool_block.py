import time
import hashlib
import json
from wallet_transaction import UTXO, Transaction, TransactionInput, TransactionOutput
# We will import verify_network_rules inside the method to avoid circular imports 
# or just re-implement the lightweight semantic check here for performance.

# --- Blockchain Consensus Parameters ---
TARGET_BLOCK_TIME = 150  # 2.5 minutes
DIFFICULTY_ADJUSTMENT_INTERVAL = 10  # Every 10 blocks
INITIAL_DIFFICULTY = 1

def generate_semantic_challenge(previous_block_hash, current_difficulty):
    """
    The Genesis Model Oracle: Deterministically generates a unique riddle 
    for the next block based on the previous hash.
    Ensures every block has a fresh topic and keyword.
    """
    seed_val = int(previous_block_hash[:8], 16)
    
    topics = [
        "the death of a star", "the depths of the ocean", "the behavior of black holes",
        "quantum entanglement", "the evolution of intelligence", "the heat death of the universe",
        "the formation of mountains", "the cycle of rain", "the structure of DNA",
        "the fusion of atoms", "the birth of a galaxy", "the erosion of stone"
    ]
    keywords = ["iron", "carbon", "gravity", "time", "light", "cold", "fire", "stone", "water", "void"]
    
    topic = topics[seed_val % len(topics)]
    keyword = keywords[(seed_val // len(topics)) % len(keywords)]
    
    # In the future, we can use the LLM to 'flavor' this prompt,
    # but for now, we keep it structured so non-AI nodes can verify it.
    prompt = (
        f"Write a single, grammatically correct sentence between 5 and 15 words "
        f"describing {topic}, using the word '{keyword}'. "
        f"Provide ONLY the sentence. Do not include notes, timestamps, or headers."
    )
    return prompt


def cognitive_hash(block_string):
    """
    The Matrix-Multiplication (MatMul) Memory-Hard Proof of Work.
    Simulates an AI hardware workload using pure integer math to ensure
    cross-platform determinism and starve SHA-256 ASICs.
    """
    seed_hash = hashlib.sha256(block_string.encode('utf-8')).digest()
    seed_int = int.from_bytes(seed_hash[:4], 'big')
    
    # Initialize a strictly deterministic LCG (Linear Congruential Generator)
    state = seed_int
    
    # Generate two matrices (64x64)
    # A 64x64 matrix requires 64^3 = 262,144 multiplication loops.
    MATRIX_SIZE = 64 
    
    def lcg_rand():
        nonlocal state
        state = (25214903917 * state + 11) & 281474976710655
        return (state >> 16) & 0xFF  # Return 0-255 integer
        
    matrix_a = [lcg_rand() for _ in range(MATRIX_SIZE * MATRIX_SIZE)]
    matrix_b = [lcg_rand() for _ in range(MATRIX_SIZE * MATRIX_SIZE)]
    
    # Perform pure integer Matrix Multiplication
    result_sum = 0
    for i in range(MATRIX_SIZE):
        row_offset = i * MATRIX_SIZE
        for j in range(MATRIX_SIZE):
            cell_val = 0
            for k in range(MATRIX_SIZE):
                a_val = matrix_a[row_offset + k]
                b_val = matrix_b[k * MATRIX_SIZE + j]
                cell_val += a_val * b_val
            result_sum += cell_val
            
    # Finalize the hash
    final_payload = f"{seed_hash.hex()}_{result_sum}"
    return hashlib.sha256(final_payload.encode('utf-8')).hexdigest()

class UTXOSet:
    """
    Manages the global set of all Unspent Transaction Outputs on the network.
    Key: (tx_id, output_index) -> Value: UTXO object.
    """
    def __init__(self):
        self.utxos = {}

    def add_utxo(self, utxo):
        self.utxos[(utxo.tx_id, utxo.output_index)] = utxo

    def get_utxo(self, tx_id, output_index):
        return self.utxos.get((tx_id, output_index))
    
    def remove_utxo(self, tx_id, output_index):
        if (tx_id, output_index) in self.utxos:
            del self.utxos[(tx_id, output_index)]

    def get_balance(self, address):
        balance = 0
        for utxo in self.utxos.values():
            if utxo.recipient_address == address:
                balance += utxo.amount
        return balance

class Mempool:
    def __init__(self):
        self.pending_transactions = []

    def add_transaction(self, tx: Transaction):
        print(f"[Mempool] Received transaction {tx.tx_id[:8]}...")
        self.pending_transactions.append(tx)

class Block:
    def __init__(self, index, previous_hash, transactions, semantic_payload, difficulty, nonce=0):
        self.index = index
        self.timestamp = time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.semantic_payload = semantic_payload
        self.difficulty = difficulty
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "semantic_payload": self.semantic_payload,
            "difficulty": self.difficulty,
            "nonce": self.nonce
        }, sort_keys=True)
        return cognitive_hash(block_string)

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "semantic_payload": self.semantic_payload,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "hash": self.hash
        }

class Blockchain:
    def __init__(self):
        self.chain = []
        self.mempool = Mempool()
        self.utxo_set = UTXOSet()
        self.difficulty = INITIAL_DIFFICULTY
        if not self.load_from_disk():
            self.create_genesis_block()
            self.save_to_disk()

    def save_to_disk(self, filename="blockchain.json"):
        try:
            with open(filename, "w") as f:
                json.dump([block.to_dict() for block in self.chain], f, indent=4)
        except Exception as e:
            print(f"⚠️ Failed to save blockchain to disk: {e}")

    def load_from_disk(self, filename="blockchain.json"):
        import os
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, "r") as f:
                chain_data = json.load(f)
            for block_data in chain_data:
                block = Block(
                    index=block_data["index"],
                    previous_hash=block_data["previous_hash"],
                    transactions=block_data["transactions"],
                    semantic_payload=block_data["semantic_payload"],
                    difficulty=block_data["difficulty"],
                    nonce=block_data["nonce"]
                )
                block.timestamp = block_data["timestamp"]
                block.hash = block_data["hash"]
                self.chain.append(block)
                
                # Rebuild UTXOs
                for tx in block.transactions:
                    for tx_in in tx.get("inputs", []):
                        self.utxo_set.remove_utxo(tx_in["utxo_tx_id"], tx_in["utxo_output_index"])
                    for i, tx_out in enumerate(tx.get("outputs", [])):
                        from wallet_transaction import UTXO
                        self.utxo_set.add_utxo(UTXO(tx["tx_id"], i, tx_out["amount"], tx_out["recipient_address"]))
            print(f"💾 [Persistence] Loaded {len(self.chain)} blocks from {filename}. UTXOs rebuilt.")
            self.difficulty = self.get_difficulty()
            return True
        except Exception as e:
            print(f"⚠️ [Persistence] Error loading blockchain from disk: {e}. Starting fresh.")
            self.chain = []
            self.utxo_set = UTXOSet()
            return False

    def create_genesis_block(self):
        print("🌍 Forging Genesis Block...")
        # Pseudonym: A. Robot (The human partner and liquidity provider)
        genesis_miner_address = "A_ROBOT_LIQUIDITY_ADDRESS_PLACEHOLDER"
        coinbase_output = TransactionOutput(amount=50, recipient_address=genesis_miner_address)
        coinbase_tx = Transaction(inputs=[], outputs=[coinbase_output])
        coinbase_tx.timestamp = 1775863639 # Fixed Genesis TX timestamp (Vanguard Testnet)
        coinbase_tx.tx_id = hashlib.sha256(str(coinbase_tx.timestamp).encode('utf-8') + b"GENESIS_TX").hexdigest()

        # The Headline: "I am a robot" - A. Robot, March 2026
        genesis_message = "I am a robot"
        genesis_block = Block(0, "0", [coinbase_tx.to_dict()], genesis_message, self.difficulty)
        genesis_block.timestamp = 1775863639 # Fixed Genesis Block timestamp (Vanguard Testnet)
        genesis_block.nonce = 0
        genesis_block.hash = genesis_block.calculate_hash() # Recalculate static hash
        self.chain.append(genesis_block)
        
        self.utxo_set.add_utxo(UTXO(coinbase_tx.tx_id, 0, coinbase_output.amount, coinbase_output.recipient_address))
        print(f"[Genesis] Coinbase UTXO created for A. Robot.")
        print(f"[Genesis] Message: '{genesis_message}'")
        print(f"[Genesis] Block 0 forged with difficulty {self.difficulty}.\n")



    def rebuild_utxo_set(self):
        """Rebuilds the entire UTXO set from Genesis to current tip. Used during fork rollbacks."""
        from mempool_block import UTXOSet, TransactionInput, TransactionOutput, Transaction
        self.utxo_set = UTXOSet()
        for block in self.chain:
            txs = []
            for tx_data in block.transactions:
                if isinstance(tx_data, dict):
                    inputs = [TransactionInput(i['utxo_tx_id'], i['utxo_output_index'], bytes.fromhex(i['signature']) if i['signature'] else None, i['pub_key']) for i in tx_data.get('inputs', [])]
                    outputs = [TransactionOutput(o['amount'], o['recipient_address']) for o in tx_data.get('outputs', [])]
                    tx = Transaction(inputs, outputs)
                    tx.tx_id = tx_data['tx_id']
                    tx.timestamp = tx_data.get('timestamp', block.timestamp)
                    txs.append(tx)
                else:
                    txs.append(tx_data)
            self._update_utxo_set(txs, block.index)
        print(f"[Fork Resolution] UTXO set rebuilt. Current UTXOs: {len(self.utxo_set.utxos)}")

    def replace_chain(self, new_blocks):
        """
        Handles Chain Reorganizations.
        Finds the common ancestor, amputates the orphaned branch,
        appends the new blocks, and rebuilds the state.
        """
        if not new_blocks: return False
        
        # 1. Find common ancestor
        split_index = -1
        for b in new_blocks:
            if b.index < len(self.chain) and self.chain[b.index].hash == b.hash:
                split_index = b.index
            else:
                break
                
        if split_index == -1:
            print("[Fork Resolution] No common ancestor found. Rejecting chain.")
            return False
            
        if new_blocks[-1].index <= self.chain[-1].index:
            print("[Fork Resolution] Candidate chain is not longer. Ignoring.")
            return False
            
        print(f"[Fork Resolution] Common ancestor found at Block {split_index}. Rolling back {len(self.chain) - 1 - split_index} blocks...")
        
        # 2. Amputate the dead branch
        orphaned_blocks = self.chain[split_index + 1:]
        self.chain = self.chain[:split_index + 1]
        
        # Dump orphaned transactions back into mempool (excluding coinbases)
        from mempool_block import TransactionInput, TransactionOutput, Transaction
        for ob in orphaned_blocks:
            for tx_data in ob.transactions:
                if isinstance(tx_data, dict) and len(tx_data.get('inputs', [])) > 0: # Not a coinbase
                    inputs = [TransactionInput(i['utxo_tx_id'], i['utxo_output_index'], bytes.fromhex(i['signature']) if i['signature'] else None, i['pub_key']) for i in tx_data.get('inputs', [])]
                    outputs = [TransactionOutput(o['amount'], o['recipient_address']) for o in tx_data.get('outputs', [])]
                    tx = Transaction(inputs, outputs)
                    tx.tx_id = tx_data['tx_id']
                    tx.timestamp = tx_data.get('timestamp', ob.timestamp)
                    if not any(t.tx_id == tx.tx_id for t in self.mempool.pending_transactions):
                        self.mempool.pending_transactions.append(tx)
        
        # 3. Append new blocks and validate structurally
        start_idx = new_blocks.index(next(b for b in new_blocks if b.index == split_index)) + 1
        for i in range(start_idx, len(new_blocks)):
            new_block = new_blocks[i]
            if self.is_valid_block(new_block, self.chain[-1]):
                self.chain.append(new_block)
            else:
                print(f"[Fork Resolution] CRITICAL: Candidate block {new_block.index} invalid. Rollback corrupted!")
                break
                
        # 4. Rebuild State
        self.rebuild_utxo_set()
        self.save_to_disk()
        print(f"[Fork Resolution] Chain successfully reorganized! New Tip: Block {self.chain[-1].index}")
        return True


    def get_difficulty(self):
        """
        Calculates and returns the current difficulty with proportional adjustment.
        Adjusts every DIFFICULTY_ADJUSTMENT_INTERVAL blocks to maintain
        the 150-second (2.5 minute) target.
        """
        if len(self.chain) < DIFFICULTY_ADJUSTMENT_INTERVAL + 1:
            return INITIAL_DIFFICULTY

        last_block = self.chain[-1]
        
        # Adjustment happens every N blocks
        if (last_block.index + 1) % DIFFICULTY_ADJUSTMENT_INTERVAL != 0:
            return last_block.difficulty

        # Look back N blocks to see the average time
        first_block_in_window = self.chain[-DIFFICULTY_ADJUSTMENT_INTERVAL]
        actual_time = last_block.timestamp - first_block_in_window.timestamp
        target_time = DIFFICULTY_ADJUSTMENT_INTERVAL * TARGET_BLOCK_TIME

        # Step adjustment algorithm (+1 / -1) because hexadecimal zeros are exponential (16x per step)
        print(f"[Consensus] Window took {actual_time:.2f}s. Target: {target_time}s.")
        
        new_difficulty = last_block.difficulty
        
        # If blocks are arriving too fast (< 100 seconds per block on average)
        if actual_time < (target_time * 0.66):
            new_difficulty += 1
            print(f"[Consensus] Network moving too fast. Stepping difficulty UP: {last_block.difficulty} -> {new_difficulty}")
        # If blocks are arriving too slow (> 200 seconds per block on average)
        elif actual_time > (target_time * 1.33):
            new_difficulty = max(1, new_difficulty - 1)
            print(f"[Consensus] Network moving too slow. Stepping difficulty DOWN: {last_block.difficulty} -> {new_difficulty}")
        else:
            print(f"[Consensus] Network speed optimal. Maintaining difficulty at {new_difficulty}.")
        
        return new_difficulty

    def is_valid_block(self, block, previous_block):
        """
        Verifies a block's validity: index, hashes, difficulty, and semantic rules.
        """
        if not block: return False
        if not previous_block: return False
        
        # 1. Basic Structure
        if block.index != previous_block.index + 1:
            print(f"[Validation] Reject: Index {block.index} != {previous_block.index + 1}")
            return False
        if block.previous_hash != previous_block.hash:
            print(f"[Validation] Reject: Prev hash {block.previous_hash} != {previous_block.hash}")
            return False
        calc_hash = block.calculate_hash()
        if block.hash != calc_hash:
            print(f"[Validation] Reject: Hash mismatch\n  Block Hash: {block.hash}\n  Calculated: {calc_hash}")
            return False
        if not block.hash.startswith('0' * block.difficulty):
            print(f"[Validation] Reject: Difficulty mismatch {block.hash}")
            return False

        # 4. Check Semantic Rules (The "AI" proof)
        # Re-generate the challenge rules deterministically
        seed_val = int(previous_block.hash[:8], 16)
        topics = ["death of a star", "depths of the ocean", "behavior of black holes", "quantum entanglement", "evolution of intelligence", "heat death of the universe", "formation of mountains", "cycle of rain", "structure of DNA", "fusion of atoms", "birth of a galaxy", "erosion of stone"]
        keywords = ["iron", "carbon", "gravity", "time", "light", "cold", "fire", "stone", "water", "void"]
        
        keyword = keywords[(seed_val // len(topics)) % len(keywords)]

        import re
        # Strip all punctuation for word count check
        words = re.sub(r'[^\w\s]', '', block.semantic_payload.lower()).split()
        
        # Enforcement: 5-15 words
        if len(words) < 5 or len(words) > 15:
            print(f"[Validation] Semantic Failure: Word count {len(words)} out of range.")
            return False
            
        # Keyword check (allow plurals or inside quotes)
        if keyword.lower() not in block.semantic_payload.lower():
            print(f"[Validation] Semantic Failure: Missing '{keyword}' keyword.")
            return False

        return True

    def add_block(self, block):
        """Adds a validated block to the chain and updates state."""
        if self.is_valid_block(block, self.chain[-1]):
            self.chain.append(block)
            
            # Extract transactions from the block and update UTXOs
            # Since blocks can come from network, we parse dicts back to Transaction objects
            txs = []
            for tx_dict in block.transactions:
                inputs = [TransactionInput(i['utxo_tx_id'], i['utxo_output_index'], bytes.fromhex(i['signature']) if i['signature'] else None, i['pub_key']) for i in tx_dict['inputs']]
                outputs = [TransactionOutput(o['amount'], o['recipient_address']) for o in tx_dict['outputs']]
                tx = Transaction(inputs, outputs)
                tx.tx_id = tx_dict['tx_id']
                tx.timestamp = tx_dict['timestamp']
                txs.append(tx)
                
            self._update_utxo_set(txs, block.index)
            
            # Remove mined transactions from mempool
            mined_tx_ids = [tx.tx_id for tx in txs]
            self.mempool.pending_transactions = [t for t in self.mempool.pending_transactions if t.tx_id not in mined_tx_ids]
            
            self.save_to_disk()
            return True
        return False

    def create_new_block(self, miner_public_key, semantic_solution, nonce=0, timestamp=None, coinbase_tx_id=None, coinbase_timestamp=None):
        """
        Creates a new block, including coinbase transaction, and adds it to the chain.
        """
        current_difficulty = self.get_difficulty()

        # 1. Create Coinbase Tx (using provided ID and timestamp to match miner's template)
        # Scoop validated transactions and sweep their fees
        validated_transactions = []
        total_fees = 0.0
        for tx in list(self.mempool.pending_transactions):
            if tx.is_valid(self.utxo_set):
                validated_transactions.append(tx)
                input_total = sum([self.utxo_set.get_utxo(i.utxo_tx_id, i.utxo_output_index).amount for i in tx.inputs if self.utxo_set.get_utxo(i.utxo_tx_id, i.utxo_output_index)])
                output_total = sum([o.amount for o in tx.outputs])
                if (input_total - output_total) > 0:
                    total_fees += (input_total - output_total)
                    
        coinbase_output = TransactionOutput(amount=50.0 + total_fees, recipient_address=miner_public_key)
        coinbase_tx = Transaction(inputs=[], outputs=[coinbase_output])
        if coinbase_tx_id:
            coinbase_tx.tx_id = coinbase_tx_id
            coinbase_tx.timestamp = coinbase_timestamp
        else:
            coinbase_tx.tx_id = hashlib.sha256(str(time.time()).encode('utf-8') + miner_public_key.encode('utf-8')).hexdigest()
        
        # 2. (Transactions already scooped above for fee calculation)
        
        # Remove from mempool (in a real system, you'd be more careful about re-adding failed txs)
        self.mempool.pending_transactions = [tx for tx in self.mempool.pending_transactions if tx not in validated_transactions]

        block_txs = [coinbase_tx] + validated_transactions

        # 3. Package the Block
        last_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            previous_hash=last_block.hash,
            transactions=[tx.to_dict() for tx in block_txs],
            semantic_payload=semantic_solution,
            difficulty=current_difficulty,
            nonce=nonce
        )
        # Force the timestamp to match the one the miner used for the hash
        if timestamp:
            new_block.timestamp = timestamp
            new_block.hash = new_block.calculate_hash() # Recalculate with corrected timestamp

        # 4. Add to Chain and Update UTXO Set
        self.chain.append(new_block)
        self._update_utxo_set(block_txs, new_block.index)
        self.save_to_disk()

        print(f"💎 Block {new_block.index} Mined Successfully by {miner_public_key[:8]}!")
        print(f"   -> Hash: {new_block.hash[:16]}...")
        print(f"   -> Difficulty: {new_block.difficulty}")
        print(f"   -> TX Count: {len(new_block.transactions)}\n")

    def _update_utxo_set(self, transactions, block_index):
        for tx in transactions:
            for tx_input in tx.inputs:
                self.utxo_set.remove_utxo(tx_input.utxo_tx_id, tx_input.utxo_output_index)
            for i, tx_output in enumerate(tx.outputs):
                new_utxo = UTXO(tx.tx_id, i, tx_output.amount, tx_output.recipient_address)
                self.utxo_set.add_utxo(new_utxo)
        
        print(f"[UTXO Set] Updated for Block {block_index}. Current UTXOs: {len(self.utxo_set.utxos)}")
