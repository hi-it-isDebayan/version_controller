# vc CLI Reference

All commands are run with `vc <command> [options]` from inside a project directory.

> `vc` covers the task-tracking workflow. For advanced operations like rebase,
> merge, split, or graft, use `git` or `sl` directly — they work alongside `vc`
> without conflict.

## Task management

### `vc start <description>`

Start a new task. Creates a task entry, a chain file, and sets it as the active task.

```
$ vc start "Build login feature"
T48162 active
```

### `vc tasks`

List all tasks with their status and description.

```
$ vc tasks
T48162   active    Build login feature
T48901   completed Fix logout bug
```

### `vc current`

Show the currently active task.

```
$ vc current
T48162 active Build login feature
```

### `vc complete <task_id>`

Mark a task as completed. The history is preserved but the task is no longer active.

```
$ vc complete T48162
T48162 completed
```

---

## File tracking

### `vc track <path>`

Stage a file for tracking. Equivalent to `git add`.

```
$ vc track src/login.py
tracked src/login.py
```

### `vc untrack <path>`

Stop tracking a file. Equivalent to `git rm --cached`.

```
$ vc untrack src/login.py
untracked src/login.py
```

### `vc status`

Show the working tree status — modified, staged, and untracked files.

```
$ vc status
M  src/login.py
A  src/utils.py
?? note.txt
```

---

## Snapshots

### `vc save <message> [--agent NAME] [--files FILE...]`

Auto-stage all changes, commit, and save a snapshot. The message describes what changed.

```
$ vc save "Create login function"
d85119870b0e 0

$ vc save "Add logout" --agent dev --files login.py utils.py
9bb18e744790 1
```

| Option | Default | Description |
|---|---|---|
| `--agent` | *(none)* | Who made the change |
| `--files` | *(none)* | List of files changed |

### `vc log`

Show the full task history — all events, snapshots, feedback, and rollbacks.

```
$ vc log
task=T48162 desc=Build login feature
  [active  ] ????????????  start
  [snapshot] d85119870b0e  Create login function
  [snapshot] 9bb18e744790  Add logout
  [feedback]               Add validation
  [rollback] d85119870b0e
feedback: 1 entries
```

---

## Review & Compare

### `vc diff [commit_a] [commit_b]`

Show files changed between two commits. If only one commit is given, diffs against HEAD. If none given, diffs parent of HEAD vs HEAD.

```
$ vc diff d851198 9bb18e7
files: 2
  FILE[login.py] +3 -0
  FILE[utils.py] +1 -0

$ vc diff d851198
    (diffs d851198 vs HEAD)

$ vc diff
    (diffs parent of HEAD vs HEAD)
```

### `vc export`

Export the task history in TOON format — a structured text format for LLM consumption.

```
$ vc export
[3]:
  - timestamp: "1779094918"
    action: start
    status: active
  - timestamp: "1779094918"
    commit_hash: d85119870b0e
    action: Create login function
    status: snapshot
  - timestamp: "1779094918"
    commit_hash: 9bb18e744790
    action: Add logout
    status: snapshot
```

### `vc context [--depth N]`

Show a summary of the current context — version count and current commit.

```
$ vc context
versions: 2
current:  d85119870b0e
```

| Option | Default | Description |
|---|---|---|
| `--depth` | 5 | How many versions back to include |

---

## Rollback

### `vc rollback --version <index>`

Rollback to a specific version by index (0 = first snapshot).

```
$ vc rollback --version 0
d85119870b0e
```

After rollback, the working tree reflects that version. CSV metadata is preserved (no data loss).

### `vc rollback --commit <hash>`

Rollback to a specific commit hash.

```
$ vc rollback --commit a1b2c3d4e5f6
a1b2c3d4e5f6
```

---

## Navigation

### `vc prev`

Go to the parent commit (move HEAD backward one step).

```
$ vc prev
d85119870b0e
```

### `vc next`

Go to the child commit (move HEAD forward one step).

```
$ vc next
9bb18e744790
```

---

## Git Operations

### `vc amend <message>`

Replace the last commit's message.

```
$ vc amend "Amended: Create login function"
d85119870b0e
```

### `vc shelve <name>`

Stash changes temporarily under a name.

```
$ vc shelve wip-login
shelved wip-login
```

### `vc unshelve [name]`

Restore shelved changes. If no name given, restores the most recent.

```
$ vc unshelve wip-login
unshelved wip-login
```

### `vc push [remote] [branch]`

Push source commits to a remote. Defaults to `origin` and current branch.

```
$ vc push
Everything up-to-date

$ vc push origin main
```

### `vc pull [remote] [branch]`

Pull source commits from a remote.

```
$ vc pull
Already up to date
```

---

## Metadata Sync

### `vc sync [message]`

Commit CSV metadata to the `vc-data` branch. This is how you save task history alongside your source code.

```
$ vc sync "Checkpoint: login done"
committed=True commit=a1b2c3d4e5f6
```

If a remote is configured, `vc sync` also pushes the `vc-data` branch automatically.

### `vc restore`

Restore CSV metadata from the `vc-data` branch. Use this on a fresh clone to recover task history.

```
$ vc restore
restored=True files=5
```

---

## Feedback

### `vc feedback <text>`

Add feedback to the current task. Used to record review notes between iterations.

```
$ vc feedback "Add input validation"
feedback recorded
```

---

## Sapling-only (not available on Git backend)

These commands work only with `SaplingBackend`. On Git, they print an informational message.

### `vc undo`

Undo the last operation.

### `vc redo`

Redo the last undone operation.

### `vc hide <rev>`

Hide a commit from the visible history.

### `vc unhide <rev>`

Restore a hidden commit.

---

## General

### `vc --help`

Show the full command list.

```
$ vc --help
```

### `vc --version`

Show the installed version.

```
$ vc --version
vc 1.0.0
```
