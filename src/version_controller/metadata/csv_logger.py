import os
import csv
import sys
import time
from typing import Optional, Callable, Any

from ..utils.file_ops import ensure_dir
from ..logs.serializer import serialize_toon


def _with_lock(lock_path: str, mode: str, fn: Callable) -> Any:
    if sys.platform == "win32":
        import msvcrt
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        try:
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            try:
                return fn()
            finally:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        finally:
            os.close(fd)
    else:
        import fcntl
        with open(lock_path, "w") as lf:
            mode_flag = fcntl.LOCK_EX if mode == "w" else fcntl.LOCK_SH
            fcntl.flock(lf, mode_flag)
            try:
                return fn()
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)


def _atomic_write(path: str, rows: list, fieldnames: list):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    os.rename(tmp_path, path)


def _read_csv(path: str) -> list:
    if not os.path.isfile(path):
        return []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _append_csv(path: str, row: dict, fieldnames: list):
    ensure_dir(os.path.dirname(path))
    existing = _read_csv(path) if os.path.isfile(path) else []
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing:
            writer.writerow(r)
        writer.writerow(row)
    os.rename(tmp_path, path)


class CsvLogger:
    def __init__(self, csv_dir: str):
        self.csv_dir = csv_dir
        self._lock_path = os.path.join(csv_dir, ".csv_lock")
        ensure_dir(csv_dir)

    # ── path helpers ──────────────────────────────────────────

    def _tasks_path(self) -> str:
        return os.path.join(self.csv_dir, "tasks.csv")

    def _commit_map_path(self) -> str:
        return os.path.join(self.csv_dir, "commit_map.csv")

    def _exec_log_path(self, task_id: str) -> str:
        return os.path.join(self.csv_dir, f"execution_log_{task_id}.csv")

    def _feedback_path(self, task_id: str) -> str:
        return os.path.join(self.csv_dir, f"feedback_{task_id}.csv")

    # ── tasks.csv operations ──────────────────────────────────

    TASKS_FIELDS = [
        "task_id", "description", "status",
        "created_at", "version_count", "feedback_count",
    ]

    def start_task(self, task_id: str, description: str) -> dict:
        row = {
            "task_id": task_id,
            "description": description,
            "status": "active",
            "created_at": str(int(time.time())),
            "version_count": "0",
            "feedback_count": "0",
        }
        path = self._tasks_path()
        def _do():
            _append_csv(path, row, self.TASKS_FIELDS)
            return row
        return _with_lock(self._lock_path, "w", _do)

    def get_task(self, task_id: str) -> Optional[dict]:
        def _do():
            for row in _read_csv(self._tasks_path()):
                if row["task_id"] == task_id:
                    return row
            return None
        return _with_lock(self._lock_path, "r", _do)

    def list_tasks(self) -> list:
        def _do():
            return _read_csv(self._tasks_path())
        return _with_lock(self._lock_path, "r", _do)

    def update_task(self, task_id: str, **updates) -> dict:
        path = self._tasks_path()
        def _do():
            rows = _read_csv(path)
            found = None
            for row in rows:
                if row["task_id"] == task_id:
                    for k, v in updates.items():
                        if k in self.TASKS_FIELDS:
                            row[k] = str(v)
                    found = row
                    break
            if found:
                _atomic_write(path, rows, self.TASKS_FIELDS)
            return found
        return _with_lock(self._lock_path, "w", _do)

    def increment_version(self, task_id: str):
        task = self.get_task(task_id)
        if task:
            self.update_task(
                task_id,
                version_count=int(task.get("version_count", 0)) + 1,
            )

    def increment_feedback(self, task_id: str):
        task = self.get_task(task_id)
        if task:
            self.update_task(
                task_id,
                feedback_count=int(task.get("feedback_count", 0)) + 1,
            )

    # ── execution_log_{task_id}.csv operations ────────────────

    EXEC_LOG_FIELDS = [
        "timestamp", "commit_hash", "action", "agent",
        "feedback", "files", "status", "parent_hash",
        "branch", "message",
    ]

    def log_event(self, task_id: str, fields: dict) -> dict:
        path = self._exec_log_path(task_id)
        row = {f: fields.get(f, "") for f in self.EXEC_LOG_FIELDS}
        if "timestamp" not in fields or not fields.get("timestamp"):
            row["timestamp"] = str(int(time.time()))
        def _do():
            _append_csv(path, row, self.EXEC_LOG_FIELDS)
            return row
        return _with_lock(self._lock_path, "w", _do)

    def get_history(self, task_id: str) -> list:
        def _do():
            return _read_csv(self._exec_log_path(task_id))
        return _with_lock(self._lock_path, "r", _do)

    def search_by_time(self, task_id: str, start: int, end: int) -> list:
        def _do():
            results = []
            for row in _read_csv(self._exec_log_path(task_id)):
                ts = int(row.get("timestamp", 0))
                if start <= ts <= end:
                    results.append(row)
            return results
        return _with_lock(self._lock_path, "r", _do)

    # ── feedback_{task_id}.csv operations ─────────────────────

    FEEDBACK_FIELDS = ["timestamp", "task_id", "feedback", "commit_hash"]

    def append_feedback(self, task_id: str, feedback: str, commit_hash: str) -> dict:
        path = self._feedback_path(task_id)
        row = {
            "timestamp": str(int(time.time())),
            "task_id": task_id,
            "feedback": feedback,
            "commit_hash": commit_hash,
        }
        def _do():
            _append_csv(path, row, self.FEEDBACK_FIELDS)
            return row
        return _with_lock(self._lock_path, "w", _do)

    def get_feedback_chain(self, task_id: str) -> list:
        def _do():
            return _read_csv(self._feedback_path(task_id))
        return _with_lock(self._lock_path, "r", _do)

    # ── commit_map.csv operations ─────────────────────────────

    COMMIT_MAP_FIELDS = [
        "commit_hash", "short_hash", "task_id",
        "version_index", "timestamp", "branch",
    ]

    def register_commit(
        self, commit_hash: str, task_id: str,
        version_index: int, branch: str = ""
    ) -> dict:
        path = self._commit_map_path()
        row = {
            "commit_hash": commit_hash,
            "short_hash": commit_hash[:12],
            "task_id": task_id,
            "version_index": str(version_index),
            "timestamp": str(int(time.time())),
            "branch": branch,
        }
        def _do():
            _append_csv(path, row, self.COMMIT_MAP_FIELDS)
            return row
        return _with_lock(self._lock_path, "w", _do)

    def search_by_commit(self, commit_hash: str) -> Optional[dict]:
        short = commit_hash[:12]
        def _do():
            for row in _read_csv(self._commit_map_path()):
                if row["commit_hash"] == commit_hash or row["short_hash"] == short:
                    return row
            return None
        return _with_lock(self._lock_path, "r", _do)

    def get_commits_for_task(self, task_id: str) -> list:
        def _do():
            return [
                r for r in _read_csv(self._commit_map_path())
                if r["task_id"] == task_id
            ]
        return _with_lock(self._lock_path, "r", _do)

    # ── TOON export ───────────────────────────────────────────

    def export_to_toon(self, task_id: str) -> str:
        def _do():
            entries = _read_csv(self._exec_log_path(task_id))
            if not entries:
                return ""
            cleaned = []
            for e in entries:
                cleaned.append({k: v for k, v in e.items() if v})
            return serialize_toon(cleaned)
        return _with_lock(self._lock_path, "r", _do)

    def export_all_toon(self) -> str:
        def _do():
            all_entries = []
            if not os.path.isdir(self.csv_dir):
                return ""
            for fname in sorted(os.listdir(self.csv_dir)):
                if fname.startswith("execution_log_") and fname.endswith(".csv"):
                    path = os.path.join(self.csv_dir, fname)
                    for e in _read_csv(path):
                        cleaned = {k: v for k, v in e.items() if v}
                        if cleaned:
                            all_entries.append(cleaned)
            return serialize_toon(all_entries)
        return _with_lock(self._lock_path, "r", _do)

    # ── metadata branch helpers ───────────────────────────────

    def get_all_csv_paths(self) -> list:
        paths = []
        if not os.path.isdir(self.csv_dir):
            return paths
        for fname in os.listdir(self.csv_dir):
            if fname.endswith(".csv") and fname != ".csv_lock":
                paths.append(os.path.join(self.csv_dir, fname))
        return sorted(paths)

    def get_csv_contents_by_rel(self, rel_from_vc: str) -> Optional[str]:
        full_path = os.path.join(self.csv_dir, rel_from_vc)
        if not os.path.isfile(full_path):
            return None
        with open(full_path, "r") as f:
            return f.read()

    def write_csv_from_rel(self, rel_from_vc: str, content: str):
        full_path = os.path.join(self.csv_dir, rel_from_vc)
        ensure_dir(os.path.dirname(full_path))
        tmp_path = full_path + ".tmp"
        with open(tmp_path, "w") as f:
            f.write(content)
        os.rename(tmp_path, full_path)

    def rel_path_from_vc(self, abs_path: str) -> str:
        vc_dir = os.path.dirname(self.csv_dir)
        return os.path.relpath(abs_path, vc_dir)
