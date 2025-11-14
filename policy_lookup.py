import json
import regex as re
from pathlib import Path

DATA_FILE = Path("policy_rules.json")

def load_mappings():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)["mappings"]

def find_insurer(policy_id: str):
    policy_id = policy_id.strip()
    mappings = load_mappings()

    # First try matching company name inside the ID
    for m in mappings:
        if m["insurer_name"].lower() in policy_id.lower():
            return m

    # Then try regex pattern matching
    for m in mappings:
        for pattern in m["patterns"]:
            if pattern and re.search(pattern, policy_id):
                return m

    # Fallback: UNKNOWN
    for m in mappings:
        if m["insurer_key"] == "UNKNOWN":
            return m

    return None


if __name__ == "__main__":
    test_ids = [
        "P/20/9876543",
        "407112345678",
        "ICICI-5567788",
        "SH-445566",
        "ABC12345"
    ]

    for pid in test_ids:
        match = find_insurer(pid)
        print(f"Policy ID: {pid}")
        print(f"Matched: {match['insurer_name']} ({match['insurer_key']})")
        print("Features:", match["features"])
        print("-" * 40)

