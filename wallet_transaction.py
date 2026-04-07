import hashlib
import json
import time
# import uuid # No longer needed for real key generation
from ecdsa import SigningKey, VerifyingKey, SECP256k1

# In a production environment, we would use the `ecdsa` or `cryptography` library 
# for true SECP256k1 (Bitcoin-style) or Ed25519 public/private key generation.
# For this architectural prototype, we are structuring the classes to show exactly
# how the data flows and is verified by the network.

class UTXO:
    """
    Represents an Unspent Transaction Output.
    This is the fundamental unit of value in a UTXO-based blockchain.
    """
    def __init__(self, tx_id, output_index, amount, recipient_address):
        self.tx_id = tx_id                  # The ID of the transaction that created this UTXO
        self.output_index = output_index    # The index of this output in the creating transaction
        self.amount = amount                # The value of this UTXO
        self.recipient_address = recipient_address # The public key (address) of the owner

    def to_dict(self):
        return {
            "tx_id": self.tx_id,
            "output_index": self.output_index,
            "amount": self.amount,
            "recipient_address": self.recipient_address
        }

    def __hash__(self):
        return hash((self.tx_id, self.output_index))

    def __eq__(self, other):
        return isinstance(other, UTXO) and (self.tx_id, self.output_index) == (other.tx_id, other.output_index)

class TransactionInput:
    """
    Represents an input to a transaction, spending a specific UTXO.
    """
    def __init__(self, utxo_tx_id, utxo_output_index, signature=None, pub_key=None):
        self.utxo_tx_id = utxo_tx_id        # The tx_id of the UTXO being spent
        self.utxo_output_index = utxo_output_index # The output_index of the UTXO being spent
        self.signature = signature          # Signature of the transaction by the UTXO owner
        self.pub_key = pub_key              # Public key of the UTXO owner (for verification)

    def to_dict(self):
        return {
            "utxo_tx_id": self.utxo_tx_id,
            "utxo_output_index": self.utxo_output_index,
            "signature": self.signature.hex() if self.signature else None,
            "pub_key": self.pub_key
        }

class TransactionOutput:
    """
    Represents an output of a transaction, creating a new UTXO.
    """
    def __init__(self, amount, recipient_address):
        self.amount = amount
        self.recipient_address = recipient_address

    def to_dict(self):
        return {
            "amount": self.amount,
            "recipient_address": self.recipient_address
        }

class Wallet:
    def __init__(self, private_key_pem=None):
        """
        A wallet doesn't hold coins. It holds cryptographic keys that prove 
        you have the right to alter the ledger.
        """
        if private_key_pem:
            # Load from PEM format (e.g., from a file)
            self.private_key = SigningKey.from_pem(private_key_pem)
        else:
            # Generate a new private key
            self.private_key = SigningKey.generate(curve=SECP256k1)
        
        self.public_key_vk = self.private_key.get_verifying_key()
        # The public address is derived from the public key, usually its hex representation
        self.public_key = self.public_key_vk.to_string().hex()

    def sign_transaction(self, transaction, utxo_set):
        """
        Signs the inputs of a transaction that belong to this wallet.
        Each input references a UTXO. The signature proves the owner of 
        that UTXO (this wallet) authorized the spend.
        """
        signed_inputs = []
        for tx_input in transaction.inputs:
            # Only sign inputs that belong to this wallet
            if tx_input.pub_key == self.public_key:
                # Get the original UTXO referenced by this input
                utxo = utxo_set.get_utxo(tx_input.utxo_tx_id, tx_input.utxo_output_index)
                if not utxo or utxo.recipient_address != self.public_key:
                    raise ValueError(f"Attempted to sign input for UTXO not owned by this wallet or non-existent.")

                # The data to be signed is usually a hash of the current transaction (excluding signatures)
                # and potentially details of the UTXO being spent.
                # For simplicity here, we sign the hash of the current transaction's core data.
                tx_hash_for_signature = transaction.calculate_hash()
                signature = self.private_key.sign(tx_hash_for_signature.encode('utf-8'))
                tx_input.signature = signature # Attach signature (bytes)
                tx_input.pub_key = self.public_key # Ensure pub_key is set for verification
            signed_inputs.append(tx_input)
        transaction.inputs = signed_inputs # Update transaction with signed inputs
        return transaction

    def create_transaction(self, recipient_address, amount, utxo_set, fee=0.0):
        """
        Creates a new transaction, selecting UTXO inputs, generating outputs
        (including change), and signing the transaction inputs.
        """
        if not self.public_key:
            raise ValueError("Wallet not initialized. Cannot create transaction.")

        # 1. Gather spendable UTXOs
        available_utxos = []
        current_balance = 0
        for utxo in utxo_set.utxos.values():
            if utxo.recipient_address == self.public_key:
                available_utxos.append(utxo)
                current_balance += utxo.amount

        if current_balance < amount + fee:
            raise ValueError(f"Insufficient funds. Available: {current_balance}, Needed: {amount + fee}")

        # 2. Select UTXOs to spend (simple greedy approach for now)
        inputs = []
        inputs_value = 0
        utxos_to_spend = []

        # Sort UTXOs for deterministic selection (optional but good practice)
        available_utxos.sort(key=lambda u: (u.tx_id, u.output_index))

        for utxo in available_utxos:
            if inputs_value < amount + fee:
                inputs.append(TransactionInput(utxo.tx_id, utxo.output_index, pub_key=self.public_key))
                inputs_value += utxo.amount
                utxos_to_spend.append(utxo)
            else:
                break

        if inputs_value < amount + fee: # Should not happen with prior balance check
            raise ValueError("Could not gather enough UTXOs for transaction.")

        # 3. Create outputs
        outputs = []
        outputs.append(TransactionOutput(amount, recipient_address)) # To recipient

        change_amount = inputs_value - (amount + fee)
        if change_amount > 0:
            outputs.append(TransactionOutput(change_amount, self.public_key)) # Change back to self

        # 4. Create the transaction
        new_tx = Transaction(inputs, outputs)

        # 5. Sign the transaction inputs
        signed_tx = self.sign_transaction(new_tx, utxo_set)

        return signed_tx

