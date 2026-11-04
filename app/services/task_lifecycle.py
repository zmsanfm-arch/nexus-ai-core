from __future__ import annotations

import uuid
from threading import Event, Thread
from datetime import datetime, timezone
from typing import Callable


class TaskQueueService:
    """Durable enqueue/lease lifecycle; worker execution is injected by the host."""

    def __init__(self, storage):
        self.storage = storage

    def enqueue(self, objective: str, task_type: str | None = None,
                context: dict | None = None, principal_id: str = "system"):
        if not isinstance(objective, str) or not 5 <= len(objective) <= 4000:
            raise ValueError("Objective must contain 5 to 4000 characters.")
        if not principal_id or len(principal_id) > 128:
            raise ValueError("A bounded principal identity is required.")
        task = {
            "id": str(uuid.uuid4()),
            "objective": objective,
            "task_type": task_type,
            "context": context or {},
            "status": "queued",
            "assigned_agent": None,
            "risk_level": "unclassified",
            "result": None,
            "principal_id": principal_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.storage.enqueue_task(task)
        self.storage.append_audit({
            "event": "task_enqueued",
            "task_id": task["id"],
            "principal_id": principal_id,
            "task_type": task_type,
        })
        return task


class TaskWorker:
    """Single-claim worker with expiring leases, bounded retries and audit events."""

    def __init__(self, storage, worker_id: str,
                 handler: Callable[[dict], dict], lease_seconds: int = 60,
                 max_attempts: int = 3, retry_delay_seconds: int = 30):
        if not worker_id or len(worker_id) > 128:
            raise ValueError("Invalid worker identity.")
        if lease_seconds < 1 or max_attempts < 1 or retry_delay_seconds < 0:
            raise ValueError("Invalid worker lifecycle configuration.")
        self.storage = storage
        self.worker_id = worker_id
        self.handler = handler
        self.lease_seconds = lease_seconds
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds

    def run_once(self) -> bool:
        lease = self.storage.claim_next_task(self.worker_id, self.lease_seconds)
        if lease is None:
            return False
        task_id = lease["task_id"]
        task = self.storage.get_task(task_id)
        if task is None:
            self.storage.fail_queued_task(
                task_id, self.worker_id, "Task record missing",
                max_attempts=self.max_attempts,
                retry_delay_seconds=self.retry_delay_seconds,
            )
            return True
        self.storage.append_audit({
            "event": "task_worker_started",
            "task_id": task_id,
            "worker_id": self.worker_id,
            "attempt": lease["attempts"],
        })
        heartbeat_stop = Event()
        lease_lost = Event()
        heartbeat_interval = max(0.1, min(30.0, self.lease_seconds / 3.0))

        def maintain_lease():
            while not heartbeat_stop.wait(heartbeat_interval):
                try:
                    renewed = self.storage.renew_queued_task_lease(
                        task_id, self.worker_id, self.lease_seconds
                    )
                except Exception:
                    lease_lost.set()
                    return
                if not renewed:
                    lease_lost.set()
                    return

        heartbeat = Thread(
            target=maintain_lease,
            name=f"nexus-lease-{task_id[:8]}",
            daemon=True,
        )
        heartbeat.start()
        try:
            result = self.handler(task)
            if not isinstance(result, dict):
                raise TypeError("Task handler must return a dictionary.")
            if lease_lost.is_set():
                self.storage.append_audit({
                    "event": "task_worker_lease_lost",
                    "task_id": task_id,
                    "worker_id": self.worker_id,
                })
                return True
            task["result"] = result
            # Queue execution can complete while the business task remains blocked
            # by the independent auditor gate.
            audit_verdict = result.get("audit_verdict")
            task["status"] = "completed" if audit_verdict == "pass" else "blocked"
            task["completed_at"] = datetime.now(timezone.utc).isoformat()
            self.storage.save_task(task)
            self.storage.complete_queued_task(task_id, self.worker_id)
            self.storage.append_audit({
                "event": "task_worker_completed",
                "task_id": task_id,
                "worker_id": self.worker_id,
                "task_status": task["status"],
                "audit_verdict": audit_verdict,
            })
        except Exception as exc:
            if lease_lost.is_set():
                self.storage.append_audit({
                    "event": "task_worker_lease_lost",
                    "task_id": task_id,
                    "worker_id": self.worker_id,
                    "error_type": type(exc).__name__,
                })
                return True
            queue_status = self.storage.fail_queued_task(
                task_id, self.worker_id, type(exc).__name__,
                max_attempts=self.max_attempts,
                retry_delay_seconds=self.retry_delay_seconds,
            )
            task["status"] = "failed" if queue_status == "dead" else "queued"
            task["result"] = "Task execution failed; see audit event."
            self.storage.save_task(task)
            self.storage.append_audit({
                "event": "task_worker_failed",
                "task_id": task_id,
                "worker_id": self.worker_id,
                "error_type": type(exc).__name__,
                "queue_status": queue_status,
            })
        finally:
            heartbeat_stop.set()
            heartbeat.join(timeout=max(1.0, heartbeat_interval + 1.0))
        return True
