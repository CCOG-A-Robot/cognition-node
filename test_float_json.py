import json
import time
t = time.time()
d1 = json.dumps({"timestamp": t}, sort_keys=True)
parsed = json.loads(d1)
d2 = json.dumps(parsed, sort_keys=True)
print(d1 == d2)
print("d1:", d1)
print("d2:", d2)
