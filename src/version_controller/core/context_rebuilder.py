class ContextRebuilder:
    def __init__(self, backend, csv_logger, execution_chain):
        self.backend = backend
        self.csv_logger = csv_logger
        self.execution_chain = execution_chain

    def rebuild(self, task_id: str, depth: int = 5) -> dict:
        task = self.csv_logger.get_task(task_id)
        chain = self.execution_chain.get_chain(task_id)
        history = self.csv_logger.get_history(task_id)
        feedback = self.csv_logger.get_feedback_chain(task_id)

        if not task and not chain:
            return {"task_id": task_id, "status": "not_found"}

        context = {
            "task_id": task_id,
            "description": (task or {}).get("description", ""),
            "status": (task or {}).get("status", "unknown"),
            "version_count": int((task or {}).get("version_count", 0)),
            "feedback_count": int((task or {}).get("feedback_count", 0)),
            "current_commit": (chain or {}).get("current"),
            "recent_versions": history[-depth:] if history else [],
            "feedback": feedback[-depth:] if feedback else [],
        }
        return context

    def export_context_summary(self, task_id: str, depth: int = 3) -> str:
        context = self.rebuild(task_id, depth)
        if context.get("status") == "not_found":
            return f"task: {task_id} status: not_found"

        parts = [
            f"task: {task_id}",
            f"versions: {context['version_count']}",
            f"current: {(context['current_commit'] or 'none')[:8]}",
        ]
        return " | ".join(parts)
