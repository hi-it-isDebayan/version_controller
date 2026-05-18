# version-controller

A reusable infrastructure layer for managing execution snapshots, rollback, execution chains, task history, feedback tracking, and SCM abstraction (Git/Sapling) for multi-agent AI systems.



## Requirements

Before installing, ensure your system has:

| Requirement | Minimum | Notes |
|---|---|---|
| Python | 3.10+ | Tested on 3.10–3.13 |
| pip | Latest | Comes with Python 3.10+ |
| Git | Any version | Required for metadata sync |
| **OS** | Linux / macOS / Windows | Works on all three via WSL, native terminal, or PowerShell |

**Optional (for Sapling backend):** Install [Sapling (sl)](https://sapling-scm.com/) for undo/redo/hide features.

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
python3 -c "from version_controller import VersionController; print('ready')"
```

### Editable install (for development)

```bash
git clone https://github.com/hi-it-isDebayan/version_controller.git
cd version_controller
pip install -e .
```

Edits to the source files take effect immediately — no reinstall needed.

## Quick start

```python
from version_controller import VersionController

# Initialize with a project workspace
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
| Undo/redo | `undo()`, `redo()` | — | ✓ |
| Hide/unhide commits | `hide()`, `unhide()` | — | ✓ |

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

## License

MIT
