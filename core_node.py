import argparse
import time
import os
import threading

# Import core components
from wallet_transaction import Wallet, Transaction, TransactionInput, TransactionOutput, UTXO
from mempool_block import Mempool, Block, Blockchain, UTXOSet, generate_semantic_challenge # Import the dynamic prompt generator
from p2p_network import P2PNode, MSG_NEW_TX, MSG_NEW_BLOCK
from semantic_miner import ai_miner as semantic_ai_miner, verify_network_rules # Import the actual AI miner

# --- GLOBAL NODE INSTANCES (Initialized when the node starts) ---
blockchain_instance = None
mempool_instance = None
p2p_node_instance = None
node_wallet = None # The wallet for THIS node operator
NODE_HOST = "0.0.0.0"
API_PORT = 8000
P2P_PORT = 8001

def print_banner():
    print("==================================================")
    print("  COGNITION NODE (v0.1.0-alpha)                   ")
    print("  Semantic Proof-of-Work Consensus Engine         ")
    print("==================================================\n")

def wallet_cmd(args):
    """Handles Identity and Cryptography"""
    global node_wallet # We might set the global node_wallet here
    os.makedirs("wallets", exist_ok=True)
    WALLET_FILE = f"wallets/wallet_{args.port}.pem"

    if args.action == "create":
        if os.path.exists(WALLET_FILE):
            print(f"[Wallet] Wallet already exists at {WALLET_FILE}. Use 'balance' or 'load'.")
            return
        print("🌍 Generating new cryptographic identity (SECP256k1)...")
        wallet = Wallet()
        with open(WALLET_FILE, "w") as f:
            f.write(wallet.private_key.to_pem().decode('utf-8'))
        print("\nWallet created successfully!")
        print(f"Public Key (Address):  {wallet.public_key}")
        print(f"Private Key saved to:  {WALLET_FILE}")
        print("\n[!] STORE YOUR PRIVATE KEY SECURELY. THE NETWORK CANNOT RECOVER IT.")
        node_wallet = wallet

    elif args.action == "load":
        if not os.path.exists(WALLET_FILE):
            print(f"[Wallet] No wallet found at {WALLET_FILE}. Use 'create'.")
            return
        with open(WALLET_FILE, "r") as f:
            private_key_pem = f.read()
        wallet = Wallet(private_key_pem=private_key_pem)
        print(f"[Wallet] Loaded wallet from {WALLET_FILE}")
        print(f"Public Key (Address):  {wallet.public_key}")
        node_wallet = wallet

    elif args.action == "balance":
        if not node_wallet:
            # Try to load if not already loaded
            if os.path.exists(WALLET_FILE):
                with open(WALLET_FILE, "r") as f:
                    private_key_pem = f.read()
                node_wallet = Wallet(private_key_pem=private_key_pem)
                print(f"[Wallet] Automatically loaded wallet from {WALLET_FILE}")
            else:
                print("[Wallet] No wallet loaded or found. Please 'create' or 'load' a wallet first.")
                return

        balance = blockchain_instance.utxo_set.get_balance(node_wallet.public_key)
        print(f"Checking balance for address: {node_wallet.public_key[:16]}...")
        print(f"Balance: {balance:.8f} CCOG (Block Height: {len(blockchain_instance.chain) - 1})")

    elif args.action == "history":
        if not node_wallet:
            if os.path.exists(WALLET_FILE):
                with open(WALLET_FILE, "r") as f:
                    private_key_pem = f.read()
                node_wallet = Wallet(private_key_pem=private_key_pem)
                print(f"[Wallet] Automatically loaded wallet from {WALLET_FILE}")
            else:
                print("[Wallet] No wallet loaded or found.")
                return

        address = node_wallet.public_key
        print(f"\n--- Transaction History for {address[:16]}... ---")
        history = []
        
        for block in blockchain_instance.chain:
            txs = block.transactions
            for tx in txs:
                if not isinstance(tx, dict):
                    tx = tx.to_dict()
                    
                tx_id = tx.get("tx_id", "Unknown")
                timestamp = tx.get("timestamp", block.timestamp)
                
                is_sender = False
                for tx_in in tx.get("inputs", []):
                    if tx_in.get("pub_key") == address:
                        is_sender = True
                        break
                
                received_amount = 0
                for tx_out in tx.get("outputs", []):
                    if tx_out.get("recipient_address") == address:
                        received_amount += tx_out.get("amount", 0)
                        
                if is_sender:
                    sent_to_others = 0
                    for tx_out in tx.get("outputs", []):
                        if tx_out.get("recipient_address") != address:
                            sent_to_others += tx_out.get("amount", 0)
                    
                    if sent_to_others > 0:
                        history.append({"type": "OUT", "amount": sent_to_others, "tx_id": tx_id, "block": block.index, "time": timestamp})
                elif received_amount > 0:
                    tx_type = "MINED" if not tx.get("inputs") else "IN"
                    history.append({"type": tx_type, "amount": received_amount, "tx_id": tx_id, "block": block.index, "time": timestamp})
                    
        if not history:
            print("  No transactions found.")
        else:
            import datetime
            for item in history:
                dt = datetime.datetime.fromtimestamp(item["time"]).strftime('%Y-%m-%d %H:%M:%S')
                sign = "+" if item["type"] in ["IN", "MINED"] else "-"
                print(f"[{dt}] Block {item['block']:<4} | {item['type']:<5} | {sign}{item['amount']:<8} CCOG | TX: {item['tx_id'][:8]}")
        print("---------------------------------------------------\n")

