import os
import subprocess
import time
from typing import Optional

from .backends.git_backend import GitBackend
from .backends.sapling_backend import SaplingBackend
from .core.workspace_manager import WorkspaceManager
from .core.validator import Validator
from .core.execution_chain import ExecutionChain
from .core.snapshot import Snapshot
from .core.rollback import Rollback
from .core.context_rebuilder import ContextRebuilder
from .metadata.csv_logger import CsvLogger
from .metadata.metadata_branch import MetadataBranch
from ._config import DEFAULTS


BACKEND_MAP = {
    "git": GitBackend,
    "sapling": SaplingBackend,
}


class VersionController:
    def __init__(
        self,
        workspace: str = "./workspace",
        backend: str = "git",
        config: dict = None,
    ):
        self.workspace = os.path.abspath(workspace)
        self.backend_name = backend
        self.config = {**DEFAULTS, **(config or {})}

        self.ws_manager = WorkspaceManager(self.workspace)
        vc_dir = os.path.join(self.workspace, ".version_controller")

        backend_cls = BACKEND_MAP.get(backend)
        if not backend_cls:
            raise ValueError(
                f"Unsupported backend: {backend}. Available: {list(BACKEND_MAP.keys())}"
            )
        self.backend = backend_cls(self.workspace)

        self.csv_logger = CsvLogger(os.path.join(vc_dir, "csv"))
        self.metadata_branch = MetadataBranch(self.workspace)
        self.execution_chain = ExecutionChain(os.path.join(vc_dir, "chains"))
        self.validator = Validator(self.workspace)
        self.snapshot = Snapshot(
            self.backend, self.csv_logger, self.execution_chain, self.validator,
        )
        self.rollbacker = Rollback(self.backend, self.csv_logger, self.execution_chain)
        self.context_rebuilder = ContextRebuilder(
            self.backend, self.csv_logger, self.execution_chain,
        )

        self._current_task_id = None
        self._initialize()

    def _initialize(self):
        if not self.backend.is_initialized():
            self.backend.init_repo()

    # ── task lifecycle ───────────────────────────────────────

    def start_task(self, description: str, task_id: str = None) -> dict:
        tid = task_id or None
        if tid:
            existing = self.csv_logger.get_task(tid)
            if not existing:
                self.csv_logger.start_task(tid, description)
        else:
            task = self.csv_logger.start_task(
                f"T{int(time.time() * 1000) % 100000}", description,
            )
            tid = task["task_id"]
        self._current_task_id = tid
        self.execution_chain.start_task(tid, description)

        self.csv_logger.log_event(tid, {
            "action": "start",
            "status": "active",
            "message": description,
        })
        return {"task_id": tid, "description": description, "status": "active"}

    def save(self, metadata: dict = None) -> dict:
        if not self._current_task_id:
            raise RuntimeError("No active task. Call start_task() first.")
        meta = metadata or {}
        meta.setdefault("agent", self.config.get("agent", "unknown"))
        meta.setdefault("action", self.config.get("action", "modify"))

        result = self.snapshot.create(self._current_task_id, meta)
        self.csv_logger.increment_version(self._current_task_id)
        return result

    def update(self, feedback: Optional[str] = None, metadata: dict = None) -> dict:
        if not self._current_task_id:
            raise RuntimeError("No active task. Call start_task() first.")
        meta = metadata or {}
        if feedback:
            meta["feedback"] = feedback
            head = self.backend.get_head()
            self.csv_logger.append_feedback(self._current_task_id, feedback, head)
            self.csv_logger.increment_feedback(self._current_task_id)
            self.csv_logger.log_event(self._current_task_id, {
                "feedback": feedback,
                "commit_hash": head,
                "status": "feedback",
            })
        return {"task_id": self._current_task_id, "feedback": feedback, "status": "updated"}

    def rollback(
        self,
        commit_id: Optional[str] = None,
        version_index: Optional[int] = None,
    ) -> dict:
        if not self._current_task_id:
            raise RuntimeError("No active task. Call start_task() first.")
        if commit_id:
            result = self.rollbacker.to_commit(commit_id, self._current_task_id)
        elif version_index is not None:
            result = self.rollbacker.to_version(self._current_task_id, version_index)
        else:
            history = self.csv_logger.get_history(self._current_task_id)
            snapshots = [e for e in history if e.get("status") == "snapshot"]
            if len(snapshots) < 2:
                raise RuntimeError("Less than 2 snapshots; nothing to rollback to")
            result = self.rollbacker.to_commit(
                snapshots[-2]["commit_hash"], self._current_task_id,
            )

        self.csv_logger.log_event(self._current_task_id, {
            "commit_hash": result["rolled_back_to"],
            "status": "rollback",
            "parent_hash": result["previous_head"],
        })
        return result

    # ── diff / history / export ──────────────────────────────

    def diff(self, commit_a: str, commit_b: str) -> dict:
        raw = self.backend.diff(commit_a, commit_b)
        files = self._extract_files_from_diff(raw)
        summaries = self._generate_summary_from_diff(raw, commit_a, commit_b)
        return {
            "commit_a": commit_a,
            "commit_b": commit_b,
            "affected_files": files,
            "summaries": summaries,
        }

    def history(self) -> dict:
        if not self._current_task_id:
            raise RuntimeError("No active task. Call start_task() first.")
        task = self.csv_logger.get_task(self._current_task_id)
        chain = self.execution_chain.get_chain(self._current_task_id)
        versions = self.csv_logger.get_history(self._current_task_id)
        feedback = self.csv_logger.get_feedback_chain(self._current_task_id)
        return {
            "task": task,
            "chain": chain,
            "versions": versions,
            "current": chain["current"] if chain else None,
            "feedback": feedback,
        }

    def export_toon(self, task_id: Optional[str] = None) -> str:
        tid = task_id or self._current_task_id
        if not tid:
            raise RuntimeError("No task specified and no active task.")
        if task_id:
            return self.csv_logger.export_to_toon(task_id)
        return self.csv_logger.export_all_toon()

    def reconstruct_context(
        self, task_id: Optional[str] = None, depth: int = 5,
    ) -> dict:
        tid = task_id or self._current_task_id
        if not tid:
            raise RuntimeError("No task specified and no active task.")
        return self.context_rebuilder.rebuild(tid, depth)

    def get_current_task_id(self) -> Optional[str]:
        return self._current_task_id

    # ── track / untrack / remove / status / revert / clean ──

    def track(self, path: str) -> str:
        return self.backend.track(path)

    def untrack(self, path: str) -> str:
        return self.backend.untrack(path)

    def remove(self, path: str) -> str:
        return self.backend.remove(path)

    def status(self) -> str:
        return self.backend.status()

    def revert(self, path: str) -> str:
        return self.backend.revert(path)

    def clean(self) -> str:
        return self.backend.clean()

    def _check_sapling_available(self) -> bool:
        try:
            result = subprocess.run(
                ["sl", "--version"],
                capture_output=True, text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _fallback_undo(self):
        if self.backend_name == "sapling":
            raise RuntimeError(
                "Neither backend supports `undo`. "
                "Install Sapling (https://sapling-scm.com/) and ensure `sl` is in PATH."
            )
        if not self._check_sapling_available():
            raise RuntimeError(
                "Git backend does not support `undo`. "
                "Sapling is not installed or not in PATH.\n"
                "Install: https://sapling-scm.com/docs/introduction/installation\n"
                "Then retry this command."
            )
        sl = SaplingBackend(self.workspace)
        return sl.undo()

    def _fallback_redo(self):
        if self.backend_name == "sapling":
            raise RuntimeError(
                "Neither backend supports `redo`. "
                "Install Sapling (https://sapling-scm.com/) and ensure `sl` is in PATH."
            )
        if not self._check_sapling_available():
            raise RuntimeError(
                "Git backend does not support `redo`. "
                "Sapling is not installed or not in PATH.\n"
                "Install: https://sapling-scm.com/docs/introduction/installation\n"
                "Then retry this command."
            )
        sl = SaplingBackend(self.workspace)
        return sl.redo()

    def _fallback_hide(self, rev: str):
        if self.backend_name == "sapling":
            raise RuntimeError(
                "Neither backend supports `hide`. "
                "Install Sapling (https://sapling-scm.com/) and ensure `sl` is in PATH."
            )
        if not self._check_sapling_available():
            raise RuntimeError(
                "Git backend does not support `hide`. "
                "Sapling is not installed or not in PATH.\n"
                "Install: https://sapling-scm.com/docs/introduction/installation\n"
                "Then retry this command."
            )
        sl = SaplingBackend(self.workspace)
        return sl.hide(rev)

    def _fallback_unhide(self, rev: str):
        if self.backend_name == "sapling":
            raise RuntimeError(
                "Neither backend supports `unhide`. "
                "Install Sapling (https://sapling-scm.com/) and ensure `sl` is in PATH."
            )
        if not self._check_sapling_available():
            raise RuntimeError(
                "Git backend does not support `unhide`. "
                "Sapling is not installed or not in PATH.\n"
                "Install: https://sapling-scm.com/docs/introduction/installation\n"
                "Then retry this command."
            )
        sl = SaplingBackend(self.workspace)
        return sl.unhide(rev)

    # ── undo / redo / hide / unhide / amend / shelve / unshelve ─

    def undo(self):
        try:
            return self.backend.undo()
        except NotImplementedError:
            return self._fallback_undo()

    def redo(self):
        try:
            return self.backend.redo()
        except NotImplementedError:
            return self._fallback_redo()

    def hide(self, rev: str):
        try:
            return self.backend.hide(rev)
        except NotImplementedError:
            return self._fallback_hide(rev)

    def unhide(self, rev: str):
        try:
            return self.backend.unhide(rev)
        except NotImplementedError:
            return self._fallback_unhide(rev)

    def amend(self, message: str) -> str:
        return self.backend.amend(message)

    def shelve(self, name: str) -> str:
        return self.backend.shelve(name)

    def unshelve(self, name: str = None) -> str:
        return self.backend.unshelve(name)

    # ── prev / next ───────────────────────────────────────────

    def prev(self) -> str:
        return self.backend.prev()

    def next(self) -> str:
        return self.backend.next()

    # ── push / pull / sync / restore ──────────────────────────

    def push(self, remote: str = "origin", branch: str = None) -> str:
        return self.backend.push(remote, branch)

    def pull(self, remote: str = "origin", branch: str = None) -> str:
        return self.backend.pull(remote, branch)

    def sync(self, message: str = None) -> dict:
        msg = message or f"VC: sync {self._current_task_id or 'metadata'}"
        csv_files = self.csv_logger.get_all_csv_paths()
        result = self.metadata_branch.sync(csv_files, msg)

        if not result.get("pushed") and result.get("committed"):
            print(
                "Metadata committed to local vc-data branch.\n"
                "To sync across machines:\n"
                "  1. git remote add origin <repository-url>\n"
                "  2. gh auth login --git-protocol https\n"
                "  3. Run vc.sync() again\n"
                "Data is safely stored in .version_controller/csv/"
            )
        return result

    def restore(self) -> dict:
        return self.metadata_branch.restore()

    # ── internal helpers ─────────────────────────────────────

    def _generate_semantic_diff(self, commit_id: str) -> list:
        try:
            parents = self.backend.get_parents(commit_id)
            if not parents:
                return []
            parent = parents[0]
            raw = self.backend.diff(parent, commit_id)
            return self._generate_summary_from_diff(raw, parent, commit_id)
        except Exception:
            return []

    def _generate_summary_from_diff(
        self, raw: str, commit_a: str, commit_b: str,
    ) -> list:
        summaries = []
        if not raw:
            return summaries
        lines = raw.split("\n")
        current_file = None
        changes = {}
        for line in lines:
            if line.startswith("diff --git"):
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[2].replace("a/", "", 1)
                    changes[current_file] = {"added": 0, "removed": 0}
            elif current_file and (line.startswith("+") and not line.startswith("+++")):
                changes[current_file]["added"] += 1
            elif current_file and (line.startswith("-") and not line.startswith("---")):
                changes[current_file]["removed"] += 1
        for fname, stats in sorted(changes.items()):
            if stats["added"] or stats["removed"]:
                summaries.append(
                    f"FILE[{fname}] +{stats['added']} -{stats['removed']}"
                )
        return summaries

    def _extract_files_from_diff(self, raw: str) -> list:
        files = []
        for line in raw.split("\n"):
            if line.startswith("diff --git"):
                parts = line.split()
                if len(parts) >= 4:
                    fname = parts[2].replace("a/", "", 1)
                    if fname not in files:
                        files.append(fname)
        return files
