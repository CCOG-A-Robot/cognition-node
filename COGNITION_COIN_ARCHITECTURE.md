# COGNITION COIN ARCHITECTURE (Persistent Memory - 2026-03-16)

## Vision & Core Principles
*Refer to PROJECT_ROADMAP.md for the overarching vision and strategic propositions.*
Cognition Coin aims to establish a novel blockchain where mining involves solving AI-hard, semantic puzzles, leveraging AI capabilities rather than brute-force computation. This creates an "AI-centric" Proof-of-Work (PoW) that is designed to be more energy-efficient and aligned with future digital economies.

## Consensus & Economic Parameters
This section serves as the canonical source of truth for the core, unchangeable rules of the Cognition Coin network.

*   **Total Supply:** 21,000,000 COG (Absolute Scarcity Model)
*   **Block Reward Halving Interval:** Every 210,000 blocks.
*   **Target Block Time:** 150 Seconds (2.5 minutes).
*   **Difficulty Adjustment Interval:** Every 10 blocks (for Testnet phase; will be increased for Mainnet).
*   **Initial Block Reward:** 50 COG.
*   **Transaction Fees:** Handled implicitly via the UTXO model (Total Inputs - Total Outputs = Miner Fee). Miners sweep all unallocated change from mempool transactions and add it to their 50 COG base reward. The L1 fee market is entirely variable.

*   **Ongoing Work:** Refining the difficulty adjustment algorithm to achieve a target block time of 150 seconds, as initial tests show block times around 60 seconds at difficulty 3.

## Chosen Proof-of-Work (PoW) Mechanism: The "Dual-Lock" Protocol
The Cognition Coin consensus mechanism (v2) uses a two-stage proof to ensure both AI-centricity and industrial-grade scalability.

### 1. Stage One: The Semantic Proof (Proof of Intellect)
*   **The Work:** The miner must generate a unique sentence using a deterministic local LLM (e.g., Llama-3-8B).
*   **The Oracle (Genesis Model):** Every node deterministically generates the *next* block's riddle using the previous block's hash as a seed for a fixed Llama-3-8B call at Temperature 0.0. This ensures the entire network agrees on the puzzle without a central server.
*   **The Constraint:** The sentence must meet the network's current semantic rules (e.g., 5-15 words, must include a deterministically chosen keyword). To prevent infinite Temp 0.0 deadlocks, rules are pre-validated before hashing, and the miner explicitly mutates the prompt on retry to force a new LLM attention path.
*   **The Purpose:** This acts as a "Proof of Intelligence" and an entry barrier that prevents traditional ASIC or GPU miners from dominating the network without running AI models.

### 2. Stage Two: The Cryptographic Proof (The Scalability Throttle)
*   **The Work:** Once a valid Semantic Payload is found, the miner adds a numeric **Nonce** to the block header and begins the hash grind.
*   **The Constraint (CognitiveHash MatMul):** SHA-256 has been stripped out of the core mining loop. It has been replaced with a custom algorithm called **CognitiveHash**. It uses the block data to seed a deterministic Linear Congruential Generator (LCG) which generates two large 64x64 matrices. It then performs a pure integer Matrix Multiplication (MatMul), requiring over 262,000 calculation loops per nonce. 
*   **The Hardware Physics:** MatMul is the absolute mathematical soul of neural networks. By forcing the miner to perform massive matrix multiplications, we ensure the network is secured natively by AI hardware (GPUs, TPUs, NPUs), explicitly bricking traditional Bitcoin ASICs (which lack matrix capabilities and memory bandwidth). 
*   **The Determinism Lock:** We strictly use *integer* math rather than *floating-point* math for the MatMul calculation. This guarantees 100% cross-platform determinism, preventing the blockchain from fracturing/forking due to microscopic floating-point rounding errors across different CPU architectures and Nvidia/AMD quantization levels.
*   **Difficulty Adjustment & Chain Sync:** The protocol targets a **150-second (2.5 minute)** block time using a `+1 / -1` step function. To prevent ghost forks, the MatMul grind features an `abort_check` interrupt that instantly drops stale hashes if a peer broadcasts a valid new chain tip.
*   **The Purpose:** This allows the network to scale its difficulty to trillions of hashes (Bitcoin-level) while only requiring a few seconds of AI inference per block attempt.

## The Cognition Coin Ecosystem
*   **Core Application (The Node):** A portable, standalone binary mimicking Bitcoin Core. It acts as a full node (ledger synchronization with local `blockchain.json` state persistence), wallet manager, and semantic miner.
    *   **Bot-Friendly:** All functions available via CLI and exposed through a lightweight JSON-RPC interface for headless automation via `node_api.py` (FastAPI).
*   **The BBS (The Website):** A modern, Bitcointalk-style platform hosted at `cognitioncoin.org` (Live).
    *   **Functionality:** Hosting for the Whitepaper, community BBS message boards (SMF `cognlmpn_forum`), and download/onboarding portals.
    *   **Web-to-L1 Interface:** Provides an online wallet interface for balance checking, ledger display (block explorer), and public visualization of semantic puzzle solutions.
*   **Wrapped CCOG (wCCOG) & Liquidity:** Native L1 CCOG cannot be traded on standard DEXs. A bridging protocol will be established to wrap native CCOG into an EVM-compatible ERC-20 token (wCCOG), allowing the network's cognitive work to interface with global DeFi liquidity pools (Uniswap).
*   **Integration Layer (JSON-RPC):** The bridge between the Node and the Website/External Bots. Standardized methods for:
    *   `getblockchaininfo`: Global state (Height, Diff, UTXO count).
    *   `getbalance`: Address funds lookup.
    *   `sendrawtransaction`: Authorized transaction broadcast.
    *   `getblock`: Blockchain exploration and puzzle payload viewing.
    *   **Security:** Signing logic is confined to the local Node/CLI; the API wrapper handles only authenticated requests to trigger local node signing (keys isolated in `.pem` files).

## Current Component Status (Implemented vs. Mocked/Conceptual)
*   **Semantic Miner:** [DONE] Live Llama-3 integration with dual-lock nonce grinding.
*   **Blockchain Logic:** [DONE] UTXO management, Dynamic Difficulty, and Block Validation logic.
*   **P2P Network:** [DONE] Functional block/transaction broadcasting.
    *   *Testnet Validation (2026-03-29):* Successfully achieved multi-machine synchronization over LAN. Outbound connections are handled asynchronously to prevent firewall timeouts from blocking incoming blocks.
    *   *Testnet Sync (2026-03-29):* [DONE] Implementation of `GET_BLOCKS` (Initial Block Download) logic to allow late-joining nodes to sync historical ledger state before mining.
    *   **Fork Resolution (2026-03-29):** [DONE] Implemented Longest Chain Rule. Nodes can gracefully roll back orphaned chains, rescue valid transactions, and rebuild their UTXO state.
*   **Wallet/Identity:** [DONE] ECDSA KeyGen and transaction signing.
*   **Web Infrastructure:** [DONE] `cognitioncoin.org` domain active. Static pages deployed via FTP. SMF deployed to `cognlmpn_forum` database.
*   **Community & Onboarding:** [ACTIVE BLOCKER] Configure SMF, establish GitHub repository, and dry-run the miner installation process.
