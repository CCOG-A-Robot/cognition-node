import asyncio
import json
import time
import threading
import socket
from wallet_transaction import Transaction, TransactionInput, TransactionOutput

# --- P2P Network Configuration ---
SEED_NODES = [("24.144.104.66", 8000)] # DigitalOcean Main Seed Node
PORT = 8001

# Beta Armor Scalability Limits
MAX_INBOUND_CONNECTIONS = 500
MAX_OUTBOUND_CONNECTIONS = 10
MAX_PAYLOAD_SIZE = 20 * 1024 * 1024 # 20 MB memory DoS shield
BAN_DURATION = 86400 # 24 hours in seconds

# --- Message Types ---
MSG_HANDSHAKE = "HANDSHAKE"
MSG_GET_PEERS = "GET_PEERS"
MSG_PEERS     = "PEERS"
MSG_NEW_TX    = "NEW_TX"
MSG_NEW_BLOCK = "NEW_BLOCK"
MSG_GET_BLOCKS = "GET_BLOCKS"
MSG_RESOLVE_FORK = "RESOLVE_FORK"
MSG_FORK_BLOCKS = "FORK_BLOCKS"
MSG_BLOCKS    = "BLOCKS"
MSG_REJECT    = "REJECT"

class P2PNode:
    def __init__(self, host="0.0.0.0", port=PORT, blockchain=None, mempool=None):
        self.host = host
        self.port = port
        
        # Connection Dictionaries: { "ip:port": (reader, writer) }
        self.inbound_peers = {}
        self.outbound_peers = {}
        self.banned_ips = {} # { "ip": unban_timestamp }
        
        self.running = True
        self.blockchain = blockchain
        self.mempool = mempool
        
        # Asyncio Event Loop running in a dedicated thread
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_loop, daemon=True)

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._async_start())

    def start(self):
        print(f"[P2P Node {self.port}] 🛡️ Initializing Asynchronous Engine (Beta Armor)...")
        self.thread.start()

    def stop(self):
        print(f"[P2P Node {self.port}] Shutting down...")
        self.running = False
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

    async def _async_start(self):
        server = await asyncio.start_server(
            self._handle_inbound_connection, self.host, self.port
        )
        print(f"[P2P Node {self.port}] Listening asynchronously on {self.host}:{self.port}")
        print(f"[P2P Node {self.port}] Limits: Inbound={MAX_INBOUND_CONNECTIONS}, Outbound={MAX_OUTBOUND_CONNECTIONS}, MaxPayload=20MB")
        
        # Start outbound seed connector
        asyncio.create_task(self._seed_connection_loop())
        
        async with server:
            while self.running:
                await asyncio.sleep(1)

    def is_banned(self, ip):
        if ip in self.banned_ips:
            if time.time() > self.banned_ips[ip]:
                del self.banned_ips[ip] # Ban expired
                return False
            return True
        return False

    def ban_ip(self, ip, reason):
        print(f"[P2P Node {self.port}] 🛑 BANNING IP {ip} for 24h. Reason: {reason}")
        self.banned_ips[ip] = time.time() + BAN_DURATION
        self._disconnect_ip(ip)

    def _disconnect_ip(self, ip):
        # Close and remove all connections matching this IP
        for addr in list(self.inbound_peers.keys()) + list(self.outbound_peers.keys()):
            if addr.startswith(f"{ip}:"):
                self._remove_peer(addr)

    async def _handle_inbound_connection(self, reader, writer):
        addr_info = writer.get_extra_info('peername')
        ip = addr_info[0]
        addr = f"{ip}:{addr_info[1]}"

        if self.is_banned(ip):
            writer.close()
            await writer.wait_closed()
            return

        if len(self.inbound_peers) >= MAX_INBOUND_CONNECTIONS:
            print(f"[P2P Node {self.port}] Max inbound reached. Rejecting {addr}")
            writer.close()
            await writer.wait_closed()
            return

        self.inbound_peers[addr] = (reader, writer)
        print(f"[P2P Node {self.port}] Inbound connection accepted from {addr}")
        
        await self._connection_loop(reader, writer, addr, ip)

    async def _seed_connection_loop(self):
        # Get actual local IP to prevent self-connection
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            my_ip = s.getsockname()[0]
            s.close()
        except:
            my_ip = "127.0.0.1"

        while self.running:
            for host, port in SEED_NODES:
                if host != my_ip and (host, port) != (self.host, self.port):
                    await self._connect_outbound(host, port)
            
            await asyncio.sleep(15) # Check every 15 seconds
            
            if self.inbound_peers or self.outbound_peers:
                await self._async_broadcast(MSG_GET_PEERS, {"sender_port": self.port})

    async def _connect_outbound(self, host, port):
        ip = host
        addr = f"{host}:{port}"
        
        if self.is_banned(ip): return
        if addr in self.outbound_peers or addr in self.inbound_peers: return
        
        if len(self.outbound_peers) >= MAX_OUTBOUND_CONNECTIONS:
            return
            
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5.0)
            self.outbound_peers[addr] = (reader, writer)
            print(f"[P2P Node {self.port}] Connected outbound to {addr}")
            
            # Handshake
            payload = {"port": self.port}
            if self.blockchain and self.blockchain.chain:
                payload["height"] = len(self.blockchain.chain) - 1
                payload["tip_hash"] = self.blockchain.chain[-1].hash
                payload["genesis_hash"] = self.blockchain.chain[0].hash
            await self._async_send(writer, MSG_HANDSHAKE, payload)

            # Start listening to this outbound peer
            asyncio.create_task(self._connection_loop(reader, writer, addr, ip))
        except Exception:
            pass # Connection failed silently

    async def _connection_loop(self, reader, writer, addr, ip):
        try:
            while self.running:
                # 1. Read 10-byte length header
                length_bytes = await reader.readexactly(10)
                msg_len_str = length_bytes.decode('utf-8').strip()
                
                if not msg_len_str.isdigit():
                    self.ban_ip(ip, "Malformed payload length header")
                    break
                    
                msg_len = int(msg_len_str)
                
                # 2. Enforce Memory DoS Shield (MAX_PAYLOAD_SIZE)
                if msg_len > MAX_PAYLOAD_SIZE:
                    self.ban_ip(ip, f"Oversized payload ({msg_len} bytes)")
                    break
                    
                # 3. Read the exact message body
                msg_bytes = await reader.readexactly(msg_len)
                message = json.loads(msg_bytes.decode('utf-8'))
                
                await self._process_message(writer, addr, ip, message)
                
        except asyncio.IncompleteReadError:
            pass # Normal disconnect (peer hung up)
        except json.JSONDecodeError:
            self.ban_ip(ip, "Invalid JSON payload")
        except Exception as e:
            pass # Catch other network interrupts
        finally:
            self._remove_peer(addr)
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

    def _remove_peer(self, addr):
        if addr in self.inbound_peers:
            del self.inbound_peers[addr]
        if addr in self.outbound_peers:
            del self.outbound_peers[addr]

    def broadcast_message(self, msg_type, payload, exclude_peer=None):
        """Thread-safe injection point for the synchronous core_node.py main thread"""
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_broadcast(msg_type, payload, exclude_peer), 
                self.loop
            )

    def send_message(self, target_socket, msg_type, payload):
        """Fallback for compatibility, though largely unused in the async rewrite"""
        pass 

    async def _async_broadcast(self, msg_type, payload, exclude_addr=None):
        all_peers = list(self.inbound_peers.items()) + list(self.outbound_peers.items())
        for addr, (reader, writer) in all_peers:
            if addr != exclude_addr:
                await self._async_send(writer, msg_type, payload)

    async def _async_send(self, writer, msg_type, payload):
        message = json.dumps({"type": msg_type, "payload": payload}).encode('utf-8')
        header = f"{len(message):<10}".encode('utf-8')
        try:
            writer.write(header + message)
            await writer.drain()
        except Exception:
            pass # Writer disconnected

    async def _process_message(self, writer, addr, ip, message):
        msg_type = message.get("type")
        payload = message.get("payload")

        if msg_type not in [MSG_GET_PEERS, MSG_PEERS, MSG_GET_BLOCKS]:
            print(f"[P2P Node {self.port}] Received {msg_type} from {addr}")

        if msg_type == MSG_HANDSHAKE:
            peer_genesis = payload.get("genesis_hash")
            if self.blockchain and self.blockchain.chain and peer_genesis:
                our_genesis = self.blockchain.chain[0].hash
                if peer_genesis != our_genesis:
                    print(f"⚠️ [P2P Node {self.port}] Genesis mismatch with {addr}. They are on a deprecated chain.")
                    await self._async_send(writer, MSG_REJECT, {"reason": "NETWORK RESET. The Vanguard Testnet has been updated. Please run `git pull`, delete your `blockchain.json`, and restart the node."})
                    self.ban_ip(ip, "Genesis Hash Mismatch (Imposter Chain)")
                    return

            peer_port = payload.get("port")
            if peer_port:
                # We have their port, they are a known peer now
                pass
            
            peer_height = payload.get("height")
            if peer_height is not None and self.blockchain:
                our_height = len(self.blockchain.chain) - 1
                if peer_height > our_height:
                    await self._async_send(writer, MSG_GET_BLOCKS, {"from_index": our_height + 1})
                elif peer_height < our_height:
                    await self._async_send(writer, MSG_NEW_BLOCK, {"block": self.blockchain.chain[-1].to_dict()})

        elif msg_type == MSG_REJECT:
            reason = payload.get("reason", "Unknown")
            print(f"\n❌ [P2P FATAL] Network connection rejected by peer: {reason}")
            print(f"❌ Action Required: Update your code and restart.\n")
            # We don't automatically kill the node, but we loudly warn the user.
            
        elif msg_type == MSG_GET_PEERS:
            known_peers = []
            for p_addr in list(self.inbound_peers.keys()) + list(self.outbound_peers.keys()):
                p_ip, p_port = p_addr.split(":")
                known_peers.append({"host": p_ip, "port": int(p_port)})
            await self._async_send(writer, MSG_PEERS, {"peers": known_peers[:50]})

        elif msg_type == MSG_PEERS:
            for peer_info in payload.get("peers", []):
                p_host = peer_info.get("host")
                p_port = peer_info.get("port")
                if p_host and p_port and (p_host, p_port) != (self.host, self.port):
                    asyncio.create_task(self._connect_outbound(p_host, p_port))
        
        elif msg_type == MSG_NEW_TX:
            tx_data = payload.get("transaction")
            if tx_data and self.mempool:
                try:
                    inputs = [TransactionInput(i['utxo_tx_id'], i['utxo_output_index'], bytes.fromhex(i['signature']) if i['signature'] else None, i['pub_key']) for i in tx_data['inputs']]
                    outputs = [TransactionOutput(o['amount'], o['recipient_address']) for o in tx_data['outputs']]
                    new_tx = Transaction(inputs, outputs)
                    new_tx.tx_id = tx_data['tx_id']
                    new_tx.timestamp = tx_data['timestamp']

                    if new_tx.is_valid(self.blockchain.utxo_set):
                        have_tx = any(t.tx_id == new_tx.tx_id for t in self.mempool.pending_transactions)
                        if not have_tx:
                            self.mempool.add_transaction(new_tx)
                            await self._async_broadcast(MSG_NEW_TX, payload, exclude_addr=addr)
                    else:
                        self.ban_ip(ip, "Invalid Transaction Math/Signature")
                except Exception as e:
                    print(f"[P2P Node {self.port}] Error processing NEW_TX: {e}")

        elif msg_type == MSG_NEW_BLOCK:
            block_data = payload.get("block")
            if block_data and self.blockchain:
                try:
                    from mempool_block import Block
                    block_hash = block_data.get("hash")
                    if any(b.hash == block_hash for b in self.blockchain.chain): return
                    
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
                        await self._async_send(writer, MSG_GET_BLOCKS, {"from_index": our_height + 1})
                    elif self.blockchain.add_block(new_block):
                        print(f"[P2P Node {self.port}] 🌐 Block {new_block.index} accepted from network!")
                        await self._async_broadcast(MSG_NEW_BLOCK, payload, exclude_addr=addr)
                    else:
                        print(f"[P2P Node {self.port}] ❌ Rejected invalid block {new_block.index} from network.")
                except Exception:
                    pass

        elif msg_type == MSG_GET_BLOCKS:
            from_index = payload.get("from_index", 0)
            if self.blockchain:
                our_height = len(self.blockchain.chain) - 1
                if from_index <= our_height:
                    end_index = min(from_index + 50, our_height + 1)
                    blocks_to_send = [b.to_dict() for b in self.blockchain.chain[from_index:end_index]]
                    await self._async_send(writer, MSG_BLOCKS, {"blocks": blocks_to_send})

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
                    else:
                        our_height = len(self.blockchain.chain) - 1
                        await self._async_send(writer, MSG_RESOLVE_FORK, {"from_index": max(0, our_height - 20)})
                        break
                
                if added_count > 0 and len(blocks) == 50:
                    our_height = len(self.blockchain.chain) - 1
                    await self._async_send(writer, MSG_GET_BLOCKS, {"from_index": our_height + 1})

        elif msg_type == MSG_RESOLVE_FORK:
            from_index = payload.get("from_index", 0)
            if self.blockchain:
                our_height = len(self.blockchain.chain) - 1
                if from_index <= our_height:
                    blocks_to_send = [b.to_dict() for b in self.blockchain.chain[from_index:our_height + 1]]
                    await self._async_send(writer, MSG_FORK_BLOCKS, {"blocks": blocks_to_send})

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
