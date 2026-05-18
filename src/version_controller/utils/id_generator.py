import uuid
import time
import hashlib

def generate_task_id() -> str:
    return f"T{int(time.time() * 1000) % 100000}"

def generate_commit_id() -> str:
    return hashlib.sha256(f"{time.time_ns()}{uuid.uuid4()}".encode()).hexdigest()[:12]

def generate_session_id() -> str:
    return str(uuid.uuid4())[:8]
