import time


class Snapshot:
    def __init__(self, backend, csv_logger, execution_chain, validator):
        self.backend = backend
        self.csv_logger = csv_logger
        self.execution_chain = execution_chain
        self.validator = validator

    def create(self, task_id: str, metadata: dict = None) -> dict:
        valid, issues = self.validator.validate()
        if not valid:
            raise RuntimeError(f"Validation failed: {'; '.join(issues)}")

        commit_msg = f"VC:{task_id}"
        if metadata and "action" in metadata:
            commit_msg += f"|{metadata['action']}"

        commit_id = self.backend.commit(commit_msg)
        chain_entry = self.execution_chain.add_version(
            task_id, commit_id, metadata,
        )

        branch = ""
        try:
            branch = self.backend.current_branch()
        except Exception:
            pass

        self.csv_logger.log_event(task_id, {
            "timestamp": str(int(time.time())),
            "commit_hash": commit_id,
            "action": (metadata or {}).get("action", "modify"),
            "agent": (metadata or {}).get("agent", ""),
            "feedback": (metadata or {}).get("feedback", ""),
            "files": ",".join((metadata or {}).get("files", [])),
            "status": "snapshot",
            "parent_hash": (chain_entry or {}).get("parent", "") or "",
            "branch": branch,
            "message": (metadata or {}).get("message", ""),
        })

        self.csv_logger.register_commit(
            commit_id, task_id,
            (chain_entry or {}).get("index", 0),
            branch,
        )

        result = {
            "commit_id": commit_id,
            "task_id": task_id,
            "version_index": (chain_entry or {}).get("index"),
            "parent_commit": (chain_entry or {}).get("parent"),
        }
        return result

    def create_empty(self, task_id: str, metadata: dict = None) -> dict:
        self.backend.stage_all()
        return self.create(task_id, metadata)
