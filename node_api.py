from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import core_node
import os
import time
from mempool_block import DEFAULT_BLOCKCHAIN_FILE # Import the canonical file path

# --- Globals for the smart reloading mechanism ---
_last_chain_mod_time = 0
# The blockchain_instance is now managed by the smart_reload function.

app = FastAPI(title="Cognition Coin Node API")

# Allow local web access if running dashboard on different port/domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def smart_reload_blockchain():
    """
    Checks the blockchain file's modification time. If it's newer, it reloads 
    the global instance from disk. This is fast and ensures data is always fresh.
    """
    global _last_chain_mod_time, core_node
    
    try:
        current_mod_time = os.path.getmtime(DEFAULT_BLOCKCHAIN_FILE)
        
        if current_mod_time > _last_chain_mod_time:
            print(f"[API] Blockchain file has changed. Reloading from disk...")
            core_node.blockchain_instance = core_node.Blockchain()
            _last_chain_mod_time = current_mod_time
            print("[API] Reload complete.")
            
    except FileNotFoundError:
        print("[API] Blockchain file not found. Using initial in-memory instance.")
        if not core_node.blockchain_instance:
             core_node.blockchain_instance = core_node.Blockchain()
        _last_chain_mod_time = time.time()
        
    except Exception as e:
        print(f"[API] Error during smart reload: {e}")
        pass
        
    return core_node.blockchain_instance


