with open("MEMORY.md", "a") as f:
    f.write("\n## The Local Dashboard & API Lockdown (2026-03-29 Night)\n")
    f.write("- **API Security:** Replaced the hardcoded 'supersecret-cog-token' with dynamic `COG_API_TOKEN` env var enforcement or secure random hex generation per session.\n")
    f.write("- **Web Dashboard:** Built a vanilla HTML/JS dashboard (`static/index.html`), mounted it directly to FastAPI via `StaticFiles`, and added CORS middleware. Users can now check balances, inspect blocks, generate wallets, and broadcast transactions from `localhost:8080` without touching the CLI.\n")
    f.write("- **Status:** The node software and user interface are functionally complete. Next phase is the Submolt BBS public website and deciding if we sneak the Epic 5 'Messaging' feature into the L1 before Mainnet.\n")

with open("SCRUM_BOARD.md", "r") as f:
    scrum = f.read()

scrum = scrum.replace(
    "- **[ACTIVE]** API Security Hardening (Remove hardcoded tokens from node_api.py).",
    "- **[DONE]** API Security Hardening (Dynamic token generation & env var enforcement)."
)
scrum = scrum.replace(
    "- **[ACTIVE]** Web Integration: Develop front-end dashboard to interface with node API.",
    "- **[DONE]** Web Integration: Local dashboard (`static/index.html`) integrated directly into `node_api.py`."
)

with open("SCRUM_BOARD.md", "w") as f:
    f.write(scrum)

with open("PROJECT_ROADMAP.md", "r") as f:
    roadmap = f.read()

roadmap = roadmap.replace(
    "- [ ] **API Security (Pre-Mainnet):** Remove hardcoded fallback token",
    "- [x] **API Security (Pre-Mainnet):** Removed hardcoded fallback token"
)
roadmap = roadmap.replace(
    "- **[ACTIVE]** **Web Integration:** Develop front-end dashboard to interface with `node_api.py`.",
    "- [x] **Web Integration:** Developed local HTML/JS front-end dashboard interfacing with `node_api.py`."
)

with open("PROJECT_ROADMAP.md", "w") as f:
    f.write(roadmap)

print("End of day updates written to memory and tracking files.")
