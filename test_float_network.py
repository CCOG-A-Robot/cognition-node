import json, time
original_float = time.time()
print("Original:", original_float)
# Simulate network transit
network_string = json.dumps({"timestamp": original_float})
received_dict = json.loads(network_string)
received_float = received_dict["timestamp"]
print("Received:", received_float)
# Simulate recalculate hash
hash_string = json.dumps({"timestamp": received_float}, sort_keys=True)
original_hash_string = json.dumps({"timestamp": original_float}, sort_keys=True)
print("Hash strings match?", hash_string == original_hash_string)
