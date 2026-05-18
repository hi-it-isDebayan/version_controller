import os
import shutil
from ..utils.file_ops import ensure_dir, path_within_workspace, set_workspace_root


class WorkspaceManager:
    def __init__(self, workspace: str):
        self.root = os.path.abspath(workspace)
        set_workspace_root(self.root)
        self._ensure_workspace()

    def _ensure_workspace(self):
        ensure_dir(self.root)
        ensure_dir(os.path.join(self.root, ".version_controller"))
        ensure_dir(os.path.join(self.root, ".version_controller", "toon"))
        ensure_dir(os.path.join(self.root, ".version_controller", "metadata"))
        ensure_dir(os.path.join(self.root, ".version_controller", "cache"))
        ensure_dir(os.path.join(self.root, ".version_controller", "chains"))

    def resolve(self, *paths: str) -> str:
        full = os.path.join(self.root, *paths)
        return path_within_workspace(full)

    def exists(self, path: str) -> bool:
        return os.path.exists(self.resolve(path))

    def list_files(self, subdir: str = "") -> list:
        target = self.resolve(subdir) if subdir else self.root
        if not os.path.isdir(target):
            return []
        result = []
        for root, dirs, files in os.walk(target):
            rel = os.path.relpath(root, self.root)
            for f in files:
                fpath = os.path.join(rel, f) if rel != "." else f
                result.append(fpath)
        return sorted(result)

    def safe_cleanup(self):
        vc_dir = os.path.join(self.root, ".version_controller")
        if os.path.isdir(vc_dir):
            shutil.rmtree(vc_dir)

    def get_root(self) -> str:
        return self.root
