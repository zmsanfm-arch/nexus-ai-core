from datetime import datetime, timezone
from threading import RLock

class InMemoryStore:
    """Development-only store. Replace with PostgreSQL before multi-instance use."""
    def __init__(self):
        self.tasks = {}
        self.approvals = {}
        self.audit = []
        self._lock = RLock()

    def save_task(self, task):
        with self._lock:
            self.tasks[task["id"]] = task.copy()

    def get_task(self, task_id):
        with self._lock:
            item = self.tasks.get(task_id)
            return item.copy() if item else None

    def save_approval(self, approval):
        with self._lock:
            self.approvals[approval["id"]] = approval.copy()

    def get_approval(self, approval_id):
        with self._lock:
            item = self.approvals.get(approval_id)
            return item.copy() if item else None

    def append_audit(self, event):
        with self._lock:
            self.audit.append({
                **event,
                "recorded_at": datetime.now(timezone.utc).isoformat()
            })

store = InMemoryStore()
