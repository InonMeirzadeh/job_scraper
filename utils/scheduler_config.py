import schedule
import time
import logging


def configure_scheduler(task_function, interval_minutes):
    """
    Configures the scheduler to run a given task at regular intervals.
    """
    task_function()
    schedule.every(interval_minutes).minutes.do(task_function)

    while True:
        schedule.run_pending()
        time.sleep(1)
