import os
import subprocess

BRANCH_NAME = "vc-data"


def _run_git(workspace: str, *args: str, input_str: str = None) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True,
        cwd=workspace, input=input_str,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git error: {result.stderr.strip()}")
    return result.stdout.strip()


class MetadataBranch:
    def __init__(self, workspace: str):
        self.workspace = workspace

    def _git(self, *args: str, input_str: str = None) -> str:
        return _run_git(self.workspace, *args, input_str=input_str)

    def branch_exists_locally(self) -> bool:
        try:
            self._git("rev-parse", "--verify", f"refs/heads/{BRANCH_NAME}")
            return True
        except RuntimeError:
            return False

    def has_remote(self) -> bool:
        try:
            output = self._git("remote", "-v")
            return bool(output.strip())
        except RuntimeError:
            return False

    def sync(self, csv_files: list, message: str = None) -> dict:
        msg = message or "VC: sync metadata"
        result = {"branch": BRANCH_NAME, "committed": False, "pushed": False}

        vc_dir = os.path.join(self.workspace, ".version_controller")

        # Use a temporary index to build the tree
        self._git("read-tree", "--empty")
        any_files = False
        for fpath in csv_files:
            if not os.path.isfile(fpath):
                continue
            rel = os.path.relpath(fpath, vc_dir)
            with open(fpath, "r") as f:
                content = f.read()
            blob_hash = self._git("hash-object", "-w", "--stdin", input_str=content)
            self._git(
                "update-index", "--add", "--replace", "--cacheinfo",
                "100644", blob_hash, rel,
            )
            any_files = True

        if not any_files:
            return result

        tree_hash = self._git("write-tree")

        parent = None
        if self.branch_exists_locally():
            parent = self._git("rev-parse", f"refs/heads/{BRANCH_NAME}")

        if parent:
            commit_hash = self._git(
                "commit-tree", tree_hash, "-p", parent, "-m", msg,
            )
        else:
            commit_hash = self._git("commit-tree", tree_hash, "-m", msg)

        self._git("update-ref", f"refs/heads/{BRANCH_NAME}", commit_hash)
        result["commit"] = commit_hash
        result["committed"] = True

        # Reset index to avoid polluting main branch state
        try:
            self._git("read-tree", "--empty")
        except RuntimeError:
            pass

        if self.has_remote():
            try:
                self._git("push", "origin", BRANCH_NAME)
                result["pushed"] = True
            except RuntimeError as e:
                result["push_error"] = str(e)

        return result

    def restore(self) -> dict:
        if not self.branch_exists_locally():
            if self.has_remote():
                try:
                    self._git("fetch", "origin", f"{BRANCH_NAME}:{BRANCH_NAME}")
                except RuntimeError:
                    return {"restored": False, "reason": "remote branch not found"}
            else:
                return {"restored": False, "reason": "no local or remote branch"}

        try:
            tree_hash = self._git("rev-parse", f"{BRANCH_NAME}^{{tree}}")
        except RuntimeError:
            return {"restored": False, "reason": "no tree at branch tip"}

        output = self._git("ls-tree", "-r", tree_hash)
        restored = 0
        vc_dir = os.path.join(self.workspace, ".version_controller")
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                rel_path = parts[1]
                content = self._git("show", f"{BRANCH_NAME}:{rel_path}")
                full_path = os.path.join(vc_dir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                tmp_path = full_path + ".tmp"
                with open(tmp_path, "w") as f:
                    f.write(content)
                os.rename(tmp_path, full_path)
                restored += 1

        return {"restored": True, "file_count": restored}
