import collections

# 1. Define Molecule Blocks and Enzyme Blocks
enzymes = {
    "E1": (("A", "B"), ("C",)),
    "E2": (("C",), ("D", "E")),
    "E3": (("D", "F"), ("G",)),
    "E4": (("E", "H"), ("I",)),
    "E5": (("G", "I"), ("J",)),
    "E6": (("K", "L"), ("M",)), # New branch, independent start
    "E7": (("M", "A"), ("N",)),
    "E8": (("J", "N"), ("O",)), # Combines results from E5 and E7
    "E9": (("H", "B"), ("P",)), # Another side branch/distractor
    "E10": (("P", "E"), ("Q",)) # Final product using a side branch
}

# 2. Define a puzzle instance (10x More Complex)
starting_materials = frozenset(["A", "B", "F", "H", "K", "L"])
target_product = "Q"

# 3. Implement solve_puzzle function using BFS
def solve_puzzle(start_materials, target, enzymes_dict):
    queue = collections.deque([(start_materials, [])]) 
    visited_states = {start_materials}

    while queue:
        current_materials, current_path_with_hashes = queue.popleft()

        if target in current_materials:
            return current_path_with_hashes

        for enzyme_name, (inputs, outputs) in enzymes_dict.items():
            if all(mol in current_materials for mol in inputs):
                new_materials_set = set(current_materials)
                for inp in inputs:
                    new_materials_set.remove(inp)
                for out in outputs:
                    new_materials_set.add(out)
                new_materials = frozenset(new_materials_set)
                new_materials_hash = hash(new_materials)

                if new_materials not in visited_states:
                    visited_states.add(new_materials)
                    queue.append((new_materials, current_path_with_hashes + [(enzyme_name, new_materials_hash)]))
    return None

# 4. Implement verify_pathway function
def verify_pathway(start_materials, target, enzymes_dict, proposed_path_with_hashes):
    current_materials_set = set(start_materials)
    path_details = []

    for enzyme_name, expected_materials_hash in proposed_path_with_hashes:
        if enzyme_name not in enzymes_dict:
            path_details.append(f"Verification Failed: Enzyme \'{enzyme_name}\' not recognized.")
            return False, path_details

        inputs, outputs = enzymes_dict[enzyme_name]
        
        if not all(mol in current_materials_set for mol in inputs):
            path_details.append(f"Verification Failed: Enzyme \'{enzyme_name}\' requires inputs {inputs}, but only {current_materials_set} are available.")
            return False, path_details
        
        for inp in inputs:
            current_materials_set.remove(inp)
        for out in outputs:
            current_materials_set.add(out)
        
        actual_materials_hash = hash(frozenset(current_materials_set))
        if actual_materials_hash != expected_materials_hash:
            path_details.append(f"Verification Failed: Hash mismatch after applying {enzyme_name}. Expected: {expected_materials_hash}, Actual: {actual_materials_hash}")
            return False, path_details

        path_details.append(f"Applied {enzyme_name}: inputs {inputs} -> outputs {outputs}. Materials hash verified: {expected_materials_hash}")

    if target in current_materials_set:
        path_details.append(f"Verification Succeeded: Target product \'{target}\' found in final materials {current_materials_set}.")
        return True, path_details
    else:
        path_details.append(f"Verification Failed: Target product \'{target}\' not found in final materials {current_materials_set}.")
        return False, path_details

# 5. Run the puzzle and print the results
print("--- Running Puzzle Solver (Enhanced Trace) ---")
enhanced_path = solve_puzzle(starting_materials, target_product, enzymes)

if enhanced_path:
    print(f"Solution Path Found (Enzyme, State Hash): {enhanced_path}")
    print("\n--- Verifying Solution (with State Hashes) ---")
    is_valid, details = verify_pathway(starting_materials, target_product, enzymes, enhanced_path)
    print("\n".join(details))
    print(f"Overall Verification Result: {'SUCCESS' if is_valid else 'FAILED'}")
else:
    print("No solution path found for the given puzzle.")
