import os
import argparse
from . import __version__


def find_workspace() -> str:
    cwd = os.path.abspath(".")
    if os.path.isdir(os.path.join(cwd, ".version_controller")):
        return cwd
    for parent in [os.path.dirname(cwd)]:
        if os.path.isdir(os.path.join(parent, ".version_controller")):
            return parent
    return cwd


def get_vc():
    from . import VersionController
    vc = VersionController(workspace=find_workspace())
    if not vc._current_task_id:
        tasks = vc.csv_logger.list_tasks()
        active = [t for t in tasks if t.get("status") == "active"]
        if active:
            vc._current_task_id = active[-1]["task_id"]
    return vc


def cmd_start(args):
    vc = get_vc()
    r = vc.start_task(args.description)
    print(r["task_id"], r["status"])


def cmd_track(args):
    vc = get_vc()
    vc.track(args.path)
    print(f"tracked {args.path}")


def cmd_save(args):
    vc = get_vc()
    meta = {"action": args.message} if args.message else {}
    if args.agent:
        meta["agent"] = args.agent
    if args.files:
        meta["files"] = args.files
    r = vc.save(metadata=meta)
    print(r["commit_id"][:12], r["version_index"])


def cmd_log(args):
    vc = get_vc()
    h = vc.history()
    print(f"task={h['task']['task_id']} desc={h['task']['description']}")
    for v in h["versions"]:
        tag = v.get("status", "?")
        c = (v.get("commit_hash") or "?" * 12)[:12]
        a = (v.get("action") or "")[:30]
        print(f"  [{tag:8}] {c}  {a}")
    fb = h.get("feedback", [])
    if fb:
        print(f"feedback: {len(fb)} entries")


def cmd_rollback(args):
    vc = get_vc()
    if args.commit:
        r = vc.rollback(commit_id=args.commit)
    elif args.version is not None:
        r = vc.rollback(version_index=args.version)
    else:
        r = vc.rollback()
    print(r["rolled_back_to"][:12])


def cmd_diff(args):
    vc = get_vc()
    if args.commit_a and args.commit_b:
        r = vc.diff(args.commit_a, args.commit_b)
    elif args.commit_a:
        r = vc.diff(args.commit_a, vc.backend.get_head())
    else:
        head = vc.backend.get_head()
        parents = vc.backend.get_parents(head)
        parent = parents[0] if parents else head
        r = vc.diff(parent, head)
    print(f"files: {len(r.get('affected_files', []))}")
    for s in r.get("summaries", []):
        print(f"  {s}")


def cmd_feedback(args):
    vc = get_vc()
    vc.update(feedback=args.text)
    print("feedback recorded")


def cmd_sync(args):
    vc = get_vc()
    msg = args.message or f"VC: sync {vc.get_current_task_id() or 'metadata'}"
    r = vc.sync(msg)
    print(f"committed={r['committed']} commit={r.get('commit','')[:12]}")


def cmd_restore(args):
    vc = get_vc()
    r = vc.restore()
    print(f"restored={r.get('restored')} files={r.get('file_count', 0)}")


def cmd_push(args):
    vc = get_vc()
    r = vc.push(args.remote, args.branch)
    print(r)


def cmd_pull(args):
    vc = get_vc()
    r = vc.pull(args.remote, args.branch)
    print(r)


def cmd_amend(args):
    vc = get_vc()
    r = vc.amend(args.message)
    print(r[:12])


def cmd_shelve(args):
    vc = get_vc()
    r = vc.shelve(args.name)
    print(r)


def cmd_unshelve(args):
    vc = get_vc()
    if args.name:
        r = vc.unshelve(args.name)
    else:
        r = vc.unshelve()
    print(r)


def cmd_prev(args):
    vc = get_vc()
    r = vc.prev()
    print(r[:12])


def cmd_next(args):
    vc = get_vc()
    r = vc.next()
    print(r[:12])


