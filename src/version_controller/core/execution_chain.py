import os
from typing import Optional
from ..utils.file_ops import safe_read, safe_write, ensure_dir


class ExecutionChain:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        ensure_dir(self.storage_path)

    def _chain_path(self, task_id: str) -> str:
        return os.path.join(self.storage_path, f"{task_id}.chain")

    def start_task(self, task_id: str, description: str = "") -> dict:
        chain = {
            "task_id": task_id,
            "description": description,
            "versions": [],
            "current": None,
        }
        self._write_chain(task_id, chain)
        return chain

    def add_version(self, task_id: str, commit_id: str, metadata: dict = None) -> dict:
        chain = self.get_chain(task_id) or self.start_task(task_id)
        version = {
            "commit": commit_id,
            "parent": chain.get("current"),
            "index": len(chain["versions"]),
        }
        if metadata:
            version.update(metadata)
        chain["versions"].append(version)
        chain["current"] = commit_id
        self._write_chain(task_id, chain)
        return version

    def get_chain(self, task_id: str) -> Optional[dict]:
        path = self._chain_path(task_id)
        if not os.path.exists(path):
            return None
        content = safe_read(path)
        import json
        return json.loads(content)

    def get_all_chains(self) -> dict:
        result = {}
        if not os.path.isdir(self.storage_path):
            return result
        for fname in os.listdir(self.storage_path):
            if fname.endswith(".chain"):
                task_id = fname[:-6]
                result[task_id] = self.get_chain(task_id)
        return result

    def rollback_to(self, task_id: str, commit_id: str) -> dict:
        chain = self.get_chain(task_id)
        if not chain:
            raise ValueError(f"No chain found for task {task_id}")
        for v in chain["versions"]:
            if v["commit"] == commit_id:
                chain["current"] = commit_id
                self._write_chain(task_id, chain)
                return v
        raise ValueError(f"Commit {commit_id} not found in chain for task {task_id}")

    def get_lineage(self, task_id: str) -> list:
        chain = self.get_chain(task_id)
        if not chain:
            return []
        lineage = []
        for v in chain["versions"]:
            lineage.append({
                "commit": v["commit"],
                "parent": v.get("parent"),
                "index": v.get("index"),
            })
        return lineage

    def set_chain(self, task_id: str, chain: dict):
        self._write_chain(task_id, chain)

    def _write_chain(self, task_id: str, chain: dict):
        import json
        path = self._chain_path(task_id)
        safe_write(path, json.dumps(chain, indent=2))
