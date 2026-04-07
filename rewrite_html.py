import re

with open("static/index.html", "r") as f:
    html = f.read()

# 1. Extract panels
active_wallet_start = html.find('<div class="panel">\n                <h2>Active Wallet</h2>')
if active_wallet_start == -1:
    print("Cannot find active wallet panel")

# 2. We can just replace the whole body since it's short, or carefully substitute.
# Let's do a carefully crafted string replacement or full write.
