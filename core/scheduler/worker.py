import asyncio
import logging
import signal
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_repo_root = str(Path(__file__).resolve().parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from core.config.settings import get_settings
from core.scheduler.service import scheduler_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("core.scheduler.worker")


async def run_worker():
    """Main production loop for the standalone background scheduler daemon worker."""
    settings = get_settings()
    logger.info("🛰️ Initializing Orbit Background Scheduler Daemon Worker...")
    logger.info("Wall-clock timezone awareness enabled across registered automations.")

    # Start APScheduler background loop
    scheduler_service.start(check_interval_seconds=15)

    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received. Stopping scheduler worker gracefully...")
        scheduler_service.shutdown()
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Signal handlers on Windows
            pass

    logger.info("Daemon worker is active and polling for due automations (interval: 15s).")
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        _signal_handler()


def main():
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker process exited.")


if __name__ == "__main__":
    main()
