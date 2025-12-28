from __future__ import annotations

import logging
import time
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler


def run_scheduler(job: Callable[[], None], interval_minutes: int = 15) -> None:
    scheduler = BackgroundScheduler()
    scheduler.add_job(job, "interval", minutes=interval_minutes, max_instances=1)
    scheduler.start()
    logging.info("Scheduler started with %s minute interval", interval_minutes)

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler shutdown requested.")
        scheduler.shutdown()
