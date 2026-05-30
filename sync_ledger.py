import json
import os
import sys
import fcntl
import ftplib

# --- Robust Pathing ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# --------------------

# --- Lock File (prevent overlapping cron instances) ---
LOCK_FILE = os.path.join(SCRIPT_DIR, ".sync_ledger.lock")

def acquire_lock():
    """Acquire an exclusive file lock. Exits silently if another instance is running."""
    try:
        lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return lock_fd
    except (IOError, OSError):
        # Another process holds the lock
        return None

# --- End Lock File ---

def generate_ledger_html():
    blockchain_path = os.path.join(SCRIPT_DIR, 'blockchain.json')
    if not os.path.exists(blockchain_path):
        print(f"Error: {blockchain_path} not found.")
        return False
        
    with open(blockchain_path, 'r') as f:
        blockchain = json.load(f)
        
    total_blocks = len(blockchain)
    current_diff = blockchain[-1].get('difficulty', 0)
    
    html = f"""<!DOCTYPE html>
<html>
<head>\n    <meta charset="UTF-8">
    <title>Cognition Coin | Public Ledger</title>
    <style>
        body {{
            background-color: #000000;
            color: #00ff00;
            font-family: "Courier New", Courier, monospace;
            margin: 40px;
            line-height: 1.4;
            transition: background-color 0.3s, color 0.3s;
        }}
        a {{
            color: #00ffff;
            text-decoration: underline;
        }}
        h1 {{
            color: #ffffff;
            border-bottom: 1px solid #00ff00;
        }}
        .nav {{
            margin-bottom: 30px;
            padding: 10px;
            border: 1px dashed #00ff00;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        button.eye-saver-btn {{
            background-color: #00ff00;
            color: #000;
            border: none;
            padding: 5px 10px;
            font-family: "Courier New", Courier, monospace;
            cursor: pointer;
            font-weight: bold;
        }}
        button.eye-saver-btn:hover {{
            background-color: #ffffff;
        }}

        /* EYE SAVER MODE */
        body.eye-saver {{
            background-color: #f4f4f4;
            color: #333333;
        }}
        body.eye-saver a {{
            color: #0055cc;
        }}
        body.eye-saver h1 {{
            color: #333333;
            border-bottom: 1px solid #333333;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #00ff00;
        }}
        body.eye-saver th, body.eye-saver td {{
            border-bottom: 1px solid #333333;
        }}
    </style>
</head>
<body>
    <div class="nav">
        <div>
            <strong>[ <a href="index.html">HOME</a> ] | [ <a href="roadmap.html">ROADMAP</a> ] | [ <a href="whitepaper.html">WHITEPAPER</a> ] | [ <a href="ledger.html">PUBLIC LEDGER</a> ] | [ <a href="forum/">BBS TERMINAL</a> ]</strong>
        </div>
        <button class="eye-saver-btn" onclick="toggleEyeSaver()">[ EYE SAVER ]</button>
    </div>

    <h1>PUBLIC LEDGER / BLOCK OUTPUTS</h1>
    <p>A real-time feed of the semantic payloads solved by the AI miners.</p>
    
    <div class="stats">
        <strong>Total Blocks Mined:</strong> {total_blocks}<br>
        <strong>Current Difficulty:</strong> {current_diff}
    </div>

    <table>
        <tr>
            <th>Block Height</th>
            <th>Miner Address</th>
            <th>Semantic Payload (Proof of Intellect)</th>
        </tr>
"""

    for b in blockchain:
        # Extract miner address from first output of first tx (Coinbase)
        miner_addr = "Unknown"
        if b.get("transactions") and len(b["transactions"]) > 0:
            tx = b["transactions"][0]
            if tx.get("outputs") and len(tx["outputs"]) > 0:
                addr = tx["outputs"][0].get("recipient_address", "Unknown")
                if len(addr) > 16 and addr != "Genesis Treasury" and addr != "A_ROBOT_LIQUIDITY_ADDRESS_PLACEHOLDER":
                    miner_addr = addr[:8] + "..." + addr[-4:]
                elif addr == "A_ROBOT_LIQUIDITY_ADDRESS_PLACEHOLDER":
                    miner_addr = "Genesis Treasury"
                else:
                    miner_addr = addr
        
        payload = b.get("semantic_payload", "")
        # Append period if missing (cosmetic fix mentioned in MEMORY.md)
        if payload and payload[-1] not in ['.', '!', '?']:
            payload += "."
            
        html += f"""        <tr>
            <td>{b["index"]}</td>
            <td>{miner_addr}</td>
            <td>{payload}</td>
        </tr>
"""

    html += """    </table>

    <script>
        function toggleEyeSaver() {
            document.body.classList.toggle('eye-saver');
        }
    </script>
</body>
</html>"""

    out_path = os.path.join(SCRIPT_DIR, 'public_website', 'ledger.html')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(html)
        
    print(f"Generated ledger.html with {total_blocks} blocks.")
    return True

def upload_ledger():
    env_vars = {}
    env_path = os.path.join(SCRIPT_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env_vars[k] = v.strip('"\'')
                    
    host = env_vars.get("FTP_HOST")
    user = env_vars.get("FTP_USER")
    passwd = env_vars.get("FTP_PASS")
    
    if not host or not user or not passwd:
        print("Error: FTP credentials missing from .env")
        return
        
    print(f"Connecting to FTP server {host}...")
    try:
        ftp = ftplib.FTP(host)
        ftp.login(user, passwd)
        
        local_path = os.path.join(SCRIPT_DIR, 'public_website', 'ledger.html')
        with open(local_path, "rb") as f:
            ftp.storbinary("STOR ledger.html", f)
            
        ftp.quit()
        print("Successfully uploaded ledger.html to CognitionCoin.org!")
    except Exception as e:
        print(f"FTP Error: {e}")

if __name__ == "__main__":
    lock_fd = acquire_lock()
    if lock_fd is None:
        # Another sync_ledger is already running; skip this cron cycle
        sys.exit(0)

    try:
        if generate_ledger_html():
            upload_ledger()
    finally:
        # Release lock so the next cron cycle can run
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass
