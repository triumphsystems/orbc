import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.db.orm import Automation
from core.db.session import SessionLocal

logger = logging.getLogger("core.scheduler")


class SchedulerService:
    """Background scheduler that automatically queries and executes recurring automations."""

    scheduler: AsyncIOScheduler
    _orchestrator: Any
    _is_running: bool

    def __init__(self, orchestrator: Any = None):
        self.scheduler = AsyncIOScheduler()
        self._orchestrator = orchestrator
        self._is_running = False

    @property
    def orchestrator(self) -> Any:
        if self._orchestrator is None:
            from core.agent.orchestrator import AgentOrchestrator

            self._orchestrator = AgentOrchestrator()
        return self._orchestrator

    def start(self, check_interval_seconds: int = 30):
        """Starts the scheduler background loop if not already running."""
        if not self._is_running:
            # Poll database for due automations
            self.scheduler.add_job(
                self._check_and_trigger_due_automations,
                trigger=IntervalTrigger(seconds=check_interval_seconds),
                id="check_due_automations",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=check_interval_seconds * 2,
            )
            self.scheduler.start()
            self._is_running = True
            logger.info(f"Scheduler service daemon successfully started (polling every {check_interval_seconds}s).")

    def shutdown(self):
        """Gracefully shuts down the scheduler background loop."""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler service daemon shut down.")

    async def _check_and_trigger_due_automations(self):
        """Finds all active automations where next_run_at <= now and triggers execution."""
        from core.scheduler.lock import LockFactory

        lock = LockFactory.get_lock()
        # Acquire leader election lock for this tick (auto-releases in 25 seconds)
        acquired = await lock.acquire("scheduler:tick", timeout_seconds=25)
        if not acquired:
            logger.debug("Scheduler tick lock held by another worker instance. Skipping tick.")
            return

        db = SessionLocal()
        try:
            now_utc = datetime.now(timezone.utc)
            due_automations = (
                db.query(Automation)
                .filter(
                    Automation.active.is_(True),
                    Automation.next_run_at.isnot(None),
                    Automation.next_run_at <= now_utc,
                )
                .all()
            )

            if due_automations:
                logger.info(f"Found {len(due_automations)} due automation(s) to execute.")

            for auto in due_automations:
                try:
                    logger.info(f"Triggering scheduled execution for automation {auto.id}...")
                    # Advance or clear next_run_at in DB immediately to prevent duplicate triggers on next tick
                    auto.next_run_at = None
                    db.commit()
                    # Execute asynchronously
                    asyncio.create_task(self._run_single_automation(auto.id))
                except Exception as e:
                    logger.error(f"Failed to launch task for automation {auto.id}: {e}")

        except Exception as e:
            logger.error(f"Error querying due automations: {e}")
        finally:
            db.close()
            await lock.release("scheduler:tick")

    async def _run_single_automation(self, automation_id: str):
        db = SessionLocal()
        try:
            auto = db.query(Automation).filter(Automation.id == automation_id).first()
            if auto:
                await self.orchestrator.execute_run(db, auto)

        except Exception as e:
            logger.error(f"Execution error for scheduled automation {automation_id}: {e}")
        finally:
            db.close()


# Default singleton instance
scheduler_service = SchedulerService()
