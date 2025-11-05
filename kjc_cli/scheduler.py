import signal
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from kjc_cli import config
from kjc_cli.logger import get_logger

logger = get_logger("scheduler")

class Scheduler:
    def __init__(self, job_func):
        """Accepts a callable (like run_pipeline) to execute on schedule"""
        self.job_func = job_func
        self.scheduler = BackgroundScheduler()

        # Parse cron string (minute hour day month dow)
        cron_parts = config.SCHEDULE_CRON.strip().split()
        if len(cron_parts) == 5:
            minute, hour, dom, month, dow = cron_parts
            trigger = CronTrigger(minute=minute, hour=hour, day=dom, month=month, day_of_week=dow)
        else:
            trigger = CronTrigger(minute="0")  # default: hourly

        self.scheduler.add_job(self._job_wrapper, trigger=trigger, id="kjc_full_run")

    def _job_wrapper(self):
        logger.info("Scheduled job started")
        try:
            self.job_func()
            logger.info("Scheduled job finished")
        except Exception:
            logger.exception("Scheduled job failed")

    def start(self):
        self.scheduler.start()

    def wait_forever(self):
        def _handle(sig, frame):
            logger.info("Shutting down scheduler gracefully...")
            self.scheduler.shutdown(wait=False)
            raise SystemExit(0)
        signal.signal(signal.SIGINT, _handle)
        signal.signal(signal.SIGTERM, _handle)
        while True:
            time.sleep(1)
