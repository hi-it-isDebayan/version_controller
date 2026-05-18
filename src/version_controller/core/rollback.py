import os


class Rollback:
    def __init__(self, backend, csv_logger, execution_chain):
        self.backend = backend
        self.csv_logger = csv_logger
        self.execution_chain = execution_chain

    def _save_csvs(self) -> dict:
        saved = {}
        for fpath in self.csv_logger.get_all_csv_paths():
            try:
                with open(fpath, "r") as f:
                    saved[fpath] = f.read()
            except OSError:
                pass
        return saved

    def _restore_csvs(self, saved: dict):
        for fpath, content in saved.items():
            try:
                tmp = fpath + ".tmp"
                with open(tmp, "w") as f:
                    f.write(content)
                os.replace(tmp, fpath)
            except OSError:
                pass

    def to_commit(self, commit_id: str, task_id: str = None) -> dict:
        old_head = self.backend.get_head()

        # Save chain state and CSV contents before checkout
        chain_saved = None
        csvs_saved = {}
        if task_id:
            chain_saved = self.execution_chain.get_chain(task_id)
            csvs_saved = self._save_csvs()

        self.backend.checkout(commit_id)

        # Restore CSV contents that checkout may have reverted
        if csvs_saved:
            self._restore_csvs(csvs_saved)

        if task_id and chain_saved:
            self.execution_chain.set_chain(task_id, chain_saved)
            self.execution_chain.rollback_to(task_id, commit_id)
            self.csv_logger.log_event(task_id, {
                "commit_hash": commit_id,
                "parent_hash": old_head,
                "status": "rollback",
            })

        return {"rolled_back_to": commit_id, "previous_head": old_head}

    def to_previous(self, commit_id: str, task_id: str = None) -> dict:
        parents = self.backend.get_parents(commit_id)
        if not parents:
            raise ValueError(f"Commit {commit_id} has no parent")
        return self.to_commit(parents[0], task_id)

    def to_version(self, task_id: str, version_index: int) -> dict:
        history = self.csv_logger.get_history(task_id)
        snapshots = [e for e in history if e.get("status") == "snapshot"]
        if version_index < 0 or version_index >= len(snapshots):
            raise ValueError(
                f"Version index {version_index} out of range "
                f"(0-{len(snapshots) - 1}) for task {task_id}"
            )
        commit_hash = snapshots[version_index].get("commit_hash", "")
        if not commit_hash:
            raise ValueError(f"No commit hash found for version {version_index}")
        return self.to_commit(commit_hash, task_id)