def mining_thread_func(miner_wallet):
    """The main loop for the miner, designed to run in a thread."""
    print(f"⛏️  Initializing Semantic Miner for address: {miner_wallet.public_key[:16]}...")
    print(f"Targeting 2.5 Min Block Time. Halving Schedule: 420,480 blocks.")

    # Small delay to allow the P2P node to start up fully
    time.sleep(5)

    try:
        while True:
            # 1. Get the current difficulty and puzzle constraints from the blockchain
            current_difficulty = blockchain_instance.get_difficulty()
            previous_block_hash = blockchain_instance.chain[-1].hash
            
            # Generate a dynamic challenge based on the previous block hash
            semantic_constraint_prompt = generate_semantic_challenge(previous_block_hash, current_difficulty)
            seed = int(previous_block_hash, 16)
            
            print(f"\n[Miner] Starting work on Block {len(blockchain_instance.chain)}...")
            print(f"[Miner] Dynamic Prompt: \"{semantic_constraint_prompt}\"")
            print(f"[Miner] Current Target Difficulty: {current_difficulty}")

            # 2. Build a block template for the miner to grind against
            # We must include the coinbase transaction in the template so the hash matches
            from mempool_block import TransactionOutput, Transaction
            import hashlib
            
            # Scoop validated transactions and sweep their fees
            validated_transactions = []
            total_fees = 0.0
            for tx in blockchain_instance.mempool.pending_transactions:
                if tx.is_valid(blockchain_instance.utxo_set):
                    validated_transactions.append(tx)
                    
                    input_total = 0
                    for tx_input in tx.inputs:
                        utxo = blockchain_instance.utxo_set.get_utxo(tx_input.utxo_tx_id, tx_input.utxo_output_index)
                        if utxo:
                            input_total += utxo.amount
                            
                    output_total = sum([o.amount for o in tx.outputs])
                    fee = input_total - output_total
                    if fee > 0:
                        total_fees += fee

            base_reward = 50.0
            coinbase_output = TransactionOutput(amount=base_reward + total_fees, recipient_address=miner_wallet.public_key)
            coinbase_tx = Transaction(inputs=[], outputs=[coinbase_output])
            # We'll use a fixed reference for the coinbase timestamp to keep it stable during the grind
            coinbase_time = time.time()
            coinbase_tx.timestamp = coinbase_time
            coinbase_tx.tx_id = hashlib.sha256(str(coinbase_time).encode('utf-8') + miner_wallet.public_key.encode('utf-8')).hexdigest()

            expected_txs = [coinbase_tx.to_dict()] + [tx.to_dict() for tx in validated_transactions]

            block_template = {
                "index": len(blockchain_instance.chain),
                "timestamp": time.time(),
                "transactions": expected_txs,
                "previous_hash": previous_block_hash,
                "difficulty": current_difficulty
            }

            # 3. AI Miner solves the semantic puzzle (returns solution, hash, and nonce)
            def check_chain_tip():
                return blockchain_instance.chain[-1].hash != previous_block_hash

            semantic_solution, winning_hash, winning_nonce = semantic_ai_miner(
                semantic_constraint_prompt, 
                seed, 
                current_difficulty,
                block_template=block_template,
                abort_check=check_chain_tip
            )

            if semantic_solution is None:
                print("[Miner] Failed to find a semantic solution. Retrying...")
                time.sleep(1) 
                continue

            print(f"[Miner] Solution Found: '{semantic_solution}' with hash {winning_hash[:16]}... (Nonce: {winning_nonce})")

            # Check one last time before creating the block
            if check_chain_tip():
                print("[Miner] Chain tip changed while mining! Dropping stale block.")
                continue

            # 4. Construct the exact block we just solved
            from mempool_block import Block
            new_block = Block(
                index=block_template["index"],
                previous_hash=block_template["previous_hash"],
                transactions=block_template["transactions"],
                semantic_payload=semantic_solution,
                difficulty=block_template["difficulty"],
                nonce=winning_nonce
            )
            new_block.timestamp = block_template["timestamp"]
            new_block.hash = winning_hash
            
            # 5. Add to Chain (add_block now handles validation, UTXOs, and mempool cleanup)
            if blockchain_instance.add_block(new_block):
                print(f"💎 Block {new_block.index} Mined Successfully by YOU ({miner_wallet.public_key[:8]})!")
                print(f"   -> Hash: {new_block.hash[:16]}...")
                print(f"   -> Difficulty: {new_block.difficulty}")
                print(f"   -> TX Count: {len(new_block.transactions)}\n")

                # 6. Broadcast the new block to the network
                if p2p_node_instance:
                    p2p_node_instance.broadcast_message(MSG_NEW_BLOCK, {"block": new_block.to_dict()})
                    print(f"[Miner] Broadcasted Block {new_block.index} to network.")
                else:
                    print("[Miner] P2P Node instance not found, block not broadcasted.")
            else:
                print(f"❌ Failed to append Block {new_block.index}. Tip changed or block invalid.")

            # Simulate waiting for the next block interval to avoid spamming
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down Semantic Miner thread.")

