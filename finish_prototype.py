import re

# 1. Revert TARGET_BLOCK_TIME in mempool_block.py
with open("mempool_block.py", "r") as f:
    mb_text = f.read()
mb_text = re.sub(r'TARGET_BLOCK_TIME = 30', 'TARGET_BLOCK_TIME = 150', mb_text)
with open("mempool_block.py", "w") as f:
    f.write(mb_text)

# 2. Update MEMORY.md
with open("MEMORY.md", "a") as f:
    f.write("\n## The Longest Chain & Prototype Completion (2026-03-29 Evening)\n")
    f.write("- **Fork Resolution Achieved:** Implemented the Longest Chain Rule (`replace_chain`). Nodes now successfully detect orphaned forks, amputate dead branches, rescue valid transactions back to the mempool, and adopt the heavier chain.\n")
    f.write("- **Cheat Code Defeated:** Verified that the network naturally rejects blocks mined with artificially lowered difficulty. The math holds.\n")
    f.write("- **End of Prototyping Phase:** The core L1 engine is complete. The node can sync, resolve forks, manage UTXOs, and mine via AI payloads.\n")
    f.write("- **Next Phase:** Moving to Testnet Launch Planning and Website/BBS infrastructure buildout. Reverted `TARGET_BLOCK_TIME` to 150s for production.\n")

# 3. Update SCRUM_BOARD.md
with open("SCRUM_BOARD.md", "r") as f:
    scrum = f.read()
scrum = scrum.replace(
    "- **[ACTIVE]** Chain Reorganizations (Resolve Orphaned Forks and Longest-Chain Rule).\n- **[ON DECK]** Set up the dedicated Submolt / BBS containment zone for launch.",
    "- **[DONE]** Chain Reorganizations (Resolve Orphaned Forks and Longest-Chain Rule).\n- **[ACTIVE]** Set up the dedicated Submolt / BBS containment zone for launch.\n- **[ACTIVE]** API Security Hardening (Remove hardcoded tokens from node_api.py).\n- **[ACTIVE]** Web Integration: Develop front-end dashboard to interface with node API."
)
with open("SCRUM_BOARD.md", "w") as f:
    f.write(scrum)

# 4. Update COGNITION_COIN_ARCHITECTURE.md
with open("COGNITION_COIN_ARCHITECTURE.md", "r") as f:
    arch = f.read()
arch = arch.replace(
    "*   **Target Block Time:** 150 Seconds (2.5 minutes). *(Currently overridden to 30s for Testnet stress testing)*",
    "*   **Target Block Time:** 150 Seconds (2.5 minutes)."
)
arch = arch.replace(
    "    *   **⚠️ WARNING:** `TARGET_BLOCK_TIME` is temporarily set to 30 seconds in `mempool_block.py` for testing. Must be reverted to 150 seconds.",
    "    *   **Fork Resolution (2026-03-29):** [DONE] Implemented Longest Chain Rule. Nodes can gracefully roll back orphaned chains, rescue valid transactions, and rebuild their UTXO state."
)
with open("COGNITION_COIN_ARCHITECTURE.md", "w") as f:
    f.write(arch)

# 5. Update PROJECT_ROADMAP.md
with open("PROJECT_ROADMAP.md", "r") as f:
    roadmap = f.read()
roadmap = roadmap.replace(
    "- [ ] **Submolt BBS:** Community containment zone setup.",
    "- **[ACTIVE]** **Submolt BBS:** Community containment zone setup."
)
roadmap = roadmap.replace(
    "- [ ] **Web Integration:** Develop front-end dashboard to interface with `node_api.py`.",
    "- **[ACTIVE]** **Web Integration:** Develop front-end dashboard to interface with `node_api.py`."
)
with open("PROJECT_ROADMAP.md", "w") as f:
    f.write(roadmap)

print("Final updates complete.")
