import os
import shutil

WORKSPACE_ROOT = None

def set_workspace_root(path: str):
    global WORKSPACE_ROOT
    WORKSPACE_ROOT = os.path.abspath(path)

def get_workspace_root() -> str:
    if WORKSPACE_ROOT is None:
        raise RuntimeError("Workspace root not set. Call set_workspace_root() first.")
    return WORKSPACE_ROOT

def path_within_workspace(path: str) -> str:
    root = get_workspace_root()
    abs_path = os.path.abspath(os.path.join(root, path))
    if not abs_path.startswith(os.path.abspath(root)):
        raise PermissionError(f"Access denied: {path} is outside workspace {root}")
    return abs_path

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def safe_read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def safe_write(path: str, content: str):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def safe_delete(path: str):
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