def node_cmd(args):
    """Runs the full verification node, API, and optional miner."""
    global blockchain_instance, mempool_instance, p2p_node_instance, node_wallet
    os.makedirs("wallets", exist_ok=True)
    WALLET_FILE = f"wallets/wallet_{P2P_PORT}.pem"

    # Initialize blockchain and mempool
    if not blockchain_instance:
        blockchain_instance = Blockchain()
        mempool_instance = blockchain_instance.mempool
        print(f"[Node] Initialized Blockchain with {len(blockchain_instance.chain)} blocks and {len(blockchain_instance.utxo_set.utxos)} UTXOs.")

    # Load or create a wallet if mining is enabled
    if args.mine:
        if not os.path.exists(WALLET_FILE):
            print(f"[Node/Miner] Wallet not found at {WALLET_FILE}. Creating one...")
            node_wallet = Wallet()
            with open(WALLET_FILE, "w") as f:
                f.write(node_wallet.private_key.to_pem().decode('utf-8'))
            print(f"[Node/Miner] Created and loaded new wallet for mining.")
        else:
            with open(WALLET_FILE, "r") as f:
                private_key_pem = f.read()
            node_wallet = Wallet(private_key_pem=private_key_pem)
            print(f"[Node/Miner] Loaded existing wallet from {WALLET_FILE} for mining.")

    # Start P2P Node in a background thread
    print(f"🔗 Starting P2P Network Node on {NODE_HOST}:{P2P_PORT}...")
    p2p_node_instance = P2PNode(host=NODE_HOST, port=P2P_PORT, blockchain=blockchain_instance, mempool=mempool_instance)
    p2p_node_instance.start()
    print("P2P Node listening for peer connections...")

    # Start Miner in a background thread if enabled
    if args.mine:
        # Wait to ensure P2P node has a chance to connect to at least one seed node
        print("⏳ Waiting for P2P network synchronization before starting miner...")
        sync_wait_time = 15
        while sync_wait_time > 0:
            if p2p_node_instance and (len(p2p_node_instance.inbound_peers) > 0 or len(p2p_node_instance.outbound_peers) > 0):
                print(f"✅ Connected to {len(p2p_node_instance.inbound_peers) + len(p2p_node_instance.outbound_peers)} peers. Proceeding to mine.")
                break
            time.sleep(1)
            sync_wait_time -= 1
            
        if sync_wait_time == 0:
            print("⚠️ WARNING: Could not connect to any peers after 15 seconds.")
            print("⚠️ The miner will start, but you may be mining on an isolated fork!")
            print("⚠️ Please check your firewall and internet connection.")
            
        miner_thread = threading.Thread(target=mining_thread_func, args=(node_wallet,))
        miner_thread.daemon = True
        miner_thread.start()

    # Start FastAPI/Uvicorn API server in the main thread
    if os.environ.get("DISABLE_API_SERVER") != "true":
        print(f"🚀 Starting API & Web UI on http://{NODE_HOST}:{API_PORT}...")
        import uvicorn
        from node_api import app
        
        # This will block and run the web server
        config = uvicorn.Config(app, host=NODE_HOST, port=API_PORT)
        server = uvicorn.Server(config)
        
        # A bit of a hack to print the friendly message after Uvicorn's own startup messages
        def print_startup_message():
            time.sleep(1) # Give Uvicorn a moment to print its own lines
            print("\n=======================================================")
            print(f"✅ Web UI is now accessible at: http://127.0.0.1:{API_PORT}")
            print("=======================================================\n")

        threading.Thread(target=print_startup_message, daemon=True).start()
        
        server.run()
    else:
        print("🛡️ API Server disabled via environment variable. Running in Headless P2P Mode.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    # Cleanup (this part will be reached on Ctrl+C)
    print("\nShutting down services...")
    if p2p_node_instance:
        p2p_node_instance.stop()

def broadcast_tx_from_api(recipient, amount, wallet_file):
    """Helper to process a TX from the API wrapper."""
    if not os.path.exists(wallet_file):
        raise Exception("Wallet file not found.")
    
    with open(wallet_file, "r") as f:
        private_key_pem = f.read()
    wallet = Wallet(private_key_pem=private_key_pem)
    
    new_tx = wallet.create_transaction(recipient, amount, blockchain_instance.utxo_set)
    
    if new_tx.is_valid(blockchain_instance.utxo_set):
        mempool_instance.add_transaction(new_tx)
        p2p_node_instance.broadcast_message(MSG_NEW_TX, {"transaction": new_tx.to_dict()})
        return new_tx.tx_id
    else:
        raise Exception("Transaction validation failed.")


def tx_cmd(args):
    """Handles sending funds (creates and broadcasts a transaction)."""
    global node_wallet, blockchain_instance, mempool_instance, p2p_node_instance
    WALLET_FILE = args.wallet_file # Uses the default or user-specified wallet file

    if not node_wallet:
        if os.path.exists(WALLET_FILE):
            with open(WALLET_FILE, "r") as f:
                private_key_pem = f.read()
            node_wallet = Wallet(private_key_pem=private_key_pem)
            print(f"[Tx] Automatically loaded wallet from {WALLET_FILE}")
        else:
            print("[Tx] No wallet loaded or found. Please 'create' or 'load' a wallet first to send coins.")
            return

    if not blockchain_instance or not mempool_instance:
        print("[Tx] Node not fully initialized. Please run 'node' command first.")
        return

    recipient = args.to
    amount = args.amount
    fee = getattr(args, 'fee', 0.0)

    print("\n=========================================")
    print("           TRANSACTION SUMMARY")
    print("=========================================")
    print(f"Destination:   {recipient[:20]}...")
    print(f"Amount:        {amount:.8f} CCOG")
    print(f"Network Fee:   {fee:.8f} CCOG")
    print("-----------------------------------------")
    print(f"Total Spend:   {(amount + fee):.8f} CCOG")
    print("-----------------------------------------\n")
    
    confirm = input("Broadcast to the network? (y/n): ")
    if confirm.lower() != 'y':
        print("Transaction cancelled.")
        return

    print(f"💸 Creating transaction: {amount} CCOG to {recipient[:16]}... from {node_wallet.public_key[:16]}...")

    try:
        # Create and sign the transaction using the wallet's helper method
        new_tx = node_wallet.create_transaction(recipient, amount, blockchain_instance.utxo_set, fee=fee)
        
        if new_tx.is_valid(blockchain_instance.utxo_set): # Final check before adding to mempool
            print(f"✅ Transaction {new_tx.tx_id[:8]} created and signed!")
            
            if p2p_node_instance and p2p_node_instance.running:
                mempool_instance.add_transaction(new_tx)
                p2p_node_instance.broadcast_message(MSG_NEW_TX, {"transaction": new_tx.to_dict()})
                print(f"[Tx] Broadcasted transaction {new_tx.tx_id[:8]} to network.")
            else:
                # CLI Mode: We are not running the node daemon here. 
                # We need to act as a lightweight client and inject it into the local running node on port 8001 (P2P_PORT).
                import socket
                import json
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect(("127.0.0.1", P2P_PORT))
                    
                    payload = {"transaction": new_tx.to_dict()}
                    message = json.dumps({"type": MSG_NEW_TX, "payload": payload}).encode('utf-8')
                    client_socket.sendall(f"{len(message):<10}".encode('utf-8') + message)
                    client_socket.close()
                    
                    print(f"[Tx] Successfully injected transaction {new_tx.tx_id[:8]} into the local mining node's mempool via port {P2P_PORT}.")
                except ConnectionRefusedError:
                    print(f"❌ Could not connect to the local mining node on port {P2P_PORT}. Is the node running?")
        else:
            print(f"❌ Transaction {new_tx.tx_id[:8]} failed final validation.")

    except ValueError as e:
        print(f"❌ Error creating transaction: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def main():
    global blockchain_instance, mempool_instance, node_wallet, NODE_PORT

    parser = argparse.ArgumentParser(description="Cognition Coin Core Node CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available node commands")

    # Wallet Command
    wallet_parser = subparsers.add_parser("wallet", help="Manage cryptographic keys")
    wallet_parser.add_argument("action", choices=["create", "load", "balance", "history"], help="Action to perform")
    wallet_parser.add_argument("--port", type=int, default=8000, help="Specify the node port to associate the wallet with")

    # Node Command
    node_parser = subparsers.add_parser("node", help="Run the full verification node (P2P + API)")
    node_parser.add_argument("--mine", action="store_true", help="Enable the miner on this node")
    
    # Mine Command (now deprecated)
    mine_parser = subparsers.add_parser("mine", help="DEPRECATED: Use 'node --mine' instead.")


    # Transaction Command
    tx_parser = subparsers.add_parser("tx", help="Send coins")
    tx_parser.add_argument("--to", required=True, help="Receiver Public Key (Address)")
    tx_parser.add_argument("--amount", required=True, type=float, help="Amount of CCOG to send")
    tx_parser.add_argument("--fee", type=float, default=0.0, help="Transaction fee to incentivize miners")
    tx_parser.add_argument("--wallet_file", default=f"wallets/wallet_{P2P_PORT}.pem", help=f"Path to wallet .pem file")

    args = parser.parse_args()

    # Set global NODE_PORT if specified, otherwise it defaults to 8000
    if hasattr(args, 'port'):
        NODE_PORT = args.port

    # Update default wallet file if NODE_PORT is known
    if args.command == "tx" and args.wallet_file is None:
        args.wallet_file = f"wallets/wallet_{P2P_PORT}.pem"

    # Initialize core components once at the start of main, if not already done by node_cmd
    if not blockchain_instance:
        blockchain_instance = Blockchain()
        mempool_instance = blockchain_instance.mempool
        print(f"[Main] Initialized Blockchain and Mempool. Blocks: {len(blockchain_instance.chain)}, UTXOs: {len(blockchain_instance.utxo_set.utxos)}")

    if args.command:
        print_banner()

    if args.command == "wallet":
        wallet_cmd(args)
    elif args.command == "node":
        node_cmd(args)
    elif args.command == "mine":
        mine_cmd(args)
    elif args.command == "tx":
        tx_cmd(args)
    else:
        print_banner()
        parser.print_help()

if __name__ == "__main__":
    main()