class Transaction:
    def __init__(self, inputs, outputs):
        self.inputs = inputs          # List of TransactionInput objects
        self.outputs = outputs        # List of TransactionOutput objects
        self.timestamp = time.time()
        self.tx_id = self.calculate_hash() # Transaction ID is its hash

    def to_dict(self):
        return {
            "tx_id": self.tx_id,
            "timestamp": self.timestamp,
            "inputs": [i.to_dict() for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs]
        }

    def calculate_hash(self, include_signatures=False):
        """
        Hashes the core transaction data.
        To avoid circularity during signing, we exclude signatures by default.
        """
        inputs_data = []
        for i in self.inputs:
            d = i.to_dict()
            if not include_signatures:
                d["signature"] = None
            inputs_data.append(d)

        tx_data = {
            "inputs": inputs_data,
            "outputs": [o.to_dict() for o in self.outputs],
            "timestamp": self.timestamp
        }
        return hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode('utf-8')).hexdigest()

    def sign(self, wallet):
        self.signature = wallet.sign_transaction(self)

    def is_valid(self, utxo_set):
        # Mining reward transaction (Coinbase) is a special case with no inputs
        # or it has a single input that signals coinbase.
        if not self.inputs: # Assuming coinbase tx has no inputs for simplicity here
            if len(self.outputs) == 1: # Must have one output (the reward)
                # Further checks for coinbase (e.g., amount within limits) would go here
                return True
            else:
                print("[Reject] Coinbase transaction must have exactly one output.")
                return False

        input_total = 0
        output_total = 0
        tx_hash_for_signature = self.calculate_hash() # Hash for verifying signatures

        # 1. Verify inputs: signatures, UTXO existence, and sum input amounts
        for tx_input in self.inputs:
            # Check if signature and public key are present
            if not tx_input.signature or not tx_input.pub_key:
                print(f"[Reject] Transaction {self.tx_id[:8]} input missing signature or public key.")
                return False

            # Check if the referenced UTXO exists and is unspent
            referenced_utxo = utxo_set.get_utxo(tx_input.utxo_tx_id, tx_input.utxo_output_index)
            if not referenced_utxo:
                print(f"[Reject] Transaction {self.tx_id[:8]} references a spent or non-existent UTXO: {tx_input.utxo_tx_id[:8]}:{tx_input.utxo_output_index}")
                return False

            # Check if the public key in the input matches the recipient of the UTXO
            if tx_input.pub_key != referenced_utxo.recipient_address:
                print(f"[Reject] Transaction {self.tx_id[:8]} input public key does not match UTXO recipient.")
                return False

            # Verify the signature against the transaction's hash and the input's public key
            try:
                vk = VerifyingKey.from_string(bytes.fromhex(tx_input.pub_key), curve=SECP256k1)
                vk.verify(tx_input.signature, tx_hash_for_signature.encode('utf-8'))
            except Exception as e:
                print(f"[Reject] Transaction {self.tx_id[:8]} input signature verification failed: {e}")
                return False

            input_total += referenced_utxo.amount

        # 2. Sum output amounts
        for tx_output in self.outputs:
            output_total += tx_output.amount

        # 3. Check input_total >= output_total (inputs must cover outputs + fee)
        if input_total < output_total:
            print(f"[Reject] Transaction {self.tx_id[:8]} input total ({input_total}) is less than output total ({output_total}).")
            return False
        
        # Transaction is valid if all checks pass
        print(f"[Network] Transaction {self.tx_id[:8]} cryptographically verified!")
        return True

