#!/usr/bin/env python3
import typer
from kjc_cli import config as cfg
from kjc_cli.logger import get_logger
from kjc_cli.scheduler import Scheduler
from kjc_cli.pipeline import run_pipeline  # 👈 new import

app = typer.Typer()
logger = get_logger("main")

@app.command()
def run_all():
    """Run the full automation pipeline once"""
    run_pipeline()

@app.command()
def schedule():
    """Start the cron-based scheduler"""
    logger.info("Starting scheduler...")
    s = Scheduler(run_pipeline)   # pass function reference
    s.start()
    s.wait_forever()

if __name__ == "__main__":
    app()
