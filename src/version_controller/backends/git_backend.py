import os
import subprocess
from typing import Optional, Any


class GitBackend:
    def __init__(self, workspace: str):
        self.workspace = os.path.abspath(workspace)

    def _run(self, *args: str, input_str: str = None) -> str:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            cwd=self.workspace,
            input=input_str,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git error: {result.stderr.strip()}")
        return result.stdout.strip()

    # ── init / config ────────────────────────────────────────

    def is_initialized(self) -> bool:
        return os.path.isdir(os.path.join(self.workspace, ".git"))

    def init_repo(self) -> str:
        if self.is_initialized():
            return self._run("rev-parse", "--git-dir")
        self._run("init")
        self._run("config", "user.email", "version-controller@ai.local")
        self._run("config", "user.name", "VersionController")
        return self._run("rev-parse", "--git-dir")

    def config(self, key: str, value: str) -> str:
        return self._run("config", key, value)

    # ── commit / stage / head ─────────────────────────────────

    def stage_all(self) -> str:
        return self._run("add", "-A")

    def commit(self, message: str) -> str:
        self.stage_all()
        self._run("commit", "--allow-empty", "-m", message)
        return self._run("rev-parse", "HEAD")

    def get_head(self) -> str:
        return self._run("rev-parse", "HEAD")

    # ── checkout / reset / branch ────────────────────────────

    def checkout(self, commit_id: str) -> str:
        self._run("checkout", "--force", commit_id)
        return self.get_head()

    def reset(self, commit_id: str, mode: str = "hard") -> str:
        self._run("reset", f"--{mode}", commit_id)
        return self.get_head()

    def branch(self, name: str) -> str:
        return self._run("branch", name)

    def current_branch(self) -> str:
        return self._run("rev-parse", "--abbrev-ref", "HEAD")

    # ── diff / log / parents ──────────────────────────────────

    def diff(self, commit_a: str, commit_b: str) -> str:
        return self._run("diff", commit_a, commit_b)

    def log(self, max_count: int = 50) -> list:
        output = self._run(
            "log", f"--max-count={max_count}",
            "--format=%H|%s|%an|%at"
        )
        if not output:
            return []
        entries = []
        for line in output.split("\n"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                entries.append({
                    "commit": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "timestamp": parts[3],
                })
        return entries

    def get_parents(self, commit_id: str) -> list:
        output = self._run("rev-list", "--parents", "-n", "1", commit_id)
        parts = output.strip().split()
        return parts[1:] if len(parts) > 1 else []

    def find_merge_base(self, commit_a: str, commit_b: str) -> str:
        return self._run("merge-base", commit_a, commit_b)

    # ── file operations ──────────────────────────────────────

    def file_list(self, commit_id: str) -> list:
        output = self._run("ls-tree", "-r", "--name-only", commit_id)
        return output.split("\n") if output else []

    def show_file(self, commit_id: str, path: str) -> str:
        return self._run("show", f"{commit_id}:{path}")

    # ── track / untrack / remove / status / revert / clean ───

    def track(self, path: str) -> str:
        return self._run("add", path)

    def untrack(self, path: str) -> str:
        return self._run("rm", "--cached", path)

    def remove(self, path: str) -> str:
        return self._run("rm", path)

    def status(self) -> str:
        return self._run("status", "--porcelain")

    def revert(self, path: str) -> str:
        return self._run("checkout", "--", path)

    def clean(self) -> str:
        return self._run("clean", "-fd")

    # ── undo / amend / shelve / unshelve ──────────────────────

    def undo(self):
        raise NotImplementedError(
            "Git backend does not support `undo`. "
            "Install Sapling (https://sapling-scm.com/) for automatic fallback."
        )

    def redo(self):
        raise NotImplementedError(
            "Git backend does not support `redo`. "
            "Install Sapling (https://sapling-scm.com/) for automatic fallback."
        )

    def hide(self, rev: str):
        raise NotImplementedError(
            "Git backend does not support `hide`. "
            "Install Sapling (https://sapling-scm.com/) for automatic fallback."
        )

    def unhide(self, rev: str):
        raise NotImplementedError(
            "Git backend does not support `unhide`. "
            "Install Sapling (https://sapling-scm.com/) for automatic fallback."
        )

    def amend(self, message: str) -> str:
        self._run("commit", "--amend", "-m", message)
        return self._run("rev-parse", "HEAD")

    def shelve(self, name: str) -> str:
        return self._run("stash", "push", "-m", name)

    def unshelve(self, name: str = None) -> str:
        if name:
            output = self._run("stash", "list")
            for line in output.split("\n"):
                if name in line:
                    stash_ref = line.split(":")[0].strip()
                    return self._run("stash", "pop", stash_ref)
            raise RuntimeError(f"No stash found matching: {name}")
        return self._run("stash", "pop")

    # ── prev / next ──────────────────────────────────────────

    def prev(self) -> str:
        self._run("checkout", "HEAD~1")
        return self.get_head()

    def next(self) -> str:
        output = self._run(
            "log", "--reverse", "--ancestry-path",
            "HEAD..@{-1}", "--format=%H",
        )
        if not output:
            raise RuntimeError("No child commit found on current branch")
        child = output.strip().split("\n")[0]
        self._run("checkout", child)
        return self.get_head()

    # ── remote / push / pull ──────────────────────────────────

    def has_remote(self) -> bool:
        try:
            output = self._run("remote", "-v")
            return bool(output.strip())
        except RuntimeError:
            return False

    def remote_url(self) -> str:
        return self._run("remote", "get-url", "origin")

    def push(self, remote: str = "origin", branch: str = None) -> str:
        if branch:
            return self._run("push", remote, branch)
        return self._run("push", remote)

    def pull(self, remote: str = "origin", branch: str = None) -> str:
        if branch:
            return self._run("pull", remote, branch)
        return self._run("pull", remote)

    def push_branch(self, branch: str) -> str:
        return self._run("push", "origin", branch)

    def fetch_branch(self, branch: str) -> str:
        return self._run("fetch", "origin", branch)

    # ── low-level git plumbing for metadata branch ────────────

    def hash_object(self, content: str) -> str:
        return self._run("hash-object", "-w", "--stdin", input_str=content)

    def mktree(self, tree_input: str) -> str:
        return self._run("mktree", input_str=tree_input)

    def commit_tree(self, tree_hash: str, message: str, parent: str = None) -> str:
        if parent:
            return self._run(
                "commit-tree", tree_hash,
                "-p", parent, "-m", message,
                input_str="",
            )
        return self._run("commit-tree", tree_hash, "-m", message, input_str="")

    def update_ref(self, ref: str, commit_hash: str) -> str:
        return self._run("update-ref", ref, commit_hash)

    def read_tree(self, ref: str, path: str) -> str:
        return self._run("show", f"{ref}:{path}")

    def ls_tree(self, ref: str) -> str:
        return self._run("ls-tree", "-r", ref)

    def ls_remote(self, remote: str, ref: str) -> str:
        return self._run("ls-remote", "--heads", remote, ref)

    # ── cleanup ───────────────────────────────────────────────

    def cleanup(self):
        pass
