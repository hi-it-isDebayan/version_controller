import hashlib
import os

def hash_string(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

def hash_file(filepath: str) -> str:
    if not os.path.isfile(filepath):
        return ""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]

def consistent_hash(*components: str) -> str:
    combined = "|".join(str(c) for c in components)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]
