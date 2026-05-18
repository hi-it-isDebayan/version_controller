import os
import subprocess


class SaplingBackend:
    def __init__(self, workspace: str):
        self.workspace = os.path.abspath(workspace)

    def _run(self, *args: str, input_str: str = None) -> str:
        result = subprocess.run(
            ["sl"] + list(args),
            capture_output=True,
            text=True,
            cwd=self.workspace,
            input=input_str,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Sapling error: {result.stderr.strip()}")
        return result.stdout.strip()

    # ── init / config ────────────────────────────────────────

    def is_initialized(self) -> bool:
        return os.path.isdir(os.path.join(self.workspace, ".sl"))

    def init_repo(self) -> str:
        if self.is_initialized():
            return self._run("root")
        self._run("init")
        self._run("config", "ui.username", "VersionController <version-controller@ai.local>")
        return self._run("root")

    def config(self, key: str, value: str) -> str:
        return self._run("config", key, value)

    # ── commit / stage / head ─────────────────────────────────

    def stage_all(self) -> str:
        return self._run("add", ".")

    def commit(self, message: str) -> str:
        self.stage_all()
        self._run("commit", "-m", message)
        return self._run("log", "-r", ".", "-T", "{node}")

    def get_head(self) -> str:
        return self._run("log", "-r", ".", "-T", "{node}")

    # ── goto / reset / bookmark ──────────────────────────────

    def checkout(self, commit_id: str) -> str:
        self._run("goto", commit_id)
        return self.get_head()

    def reset(self, commit_id: str, mode: str = "hard") -> str:
        self._run("goto", commit_id, "--clean")
        return self.get_head()

    def branch(self, name: str) -> str:
        return self._run("bookmark", name)

    def current_branch(self) -> str:
        try:
            return self._run("bookmark")
        except RuntimeError:
            return "default"

    # ── diff / log / parents ──────────────────────────────────

    def diff(self, commit_a: str, commit_b: str) -> str:
        return self._run("diff", "-r", commit_a, "-r", commit_b)

    def log(self, max_count: int = 50) -> list:
        template = "{node}|{desc|firstline}|{author}|{date}"
        output = self._run(
            "log", "-r", "reverse(::.)",
            "-T", f"{template}\n",
        )
        if not output:
            return []
        lines = output.strip().split("\n")
        entries = []
        for line in lines[-max_count:]:
            parts = line.strip().split("|", 3)
            if len(parts) == 4:
                entries.append({
                    "commit": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "timestamp": parts[3],
                })
        return entries

    def get_parents(self, commit_id: str) -> list:
        output = self._run("log", "-r", commit_id, "-T", "{parents}")
        return output.strip().split() if output else []

    def find_merge_base(self, commit_a: str, commit_b: str) -> str:
        output = self._run("log", "-r", f"ancestor({commit_a}, {commit_b})", "-T", "{node}")
        return output.strip()

    # ── file operations ──────────────────────────────────────

    def file_list(self, commit_id: str) -> list:
        output = self._run("manifest", "-r", commit_id)
        return output.strip().split("\n") if output else []

    def show_file(self, commit_id: str, path: str) -> str:
        return self._run("cat", "-r", commit_id, path)

    # ── track / untrack / remove / status / revert / clean ───

    def track(self, path: str) -> str:
        return self._run("add", path)

    def untrack(self, path: str) -> str:
        return self._run("forget", path)

    def remove(self, path: str) -> str:
        return self._run("remove", path)

    def status(self) -> str:
        return self._run("status")

    def revert(self, path: str) -> str:
        return self._run("revert", path)

    def clean(self) -> str:
        return self._run("clean")

    # ── undo / redo / hide / unhide / amend / shelve ──────────

    def undo(self) -> str:
        return self._run("undo")

    def redo(self) -> str:
        return self._run("redo")

    def hide(self, rev: str) -> str:
        return self._run("hide", "-r", rev)

    def unhide(self, rev: str) -> str:
        return self._run("unhide", "-r", rev)

    def amend(self, message: str) -> str:
        self._run("amend", "-m", message)
        return self._run("log", "-r", ".", "-T", "{node}")

    def shelve(self, name: str) -> str:
        return self._run("shelve", "--name", name)

    def unshelve(self, name: str = None) -> str:
        if name:
            return self._run("unshelve", name)
        return self._run("unshelve")

    # ── prev / next ──────────────────────────────────────────

    def prev(self) -> str:
        self._run("prev")
        return self.get_head()

    def next(self) -> str:
        self._run("next")
        return self.get_head()

    # ── remote / push / pull ──────────────────────────────────

    def has_remote(self) -> bool:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True, text=True,
            cwd=self.workspace,
        )
        return result.returncode == 0 and result.stdout.strip() != ""

    def remote_url(self) -> str:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True,
            cwd=self.workspace,
        )
        if result.returncode != 0:
            raise RuntimeError("No remote configured")
        return result.stdout.strip()

    def push(self, remote: str = "origin", branch: str = None) -> str:
        if branch:
            return self._run("push", "--to", branch)
        return self._run("push")

    def pull(self, remote: str = "origin", branch: str = None) -> str:
        return self._run("pull")

    def push_branch(self, branch: str) -> str:
        return self._run("push", "--to", branch)

    def fetch_branch(self, branch: str) -> str:
        return self._run("pull")

    # ── low-level git plumbing for metadata branch ────────────

    def hash_object(self, content: str) -> str:
        result = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            capture_output=True, text=True,
            cwd=self.workspace,
            input=content,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git hash-object error: {result.stderr.strip()}")
        return result.stdout.strip()

    def mktree(self, tree_input: str) -> str:
        result = subprocess.run(
            ["git", "mktree"],
            capture_output=True, text=True,
            cwd=self.workspace,
            input=tree_input,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git mktree error: {result.stderr.strip()}")
        return result.stdout.strip()

    def commit_tree(self, tree_hash: str, message: str, parent: str = None) -> str:
        args = ["git", "commit-tree", tree_hash]
        if parent:
            args.extend(["-p", parent])
        args.extend(["-m", message])
        result = subprocess.run(
            args, capture_output=True, text=True,
            cwd=self.workspace,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git commit-tree error: {result.stderr.strip()}")
        return result.stdout.strip()

    def update_ref(self, ref: str, commit_hash: str) -> str:
        result = subprocess.run(
            ["git", "update-ref", ref, commit_hash],
            capture_output=True, text=True,
            cwd=self.workspace,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git update-ref error: {result.stderr.strip()}")
        return result.stdout.strip()

    def read_tree(self, ref: str, path: str) -> str:
        return self._run("cat", "-r", ref, path)

    def ls_tree(self, ref: str) -> str:
        result = subprocess.run(
            ["git", "ls-tree", "-r", ref],
            capture_output=True, text=True,
            cwd=self.workspace,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git ls-tree error: {result.stderr.strip()}")
        return result.stdout.strip()

    def ls_remote(self, remote: str, ref: str) -> str:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", remote, ref],
            capture_output=True, text=True,
            cwd=self.workspace,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git ls-remote error: {result.stderr.strip()}")
        return result.stdout.strip()

    # ── cleanup ───────────────────────────────────────────────

    def cleanup(self):
        pass
