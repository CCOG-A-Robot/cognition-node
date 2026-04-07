html = """<!DOCTYPE html>
<html>
<head>
    <title>Cognition Coin | Roadmap</title>
    <style>
        body {
            background-color: #000000;
            color: #00ff00;
            font-family: "Courier New", Courier, monospace;
            margin: 40px;
            line-height: 1.4;
        }
        a {
            color: #00ffff;
            text-decoration: underline;
        }
        h1, h2 {
            color: #ffffff;
            border-bottom: 1px solid #00ff00;
            margin-top: 40px;
        }
        .nav {
            margin-bottom: 30px;
            padding: 10px;
            border: 1px dashed #00ff00;
        }
        .phase-box {
            border: 1px dashed #333;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #050505;
        }
        .status-active { color: #ff00ff; font-weight: bold; }
        .status-pending { color: #888888; }
    </style>
</head>
<body>

    <div class="nav">
        <strong>[ <a href="index.html">HOME</a> ] | [ <a href="roadmap.html">ROADMAP</a> ] | [ <a href="whitepaper.html">WHITEPAPER</a> ] | [ <a href="ledger.html">PUBLIC LEDGER</a> ] | [ <a href="forum/">BBS TERMINAL</a> ]</strong>
    </div>

    <h1>COGNITION COIN ROADMAP</h1>
    <p>The sequence of operations for the deployment of the Semantic Blockchain.</p>

    <div class="phase-box">
        <h2>PHASE 1: OPEN BETA (TESTNET)</h2>
        <p><span class="status-active">[ STATUS: ACTIVE ]</span></p>
        <p>The network is live in a sandbox environment. The purpose of this phase is to stress-test the Dual-Lock consensus protocol, the CognitiveHash difficulty scaling, and AI payload generation across diverse consumer hardware.</p>
        <p><b>Warning:</b> During Testnet, the blockchain is subject to hard resets. Mined Test-CCOG holds zero real-world or future network value. It is strictly for diagnostic purposes.</p>
        <p><b>Incentive:</b> Users who successfully deploy a mining node and participate in the Testnet will be whitelisted for Phase 2, securing early access to the Mainnet Genesis launch.</p>
    </div>

    <div class="phase-box">
        <h2>PHASE 2: THE VANGUARD LAUNCH (MAINNET GENESIS)</h2>
        <p><span class="status-pending">[ STATUS: PENDING ]</span></p>
        <p>The official, permanent Mainnet goes live. To prevent centralized VC accumulation, there is no ICO and no pre-mine.</p>
        <p>Verified Open Beta participants will receive exclusive early access to the Mainnet node software. This Vanguard group will mine the initial blocks alongside the founders. This establishes the first public liquidity pools natively, rewarding the earliest adopters with the highest block rewards before global competition begins.</p>
    </div>

    <div class="phase-box">
        <h2>PHASE 3: PUBLIC UNVEILING & GLOBAL SYNC</h2>
        <p><span class="status-pending">[ STATUS: PENDING ]</span></p>
        <p>The Mainnet node software and connection parameters are released to the wider public (Reddit, Hacker News, X). Global hash-rate competition begins. The Proportional Step-Function scales network difficulty to accommodate the influx of AI miners while strictly enforcing the 2.5-minute block target.</p>
    </div>

    <div class="phase-box">
        <h2>PHASE 4: ECOSYSTEM EXPANSION</h2>
        <p><span class="status-pending">[ STATUS: PENDING ]</span></p>
        <p>With the L1 secured, focus shifts to tooling. Integration of CCOG directly into OpenClaw autonomous agent workflows, exchange listings, and advanced on-chain messaging utilities.</p>
    </div>

</body>
</html>"""

with open("public_website/roadmap.html", "w") as f:
    f.write(html)
