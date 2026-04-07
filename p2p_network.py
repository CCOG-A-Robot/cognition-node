import socket
import threading
import json
import time
from wallet_transaction import Transaction, TransactionInput, TransactionOutput

# --- P2P Network Configuration ---
# For a real network, these would be dynamic and discovered.
# For this prototype, we'll use a simple list of seed nodes.
SEED_NODES = [("10.0.0.248", 8000)] # Mookie
PORT = 8000 # Default port for this node
MAX_CONNECTIONS = 10 # Max number of outgoing peer connections

# --- Message Types ---
MSG_HANDSHAKE = "HANDSHAKE"        # Initial connection message
MSG_GET_PEERS = "GET_PEERS"        # Request for known peers
MSG_PEERS     = "PEERS"            # Response with known peers
MSG_NEW_TX    = "NEW_TX"           # New transaction broadcast
MSG_NEW_BLOCK = "NEW_BLOCK"        # New block broadcast
MSG_GET_BLOCKS = "GET_BLOCKS"
MSG_RESOLVE_FORK = "RESOLVE_FORK"
MSG_FORK_BLOCKS = "FORK_BLOCKS"      # Request for blocks (e.g., for syncing)
MSG_BLOCKS    = "BLOCKS"           # Response with blocks

class P2PNode:
    def __init__(self, host="127.0.0.1", port=PORT, blockchain=None, mempool=None):
        self.host = host
        self.port = port
        self.peers = {} # Dictionary to store connected peers: { (ip, port): socket_object }
        self.peer_lock = threading.Lock() # Lock for thread-safe access to peers
        self.running = True
        self.blockchain = blockchain # Reference to our blockchain instance
        self.mempool = mempool     # Reference to our mempool instance

        print(f"[P2P Node {self.port}] Initializing...")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"[P2P Node {self.port}] Listening on {self.host}:{self.port}")

    def start(self):
        # Thread to accept incoming connections
        accept_thread = threading.Thread(target=self._accept_connections)
        accept_thread.start()

        # Thread to connect to known seed nodes (and periodically discover more)
        connect_thread = threading.Thread(target=self._connect_to_seed_nodes)
        connect_thread.start()

    def stop(self):
        print(f"[P2P Node {self.port}] Shutting down...")
        self.running = False
        self.server_socket.close()
        for peer_socket in self.peers.values():
            peer_socket.close()

    def _accept_connections(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"[P2P Node {self.port}] Accepted connection from {addr}")
                with self.peer_lock:
                    self.peers[addr] = conn
                # Start a new thread to handle this client connection
                client_handler = threading.Thread(target=self._handle_connection, args=(conn, addr))
                client_handler.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running: # Only print error if node is still supposed to be running
                    print(f"[P2P Node {self.port}] Error accepting connection: {e}")
                break

    def _connect_to_seed_nodes(self):
        import socket
        # Get actual local IP to prevent self-connection when host is 0.0.0.0
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            my_ip = s.getsockname()[0]
            s.close()
        except:
            my_ip = "127.0.0.1"

        while self.running:
            # Continuously retry seed nodes
            for host, port in SEED_NODES:
                if host != my_ip and (host, port) != (self.host, self.port):
                    # connect_to_peer already checks if it's in self.peers
                    self.connect_to_peer(host, port)
            
            time.sleep(15) # Check every 15 seconds
            if self.peers:
                self.broadcast_message(MSG_GET_PEERS, {"sender_port": self.port})

    def connect_to_peer(self, host, port):
        with self.peer_lock:
            if (host, port) in self.peers:
                return # Already connected
            if len(self.peers) >= MAX_CONNECTIONS:
                print(f"[P2P Node {self.port}] Max connections reached, cannot connect to {host}:{port}")
                return

        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((host, port))
            print(f"[P2P Node {self.port}] Connected to peer {host}:{port}")
            with self.peer_lock:
                self.peers[(host, port)] = peer_socket
            
            # Send handshake message
            payload = {"port": self.port}
            if self.blockchain and self.blockchain.chain:
                payload["height"] = len(self.blockchain.chain) - 1
                payload["tip_hash"] = self.blockchain.chain[-1].hash
            self.send_message(peer_socket, MSG_HANDSHAKE, payload)

            # Start a thread to listen to this peer
            listener_thread = threading.Thread(target=self._handle_connection, args=(peer_socket, (host, port)))
            listener_thread.start()
            return True
        except Exception as e:
            print(f"[P2P Node {self.port}] Could not connect to {host}:{port}: {e}")
            return False

    def send_message(self, target_socket, msg_type, payload):
        message = json.dumps({"type": msg_type, "payload": payload}).encode('utf-8')
        try:
            # Prepend message length to handle variable-length messages
            target_socket.sendall(f"{len(message):<10}".encode('utf-8') + message)
        except Exception as e:
            print(f"[P2P Node {self.port}] Error sending message to peer: {e}")
            self._remove_peer(target_socket)

    def broadcast_message(self, msg_type, payload, exclude_peer=None):
        with self.peer_lock:
            peers_to_notify = list(self.peers.values())
        
        for peer_socket in peers_to_notify:
            if peer_socket != exclude_peer:
                self.send_message(peer_socket, msg_type, payload)

    def _handle_connection(self, conn, addr):
        buffer = b''
        while self.running:
            try:
                data = conn.recv(4096)
                if not data:
                    break # Connection closed by peer
                
                buffer += data
                
                while True:
                    if len(buffer) < 10: # Need at least 10 bytes for length header
                        break
                    
                    msg_len_str = buffer[:10].decode('utf-8')
                    if not msg_len_str.strip().isdigit(): # Basic check for valid length header
                        print(f"[P2P Node {self.port}] Invalid message length header from {addr}: {msg_len_str}")
                        break

                    msg_len = int(msg_len_str)
                    
                    if len(buffer) < 10 + msg_len: # Not enough data for full message
                        break
                    
                    # Extract message
                    message = buffer[10 : 10 + msg_len].decode('utf-8')
                    buffer = buffer[10 + msg_len:] # Remaining buffer
                    
                    self._process_message(conn, addr, json.loads(message))

            except json.JSONDecodeError as e:
                print(f"[P2P Node {self.port}] JSON decode error from {addr}: {e}")
                break
            except Exception as e:
                if self.running:
                    print(f"[P2P Node {self.port}] Connection with {addr} error: {e}")
                break
        
        print(f"[P2P Node {self.port}] Connection closed with {addr}")
        self._remove_peer(conn, addr)

    def _remove_peer(self, peer_socket, addr=None):
        with self.peer_lock:
            if addr: # If addr is known, remove by addr
                if addr in self.peers:
                    del self.peers[addr]
            else: # Otherwise, find by socket object
                for p_addr, p_sock in list(self.peers.items()):
                    if p_sock == peer_socket:
                        del self.peers[p_addr]
                        break
            try:
                peer_socket.close()
            except:
                pass

    def _process_message(self, conn, addr, message):
        msg_type = message.get("type")
        payload = message.get("payload")

        if msg_type not in [MSG_GET_PEERS, MSG_PEERS]:
            print(f"[P2P Node {self.port}] Received {msg_type} from {addr}: {payload}")

        if msg_type == MSG_HANDSHAKE:
            peer_port = payload.get("port")
            if peer_port and (addr[0], peer_port) not in self.peers:
                print(f"[P2P Node {self.port}] Adding new peer from handshake: {addr[0]}:{peer_port}")
                import threading
                threading.Thread(target=self.connect_to_peer, args=(addr[0], peer_port)).start()
            
            peer_height = payload.get("height")
            if peer_height is not None and self.blockchain:
                our_height = len(self.blockchain.chain) - 1
                if peer_height > our_height:
                    print(f"[P2P Node {self.port}] Peer is at height {peer_height}, we are at {our_height}. Requesting blocks...")
                    self.send_message(conn, MSG_GET_BLOCKS, {"from_index": our_height + 1})

        elif msg_type == MSG_GET_PEERS:
            with self.peer_lock:
                known_peers = [{"host": p_addr[0], "port": p_addr[1]} for p_addr in self.peers.keys()]
            self.send_message(conn, MSG_PEERS, {"peers": known_peers, "sender_port": self.port})

        elif msg_type == MSG_PEERS:
            for peer_info in payload.get("peers", []):
                peer_host = peer_info.get("host")
                peer_port = peer_info.get("port")
                if peer_host and peer_port and (peer_host, peer_port) != (self.host, self.port):
                    import threading
                    threading.Thread(target=self.connect_to_peer, args=(peer_host, peer_port)).start()
        
        elif msg_type == MSG_NEW_TX:
            tx_data = payload.get("transaction")
            if tx_data and self.mempool:
                try:
                    from wallet_transaction import Transaction, TransactionInput, TransactionOutput
                    inputs = [TransactionInput(i['utxo_tx_id'], i['utxo_output_index'], bytes.fromhex(i['signature']) if i['signature'] else None, i['pub_key']) for i in tx_data['inputs']]
                    outputs = [TransactionOutput(o['amount'], o['recipient_address']) for o in tx_data['outputs']]
                    new_tx = Transaction(inputs, outputs)
                    new_tx.tx_id = tx_data['tx_id']
                    new_tx.timestamp = tx_data['timestamp']

                    if new_tx.is_valid(self.blockchain.utxo_set):
                        have_tx = any(t.tx_id == new_tx.tx_id for t in self.mempool.pending_transactions)
                        if not have_tx:
                            self.mempool.add_transaction(new_tx)
                            self.broadcast_message(MSG_NEW_TX, payload, exclude_peer=conn)
                    else:
                        print(f"[P2P Node {self.port}] Received invalid transaction {new_tx.tx_id[:8]}, not adding to mempool.")
                except Exception as e:
                    print(f"[P2P Node {self.port}] Error processing NEW_TX: {e}")

        elif msg_type == MSG_NEW_BLOCK:
            block_data = payload.get("block")
            if block_data and self.blockchain:
                try:
                    from mempool_block import Block
                    block_hash = block_data.get("hash")
                    have_it = any(b.hash == block_hash for b in self.blockchain.chain)
                    if not have_it:
                        new_block = Block(
                            index=block_data["index"],
                            previous_hash=block_data["previous_hash"],
                            transactions=block_data["transactions"],
                            semantic_payload=block_data["semantic_payload"],
                            difficulty=block_data["difficulty"],
                            nonce=block_data["nonce"]
                        )
                        new_block.timestamp = block_data["timestamp"]
                        new_block.hash = block_data["hash"]
                        
                        our_height = len(self.blockchain.chain) - 1
                        if new_block.index > our_height + 1:
                            print(f"[P2P Node {self.port}] Received Block {new_block.index} from future (we are at {our_height}). Requesting sync...")
                            self.send_message(conn, MSG_GET_BLOCKS, {"from_index": our_height + 1})
                        elif self.blockchain.add_block(new_block):
                            peer_miner = block_data['transactions'][0]['outputs'][0]['recipient_address'][:8] if block_data['transactions'] else "Unknown"
                            print(f"[P2P Node {self.port}] 🌐 Block {new_block.index} accepted from network! Mined by Peer ({peer_miner})")
                            self.broadcast_message(MSG_NEW_BLOCK, payload, exclude_peer=conn)
                        else:
                            print(f"[P2P Node {self.port}] ❌ Rejected invalid block {new_block.index} from network.")
                except Exception as e:
                    print(f"[P2P Node {self.port}] Error processing NEW_BLOCK: {e}")

        elif msg_type == MSG_GET_BLOCKS:
            from_index = payload.get("from_index", 0)
            if self.blockchain:
                our_height = len(self.blockchain.chain) - 1
                if from_index <= our_height:
                    end_index = min(from_index + 50, our_height + 1)
                    blocks_to_send = [b.to_dict() for b in self.blockchain.chain[from_index:end_index]]
                    print(f"[P2P Node {self.port}] Sending blocks {from_index} to {end_index - 1} to {addr}")
                    self.send_message(conn, MSG_BLOCKS, {"blocks": blocks_to_send})

        elif msg_type == MSG_BLOCKS:
            blocks = payload.get("blocks", [])
            if blocks and self.blockchain:
                from mempool_block import Block
                added_count = 0
                for block_data in blocks:
                    new_block = Block(
                        index=block_data["index"],
                        previous_hash=block_data["previous_hash"],
                        transactions=block_data["transactions"],
                        semantic_payload=block_data["semantic_payload"],
                        difficulty=block_data["difficulty"],
                        nonce=block_data["nonce"]
                    )
                    new_block.timestamp = block_data["timestamp"]
                    new_block.hash = block_data["hash"]
                    
                    if len(self.blockchain.chain) > new_block.index and self.blockchain.chain[new_block.index].hash == new_block.hash:
                        continue
                        
                    if self.blockchain.add_block(new_block):
                        added_count += 1
                        print(f"[P2P Node {self.port}] 🔄 Synced Block {new_block.index} [{new_block.hash[:8]}]")
                    else:
                        print(f"[P2P Node {self.port}] ❌ Failed to sync block {new_block.index}. Possible Fork Detected.")
                        our_height = len(self.blockchain.chain) - 1
                        self.send_message(conn, MSG_RESOLVE_FORK, {"from_index": max(0, our_height - 20)})
                        break
                
                if added_count > 0 and len(blocks) == 50:
                    our_height = len(self.blockchain.chain) - 1
                    print(f"[P2P Node {self.port}] Requesting next batch of blocks from {our_height + 1}...")
                    self.send_message(conn, MSG_GET_BLOCKS, {"from_index": our_height + 1})



        elif msg_type == MSG_RESOLVE_FORK:
            from_index = payload.get("from_index", 0)
            if self.blockchain:
                our_height = len(self.blockchain.chain) - 1
                if from_index <= our_height:
                    blocks_to_send = [b.to_dict() for b in self.blockchain.chain[from_index:our_height + 1]]
                    print(f"[P2P Node {self.port}] Sending fork resolution blocks {from_index} to {our_height} to {addr}")
                    self.send_message(conn, MSG_FORK_BLOCKS, {"blocks": blocks_to_send})

        elif msg_type == MSG_FORK_BLOCKS:
            blocks = payload.get("blocks", [])
            if blocks and self.blockchain:
                from mempool_block import Block
                candidate_blocks = []
                for block_data in blocks:
                    new_block = Block(
                        index=block_data["index"],
                        previous_hash=block_data["previous_hash"],
                        transactions=block_data["transactions"],
                        semantic_payload=block_data["semantic_payload"],
                        difficulty=block_data["difficulty"],
                        nonce=block_data["nonce"]
                    )
                    new_block.timestamp = block_data["timestamp"]
                    new_block.hash = block_data["hash"]
                    candidate_blocks.append(new_block)
                
                self.blockchain.replace_chain(candidate_blocks)

if __name__ == "__main__":
    pass
