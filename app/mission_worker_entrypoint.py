"""Supervised process entrypoint for the dedicated durable mission queue."""
from __future__ import annotations

import logging
import os
import signal
import socket
import time

from app.agents.ict_mentor import ICTMentorHandler
from app.services.knowledge_store import KnowledgeStoreAdapter
from app.services.mission_run_repository import MissionRunRepository
from app.services.mission_run_worker import MissionRunWorker
from app.services.model_router import ModelRouter
from app.services.registry import AgentRegistry
from app.storage import store

LOGGER = logging.getLogger("nexus.mission-worker")


def run() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    model_router = ModelRouter.from_env()
    if model_router.select("worker") is None:
        raise SystemExit(
            "Mission worker startup blocked: configure MODEL_BASE_URL, MODEL_NAME and MODEL_API_KEY."
        )

    poll_seconds = int(os.getenv("NEXUS_MISSION_WORKER_POLL_SECONDS", "2"))
    lease_seconds = int(os.getenv("NEXUS_MISSION_WORKER_LEASE_SECONDS", "600"))
    if not 1 <= poll_seconds <= 60 or not 361 <= lease_seconds <= 3600:
        raise SystemExit("Mission worker poll/lease configuration is outside its permitted range.")

    registry = AgentRegistry()
    knowledge_store = KnowledgeStoreAdapter(store)
    handlers = {
        "ict_mentor": ICTMentorHandler(model_router, knowledge_store),
    }
    worker = MissionRunWorker(
        repository=MissionRunRepository(store),
        registry=registry,
        handlers=handlers,
        storage=store,
        worker_id=os.getenv("NEXUS_MISSION_WORKER_ID", socket.gethostname())[:128],
        lease_seconds=lease_seconds,
    )

    stopping = False

    def request_stop(signum, frame):
        nonlocal stopping
        stopping = True
        LOGGER.info("Shutdown requested; current mission lease will expire for safe recovery.")

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    LOGGER.info("Dedicated mission worker started.")
    try:
        while not stopping:
            try:
                claimed = worker.run_once()
            except Exception:
                LOGGER.exception("Mission worker loop failed; retrying.")
                claimed = False
            if not claimed and not stopping:
                time.sleep(poll_seconds)
    finally:
        store.close()
        LOGGER.info("Dedicated mission worker stopped.")


if __name__ == "__main__":
    run()
