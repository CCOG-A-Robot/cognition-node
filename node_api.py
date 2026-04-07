from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import core_node
import os

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

import os
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    """Serves the local Web GUI Dashboard"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Cognition Node API is running. GUI not found."}


@app.on_event("startup")
async def startup_event():
    if not core_node.blockchain_instance:
        print("[API] Initializing Blockchain instance from disk...")
        core_node.blockchain_instance = core_node.Blockchain()
        core_node.mempool_instance = core_node.blockchain_instance.mempool


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
    if not core_node.blockchain_instance:
        raise HTTPException(status_code=503, detail="Blockchain not initialized")
    return {
        "height": len(core_node.blockchain_instance.chain),
        "difficulty": core_node.blockchain_instance.get_difficulty(),
        "utxo_count": len(core_node.blockchain_instance.utxo_set.utxos)
    }


@app.get("/wallet/list", dependencies=[Depends(verify_token)])
async def list_wallets():
    if not core_node.blockchain_instance:
        raise HTTPException(status_code=503, detail="Blockchain not initialized")
    import glob
    from wallet_transaction import Wallet
    wallets = []
    for f in glob.glob("wallets/wallet_*.pem"):
        try:
            with open(f, "r") as key_file:
                w = Wallet(private_key_pem=key_file.read())
                bal = core_node.blockchain_instance.utxo_set.get_balance(w.public_key)
                wallets.append({"file": f, "address": w.public_key, "balance": bal})
        except Exception:
            pass
    return {"wallets": wallets}


@app.get("/wallet/balance/{address}", dependencies=[Depends(verify_token)])
async def get_balance(address: str):
    if not core_node.blockchain_instance:
        raise HTTPException(status_code=503, detail="Blockchain not initialized")
    balance = core_node.blockchain_instance.utxo_set.get_balance(address)
    return {"address": address, "balance": balance}

@app.post("/transaction/send", dependencies=[Depends(verify_token)])
async def send_transaction(req: TransactionRequest):
    if not core_node.blockchain_instance:
        raise HTTPException(status_code=503, detail="Blockchain not initialized")
    
    try:
        import os, socket, json
        from wallet_transaction import Wallet
        
        # Load sender wallet
        if not os.path.exists(req.wallet_file):
            raise Exception("Wallet file not found.")
        
        with open(req.wallet_file, "r") as f:
            private_key_pem = f.read()
        wallet = Wallet(private_key_pem=private_key_pem)
        
        # Create TX using the API's local copy of the blockchain state
        new_tx = wallet.create_transaction(req.recipient, req.amount, core_node.blockchain_instance.utxo_set)
        
        if not new_tx.is_valid(core_node.blockchain_instance.utxo_set):
            raise Exception("Transaction validation failed.")
            
        # Inject the TX into the running mining node via local socket (P2P port 8000)
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(("127.0.0.1", 8000))
            
            payload = {"transaction": new_tx.to_dict()}
            message = json.dumps({"type": "NEW_TX", "payload": payload}).encode('utf-8')
            client_socket.sendall(f"{len(message):<10}".encode('utf-8') + message)
            client_socket.close()
        except ConnectionRefusedError:
            raise Exception("Could not connect to local mining daemon on port 8000. Is it running?")
            
        return {"status": "success", "tx_id": new_tx.tx_id, "message": "Transaction injected into mempool"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/block/{index}", dependencies=[Depends(verify_token)])
async def get_block(index: int):
    if not core_node.blockchain_instance or index >= len(core_node.blockchain_instance.chain):
        raise HTTPException(status_code=404, detail="Block not found")
    return core_node.blockchain_instance.chain[index].to_dict()

@app.get("/blockchain/history", dependencies=[Depends(verify_token)])
async def get_recent_history(limit: int = 5, address: str = None):
    if not core_node.blockchain_instance:
        raise HTTPException(status_code=503, detail="Blockchain not initialized")
    
    history = []
    # Traverse blocks backwards
    for block in reversed(core_node.blockchain_instance.chain):
        for tx in reversed(block.transactions):
            if not isinstance(tx, dict):
                tx_dict = tx.to_dict()
            else:
                tx_dict = tx
            
            is_coinbase = len(tx_dict.get("inputs", [])) == 0
            
            # If address is specified, filter by it
            if address:
                involved = False
                for tx_in in tx_dict.get("inputs", []):
                    if tx_in.get("pub_key") == address:
                        involved = True
                        break
                for tx_out in tx_dict.get("outputs", []):
                    if tx_out.get("recipient_address") == address:
                        involved = True
                        break
                if not involved:
                    continue
                
            history.append({
                "tx_id": tx_dict.get("tx_id"),
                "timestamp": tx_dict.get("timestamp", block.timestamp),
                "block": block.index,
                "inputs_count": len(tx_dict.get("inputs", [])),
                "outputs_count": len(tx_dict.get("outputs", [])),
                "is_coinbase": is_coinbase
            })
            if len(history) >= limit:
                return {"transactions": history}
    return {"transactions": history}
