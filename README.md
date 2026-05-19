# version-controller

A reusable infrastructure layer for managing execution snapshots, rollback, execution chains, task history, feedback tracking, and SCM abstraction (Git/Sapling) for multi-agent AI systems.



## System dependencies

These must be installed on your system before using `vc`.

| Dependency | Required | Check | Install |
|---|---|---|---|
| Python 3.10+ | Yes | `python --version` | [python.org](https://python.org/downloads/) |
| Git | Yes | `git --version` | [git-scm.com](https://git-scm.com/downloads) |
| Sapling (sl) | No | `sl --version` | [sapling-scm.com](https://sapling-scm.com/) |

### Installing Sapling (optional — enables undo/redo/hide)

```bash
# Linux / macOS
curl -LsSf https://sapling-scm.com/install.sh | sh

# Windows (PowerShell)
winget install Sapling.Sapling
```

### Verify everything is ready

```bash
git --version
python --version
sl --version   # optional
```

## Installation

```bash
pip install git+https://github.com/hi-it-isDebayan/version_controller.git
```

If you get a PEP 668 error on Ubuntu/Debian:

```bash
pip install git+https://github.com/hi-it-isDebayan/version_controller.git --break-system-packages
```

### Windows (cmd / PowerShell)

If `pip` gives you "Unable to create process" or "not found", use `python -m pip` instead:

```powershell
python -m pip install git+https://github.com/hi-it-isDebayan/version_controller.git
```

This bypasses the broken `pip.exe` launcher and runs pip via Python directly.

After install, verify:

```bash
python -c "from version_controller import VersionController; print('ready')"
```

### Editable install (for development)

```bash
git clone https://github.com/hi-it-isDebayan/version_controller.git
cd version_controller
pip install -e .
```

Edits to the source files take effect immediately — no reinstall needed.

## CLI

All features are also available via the `vc` command-line tool:

```bash
vc start "Build login"
vc track login.py
vc save "Create login"
vc log
```

See the full reference: [CLI.md](CLI.md)

## Quick start

```python
from version_controller import VersionController

# Initialize with a project workspace (default backend is "git")
vc = VersionController(workspace="./my-project", backend="git")

# Start a task
vc.start_task("Implement feature X")

# Track a file and save a snapshot
vc.track("src/feature.py")
snapshot = vc.save(metadata={
    "agent": "coder",
    "action": "implement",
    "files": ["src/feature.py"],
})
print(f"Saved snapshot: {snapshot['commit_id'][:12]} (version {snapshot['version_index']})")

# Add feedback between iterations
vc.update(feedback="Add error handling for edge case")

# View history
history = vc.history()

# Rollback to a previous version
vc.rollback(version_index=0)

# Sync metadata to vc-data branch (requires a Git remote)
vc.sync("Progress update")

# undo/redo/hide/unhide auto-fallback to Sapling if available
# (no need to reconfigure — just install `sl` and it works)
vc.undo()
vc.hide("abc1234")
```

## Capabilities

| Operation | Method | Git | Sapling |
|---|---|---|---|
| Track files | `track()` | ✓ | ✓ |
| Save snapshot | `save()` | ✓ | ✓ |
| Rollback | `rollback()` | ✓ | ✓ |
| History & context | `history()`, `reconstruct_context()` | ✓ | ✓ |
| Feedback loop | `update()` | ✓ | ✓ |
| TOON export | `export_toon()` | ✓ | ✓ |
| Diff between versions | `diff()` | ✓ | ✓ |
| Amend last commit | `amend()` | ✓ | ✓ |
| Shelve/unshelve work | `shelve()`, `unshelve()` | ✓ | ✓ |
| Prev/next navigation | `prev()`, `next()` | ✓ | ✓ |
| Push/pull | `push()`, `pull()` | ✓ | ✓ |
| Sync metadata branch | `sync()`, `restore()` | ✓ | ✓ |
| Undo/redo | `undo()`, `redo()` | — (auto-fallback ✓) | ✓ |
| Hide/unhide commits | `hide()`, `unhide()` | — (auto-fallback ✓) | ✓ |

### Auto-fallback to Sapling

Operations that Git cannot natively do (`undo`, `redo`, `hide`, `unhide`) use the
**installed `sl` CLI automatically** when the Git backend is active. No
reconfiguration needed.

```
Git backend  ──→ undo() → NotImplementedError ──→ detects sl on PATH ──→ runs sl undo
```

If Sapling is not installed, a clear error tells you how to install it. See
[Installing Sapling](#installing-sapling-optional--enables-undoredohide).

## Workspace structure

When you create a `VersionController(workspace="/path/to/project")`, the module creates:

```
/path/to/project/
├── .version_controller/
│   ├── csv/                    ← metadata stored as CSV files
│   │   ├── tasks.csv
│   │   ├── commit_map.csv
│   │   ├── execution_log_T*.csv
│   │   ├── feedback_T*.csv
│   │   └── .csv_lock           ← file lock for multi-agent safety
│   └── chains/                 ← execution chain files
│       └── T*.chain
├── (your source files)
└── .git/                       ← or .sl/ for Sapling
```

## Multi-agent safety

- **Per-task file isolation**: Each agent writes to its own `execution_log_{task_id}.csv`
- **File-level locking**: `fcntl` locks on `.csv_lock` — exclusive for writes, shared for reads
- **Workspace sandbox**: All metadata stays within `.version_controller/` under the workspace

## Using Git / Sapling directly

`vc` is a high-level layer for task tracking and metadata. It doesn't replace Git
or Sapling — it wraps them. For anything `vc` doesn't cover, use the underlying
tool directly:

```bash
# Git — works in any vc workspace
git log --oneline --graph
git rebase -i HEAD~3
git branch feature-x

# Sapling — works if using sl backend
sl log -r "draft()"
sl split -r .
sl fold -r "draft()"
```

The `.version_controller/` directory is in `.gitignore` — raw Git/Sapling
operations won't touch metadata. The `vc-data` branch is separate from source
branches. No interference.

### Concrete examples

Use `sl` (or `git`) to inspect the same commits that `vc` manages:

```bash
# After vc save, inspect the commit
vc save "Added login"        # output: a1b2c3d4e5f6 0
git show a1b2c3d4e5f6       # see full diff
git log --oneline -5        # see recent vc commits

# With Sapling backend:
sl log -r "draft()"
sl diff -r .~2 -r .
sl show --stat a1b2c3d4e5f6
```

The commit messages follow the pattern `VC:T00001|action`, so you can filter:

```bash
sl log -r "draft()" --line-range "re:VC:"
```

## License

MIT