if __name__ == "__main__":
    print("==================================================")
    print("  COGNITION COIN: WALLET & TX ARCHITECTURE")
    print("==================================================\n")

    # --- Mock UTXO Set for Demonstration ---
    # In a real system, this would be managed by the Blockchain/Node.
    class MockUTXOSet:
        def __init__(self):
            self.utxos = {}

        def add_utxo(self, utxo):
            self.utxos[(utxo.tx_id, utxo.output_index)] = utxo

        def get_utxo(self, tx_id, output_index):
            return self.utxos.get((tx_id, output_index))
        
        def remove_utxo(self, tx_id, output_index):
            if (tx_id, output_index) in self.utxos:
                del self.utxos[(tx_id, output_index)]

    mock_utxo_set = MockUTXOSet()

    # 1. Create two users
    alice_wallet = Wallet()
    bob_wallet = Wallet()

    print(f"Alice Public Key (Address): {alice_wallet.public_key[:16]}...")
    print(f"Bob Public Key (Address):   {bob_wallet.public_key[:16]}...\n")

    # --- Simulate a Coinbase Transaction to give Alice funds ---
    print("Simulating initial funds for Alice via a Coinbase transaction...")
    coinbase_tx_id = hashlib.sha256(b"coinbase_tx_initial").hexdigest()
    alice_initial_utxo = UTXO(coinbase_tx_id, 0, 100, alice_wallet.public_key)
    mock_utxo_set.add_utxo(alice_initial_utxo)
    print(f"Alice received 100 CCOG in UTXO: {coinbase_tx_id[:8]}:0\n")

    # 2. Alice creates a transaction to send 50 CCOG to Bob
    print("Alice is creating a transaction to send 50 coins to Bob...")

    # Inputs: Alice spends her initial UTXO
    tx_input_from_alice = TransactionInput(
        utxo_tx_id=alice_initial_utxo.tx_id,
        utxo_output_index=alice_initial_utxo.output_index,
        pub_key=alice_wallet.public_key # Alice's public key for signing
    )

    # Outputs: 50 to Bob, 50 back to Alice (change)
    tx_output_to_bob = TransactionOutput(50, bob_wallet.public_key)
    tx_output_to_alice_change = TransactionOutput(50, alice_wallet.public_key)

    tx1 = Transaction(inputs=[tx_input_from_alice], outputs=[tx_output_to_bob, tx_output_to_alice_change])

    # 3. Alice signs the transaction inputs that belong to her
    print("Alice is signing the transaction...")
    tx1 = alice_wallet.sign_transaction(tx1, mock_utxo_set)
    print(f"Transaction Signed! Input Signature: {tx1.inputs[0].signature.hex()[:16]}...\n")

    # 4. The network intercepts the transaction and verifies it
    print("Broadcasting to network mempool for verification...")
    if tx1.is_valid(mock_utxo_set):
        print("✅ Transaction cryptographically verified and UTXO rules valid! Ready to be mined into a block.")
        # Simulate UTXO update (spent Alice's initial, added new for Bob and Alice's change)
        mock_utxo_set.remove_utxo(alice_initial_utxo.tx_id, alice_initial_utxo.output_index)
        mock_utxo_set.add_utxo(UTXO(tx1.tx_id, 0, tx_output_to_bob.amount, tx_output_to_bob.recipient_address))
        mock_utxo_set.add_utxo(UTXO(tx1.tx_id, 1, tx_output_to_alice_change.amount, tx_output_to_alice_change.recipient_address))
        print(f"[DEMO] UTXO Set updated. Alice's initial UTXO spent. New UTXOs created.")
    else:
        print("❌ Transaction rejected (Invalid Signature or UTXO rules).")