def cmd_status(args):
    vc = get_vc()
    print(vc.status())


def cmd_undo(args):
    vc = get_vc()
    try:
        r = vc.undo()
        print(r)
    except NotImplementedError as e:
        print(e)


def cmd_redo(args):
    vc = get_vc()
    try:
        r = vc.redo()
        print(r)
    except NotImplementedError as e:
        print(e)


def cmd_hide(args):
    vc = get_vc()
    try:
        r = vc.hide(args.rev)
        print(r)
    except NotImplementedError as e:
        print(e)


def cmd_unhide(args):
    vc = get_vc()
    try:
        r = vc.unhide(args.rev)
        print(r)
    except NotImplementedError as e:
        print(e)


def cmd_tasks(args):
    vc = get_vc()
    tasks = vc.csv_logger.list_tasks()
    if not tasks:
        print("no tasks")
        return
    for t in tasks:
        print(f"{t['task_id']:8} {t['status']:8} {t.get('description','')}")


def cmd_complete(args):
    vc = get_vc()
    tid = args.task_id or vc._current_task_id
    if not tid:
        print("no active task to complete")
        return
    vc.csv_logger.update_task(tid, status="completed")
    if tid == vc._current_task_id:
        vc._current_task_id = None
    print(f"{tid} completed")


def cmd_current(args):
    vc = get_vc()
    tid = vc._current_task_id
    if not tid:
        tasks = vc.csv_logger.list_tasks()
        active = [t for t in tasks if t.get("status") == "active"]
        if active:
            tid = active[-1]["task_id"]
    if tid:
        t = vc.csv_logger.get_task(tid)
        if t:
            print(f"{t['task_id']} {t['status']} {t.get('description','')}")
        else:
            print("no active task")
    else:
        print("no active task")


def cmd_export(args):
    vc = get_vc()
    print(vc.export_toon())


def cmd_context(args):
    vc = get_vc()
    ctx = vc.reconstruct_context(depth=args.depth)
    print(f"versions: {ctx.get('version_count', 0)}")
    print(f"current:  {ctx.get('current_commit', '')[:12]}")


