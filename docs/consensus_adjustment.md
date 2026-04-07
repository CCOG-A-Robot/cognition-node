# Documentation: Proportional Difficulty Adjustment (2026-03-20)
*   **Problem:** The previous linear `+/- 1` difficulty adjustment was too conservative, failing to stabilize the 150-second (2.5 min) block time during Testnet testing.
*   **Solution:** Implemented proportional scaling based on the ratio of `target_time` to `actual_time`.
*   **Logic:** `new_difficulty = max(1, int(round(last_block.difficulty * ratio)))` with a damping factor (range 0.5x to 2.0x) applied to prevent extreme network volatility.
*   **Affected File:** `mempool_block.py` (Method: `get_difficulty`)
