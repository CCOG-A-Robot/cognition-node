import json
with open('blockchain.json', 'r') as f:
    data = json.load(f)

for b in data:
    if len(b['transactions']) > 1:
        print(f"Block {b['index']} has {len(b['transactions'])} txs!")
        for tx in b['transactions']:
            print(tx['tx_id'], tx['outputs'])
