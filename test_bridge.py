import logging
import time
from mempool_block import Blockchain, Block
from bridge_relayer import BridgeRelayer
from wallet_transaction import Wallet, Transaction, TransactionOutput

def run_bridge_simulation():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    print("==================================================")
    print("  COGNITION COIN: BRIDGE SIMULATION (L1 -> L2)    ")
    print("==================================================\n")

    # 1. Initialize Native Blockchain
    print("[L1] Initializing Cognition Ledger...")
    blockchain = Blockchain()
    relayer = BridgeRelayer(blockchain)

    # 2. Setup Wallets
    miner_wallet = Wallet() # The sender
    vault_address = "A_ROBOT_VAULT_L1" # The bridge target
    print(f"[L1] Miner Address: {miner_wallet.public_key[:16]}...")
    print(f"[L1] Vault Address: {vault_address}\n")

    # 3. "Mine" a block to give the miner some coins
    print("[L1] Mining Block 1 to generate initial COG...")
    blockchain.create_new_block(miner_wallet.public_key, "Deterministic AI Sentence for Block 1")
    
    balance = blockchain.utxo_set.get_balance(miner_wallet.public_key)
    print(f"[L1] Miner Balance: {balance} COG\n")

    # 4. SEND COINS TO THE BRIDGE VAULT
    print(f"[L1] Sending 25 COG to the Bridge Vault...")
    # Create the bridge transaction
    tx = miner_wallet.create_transaction(vault_address, 25.0, blockchain.utxo_set)
    blockchain.mempool.add_transaction(tx)
    
    # Mine the transaction into a block so it's finalized
    blockchain.create_new_block(miner_wallet.public_key, "AI Sentence for Block 2 (Bridge TX)")
    print("[L1] Transaction finalized in Block 2.\n")

    # 5. RUN THE RELAYER
    print("[Relayer] Scanning L1 chain for vault deposits...")
    time.sleep(1)
    relayer.monitor_l1_vault()

    print("\n[Result] Simulation Complete. Native COG locked, wCOG minted.")

if __name__ == "__main__":
    run_bridge_simulation()