def main():
    parser = argparse.ArgumentParser(prog="vc", description="version-controller CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    EXAMPLES = {
        "start": "  vc start \"Add login feature\"",
        "track": "  vc track src/main.py",
        "log": "  vc log",
        "diff": "  vc diff  |  vc diff abc1234 def5678",
        "feedback": "  vc feedback \"Needs review\"",
        "sync": "  vc sync  |  vc sync \"sync metadata before push\"",
        "tasks": "  vc tasks",
        "current": "  vc current",
        "restore": "  vc restore",
        "push": "  vc push  |  vc push upstream main",
        "pull": "  vc pull  |  vc pull upstream vc-data",
        "amend": "  vc amend \"Updated commit message\"",
        "shelve": "  vc shelve wip-branch",
        "unshelve": "  vc unshelve  |  vc unshelve wip-branch",
        "prev": "  vc prev",
        "next": "  vc next",
        "status": "  vc status",
        "undo": "  vc undo",
        "redo": "  vc redo",
        "hide": "  vc hide abc1234",
        "unhide": "  vc unhide abc1234",
        "export": "  vc export",
        "context": "  vc context  |  vc context --depth 10",
    }

    p = sub.add_parser("start", help="Start a new task", epilog=EXAMPLES["start"])
    p.add_argument("description")
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("track", help="Track a file", epilog=EXAMPLES["track"])
    p.add_argument("path")
    p.set_defaults(func=cmd_track)

    p = sub.add_parser("save", help="Save a snapshot (auto-stages all)", epilog="  vc save  |  vc save \"Implemented auth\"  |  vc save \"Fix\" --agent agent-1")
    p.add_argument("message", nargs="?", default=None)
    p.add_argument("--agent", default=None)
    p.add_argument("--files", nargs="*", default=None)
    p.set_defaults(func=cmd_save)

    p = sub.add_parser("log", aliases=["history"], help="Show task history", epilog=EXAMPLES["log"])
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("rollback", help="Rollback to a version", epilog="  vc rollback  |  vc rollback --version 2  |  vc rollback --commit abc1234")
    p.add_argument("--version", type=int, default=None)
    p.add_argument("--commit", default=None)
    p.set_defaults(func=cmd_rollback)

    p = sub.add_parser("diff", help="Show diff between commits", epilog=EXAMPLES["diff"])
    p.add_argument("commit_a", nargs="?")
    p.add_argument("commit_b", nargs="?")
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("feedback", help="Add feedback", epilog=EXAMPLES["feedback"])
    p.add_argument("text")
    p.set_defaults(func=cmd_feedback)

    p = sub.add_parser("sync", help="Sync metadata to vc-data branch", epilog=EXAMPLES["sync"])
    p.add_argument("message", nargs="?", default=None)
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("tasks", help="List all tasks", epilog=EXAMPLES["tasks"])
    p.set_defaults(func=cmd_tasks)

    p = sub.add_parser("complete", help="Mark a task as completed", epilog="  vc complete  |  vc complete T00001")
    p.add_argument("task_id", nargs="?", default=None)
    p.set_defaults(func=cmd_complete)

    p = sub.add_parser("current", help="Show the current active task", epilog=EXAMPLES["current"])
    p.set_defaults(func=cmd_current)

    p = sub.add_parser("restore", help="Restore metadata from vc-data branch", epilog=EXAMPLES["restore"])
    p.set_defaults(func=cmd_restore)

    p = sub.add_parser("push", help="Git push", epilog=EXAMPLES["push"])
    p.add_argument("remote", nargs="?", default="origin")
    p.add_argument("branch", nargs="?", default=None)
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("pull", help="Git pull", epilog=EXAMPLES["pull"])
    p.add_argument("remote", nargs="?", default="origin")
    p.add_argument("branch", nargs="?", default=None)
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("amend", help="Amend last commit message", epilog=EXAMPLES["amend"])
    p.add_argument("message")
    p.set_defaults(func=cmd_amend)

    p = sub.add_parser("shelve", help="Shelve changes", epilog=EXAMPLES["shelve"])
    p.add_argument("name")
    p.set_defaults(func=cmd_shelve)

    p = sub.add_parser("unshelve", help="Unshelve changes", epilog=EXAMPLES["unshelve"])
    p.add_argument("name", nargs="?")
    p.set_defaults(func=cmd_unshelve)

    p = sub.add_parser("prev", help="Go to parent commit", epilog=EXAMPLES["prev"])
    p.set_defaults(func=cmd_prev)

    p = sub.add_parser("next", help="Go to child commit", epilog=EXAMPLES["next"])
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("status", help="Show working tree status", epilog=EXAMPLES["status"])
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("undo", help="Undo last operation (Sapling only)", epilog=EXAMPLES["undo"])
    p.set_defaults(func=cmd_undo)

    p = sub.add_parser("redo", help="Redo last undo (Sapling only)", epilog=EXAMPLES["redo"])
    p.set_defaults(func=cmd_redo)

    p = sub.add_parser("hide", help="Hide a commit (Sapling only)", epilog=EXAMPLES["hide"])
    p.add_argument("rev")
    p.set_defaults(func=cmd_hide)

    p = sub.add_parser("unhide", help="Unhide a commit (Sapling only)", epilog=EXAMPLES["unhide"])
    p.add_argument("rev")
    p.set_defaults(func=cmd_unhide)

    p = sub.add_parser("export", help="Export TOON output", epilog=EXAMPLES["export"])
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("context", help="Show context summary", epilog=EXAMPLES["context"])
    p.add_argument("--depth", type=int, default=5)
    p.set_defaults(func=cmd_context)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
