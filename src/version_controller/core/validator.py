import os
import subprocess
import shutil


class Validator:
    def __init__(self, workspace: str):
        self.workspace = workspace

    def validate(self) -> tuple:
        issues = []
        issues.extend(self._check_syntax())
        issues.extend(self._check_lint())
        issues.extend(self._check_lightweight_tests())
        valid = len(issues) == 0
        return valid, issues

    def _tool_exists(self, name: str) -> bool:
        return shutil.which(name) is not None

    def _check_syntax(self) -> list:
        issues = []
        for root, dirs, files in os.walk(self.workspace):
            for f in files:
                fpath = os.path.join(root, f)
                if f.endswith(".py"):
                    if not self._tool_exists("python3"):
                        continue
                    result = subprocess.run(
                        ["python3", "-m", "py_compile", fpath],
                        capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        issues.append(f"Syntax error in {f}: {result.stderr.strip()}")
                elif f.endswith(".js") or f.endswith(".ts") or f.endswith(".tsx"):
                    if not self._tool_exists("node"):
                        continue
                    result = subprocess.run(
                        ["node", "--check", fpath],
                        capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        issues.append(f"Syntax error in {f}: {result.stderr.strip()}")
                elif f.endswith(".json"):
                    try:
                        import json
                        with open(fpath) as fh:
                            json.load(fh)
                    except json.JSONDecodeError as e:
                        issues.append(f"JSON error in {f}: {e}")
        return issues

    def _check_lint(self) -> list:
        if not self._tool_exists("python3"):
            return []
        issues = []
        py_files = []
        for root, dirs, files in os.walk(self.workspace):
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))
        if py_files:
            result = subprocess.run(
                ["python3", "-m", "pyflakes"] + py_files,
                capture_output=True, text=True
            )
            if result.returncode != 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        issues.append(f"Lint: {line.strip()}")
        return issues

    def _check_lightweight_tests(self) -> list:
        if not self._tool_exists("python3"):
            return []
        issues = []
        test_dir = os.path.join(self.workspace, "tests")
        if os.path.isdir(test_dir):
            result = subprocess.run(
                ["python3", "-m", "pytest", test_dir, "--tb=short", "-q"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                issues.append(f"Tests failed: {result.stdout.strip()[-200:]}")
        return issues