@app.get("/")
async def serve_dashboard():
    """Serves the local Web GUI Dashboard"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Cognition Node API is running. GUI not found."}


@app.on_event("startup")
async def startup_event():
    # Perform an initial load on startup
    smart_reload_blockchain()


import secrets

# Secure API Token Authentication
API_TOKEN = os.getenv("COG_API_TOKEN")
if not API_TOKEN:
    API_TOKEN = secrets.token_hex(32)
    print("\n" + "="*60)
    print(" ⚠️  WARNING: No COG_API_TOKEN environment variable found. ")
    print(" 🛡️  Generated random auth token for this session:")
    print(f"     {API_TOKEN}")
    print("     Pass this in the Authorization header: Bearer <token>")
    print("="*60 + "\n")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid API Token")
    return credentials.credentials


@app.post("/wallet/generate", dependencies=[Depends(verify_token)])
async def generate_wallet(filename: str = None):
    """Generates a new wallet and saves it locally. Returns the public address."""
    from wallet_transaction import Wallet
    import os, time
    
    if not filename:
        filename = f"wallets/wallet_{int(time.time())}.pem"
        
    if os.path.exists(filename):
        raise HTTPException(status_code=400, detail=f"Wallet {filename} already exists. Refusing to overwrite.")
    
    wallet = Wallet()
    with open(filename, "w") as f:
        f.write(wallet.private_key.to_pem().decode('utf-8'))
        
    return {
        "status": "success",
        "address": wallet.public_key,
        "file": filename,
        "message": "Store this file securely. It contains your private key."
    }

# API Models
class TransactionRequest(BaseModel):
    recipient: str
    amount: float
    wallet_file: str = "wallets/wallet_8000.pem"

@app.get("/blockchain/info", dependencies=[Depends(verify_token)])
async def get_blockchain_info():
    blockchain = smart_reload_blockchain()
    return {
        "height": len(blockchain.chain),
        "difficulty": blockchain.get_difficulty(),
        "utxo_count": len(blockchain.utxo_set.utxos)
    }


@app.get("/wallet/list", dependencies=[Depends(verify_token)])
async def list_wallets():
    blockchain = smart_reload_blockchain()
    import glob
    from wallet_transaction import Wallet
    wallets = []
    for f in glob.glob("wallets/wallet_*.pem"):
        try:
            with open(f, "r") as key_file:
                w = Wallet(private_key_pem=key_file.read())
                bal = blockchain.utxo_set.get_balance(w.public_key)
                wallets.append({"file": f, "address": w.public_key, "balance": bal})
        except Exception:
            pass
    return {"wallets": wallets}


@app.get("/wallet/balance/{address}", dependencies=[Depends(verify_token)])
async def get_balance(address: str):
    blockchain = smart_reload_blockchain()
    balance = blockchain.utxo_set.get_balance(address)
    return {"address": address, "balance": balance}

@app.post("/transaction/send", dependencies=[Depends(verify_token)])
async def send_transaction(req: TransactionRequest):
    blockchain = smart_reload_blockchain()
    
    try:
        import os, socket, json
        from wallet_transaction import Wallet
        
        # Load sender wallet
        if not os.path.exists(req.wallet_file):
            raise Exception("Wallet file not found.")
        
        with open(req.wallet_file, "r") as f:
            private_key_pem = f.read()
        wallet = Wallet(private_key_pem=private_key_pem)
        
        # Create TX using a fresh copy of the blockchain state
        new_tx = wallet.create_transaction(req.recipient, req.amount, blockchain.utxo_set)
        
        if not new_tx.is_valid(blockchain.utxo_set):
            raise Exception("Transaction validation failed.")
            
        # Inject the TX into the running mining node via local socket (P2P port 8001)
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(("127.0.0.1", 8001))
            
            payload = {"transaction": new_tx.to_dict()}
            message = json.dumps({"type": "NEW_TX", "payload": payload}).encode('utf-8')
            client_socket.sendall(f"{len(message):<10}".encode('utf-8') + message)
            client_socket.close()
        except ConnectionRefusedError:
            raise Exception("Could not connect to local mining daemon on port 8001. Is it running?")
            
        return {"status": "success", "tx_id": new_tx.tx_id, "message": "Transaction injected into mempool"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/block/{index}", dependencies=[Depends(verify_token)])
async def get_block(index: int):
    blockchain = smart_reload_blockchain()
    if index >= len(blockchain.chain):
        raise HTTPException(status_code=404, detail="Block not found")
    return blockchain.chain[index].to_dict()

@app.get("/blockchain/history", dependencies=[Depends(verify_token)])
async def get_recent_history(limit: int = 10, address: str = None):
    blockchain = smart_reload_blockchain()
    
    history = []
    
    # Traverse blocks backwards for recent history
    for block in reversed(blockchain.chain):
        for tx in reversed(block.transactions):
            if not isinstance(tx, dict):
                tx = tx.to_dict()
            
            tx_id = tx.get("tx_id", "Unknown")
            timestamp = tx.get("timestamp", block.timestamp)
            
            # If no address is specified, just show all transactions
            if not address:
                history.append({
                    "type": "MINED" if not tx.get("inputs") else "TRANSFER",
                    "amount": sum(o.get("amount", 0) for o in tx.get("outputs", [])),
                    "tx_id": tx_id,
                    "block": block.index,
                    "time": timestamp
                })
                if len(history) >= limit:
                    return {"transactions": history}
                continue

            # If address is specified, determine its role
            is_sender = any(tx_in.get("pub_key") == address for tx_in in tx.get("inputs", []))
            
            received_amount = sum(tx_out.get("amount", 0) for tx_out in tx.get("outputs", []) if tx_out.get("recipient_address") == address)
            
            if is_sender:
                sent_to_others = sum(tx_out.get("amount", 0) for tx_out in tx.get("outputs", []) if tx_out.get("recipient_address") != address)
                if sent_to_others > 0:
                    history.append({"type": "SENT", "amount": sent_to_others, "tx_id": tx_id, "block": block.index, "time": timestamp})

            elif received_amount > 0:
                tx_type = "MINED" if not tx.get("inputs") else "RECEIVED"
                history.append({"type": tx_type, "amount": received_amount, "tx_id": tx_id, "block": block.index, "time": timestamp})

            if len(history) >= limit:
                break
        if len(history) >= limit:
            break
            
    return {"transactions": history}
