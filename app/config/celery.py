import os

from celery import Celery, shared_task
from celery.signals import setup_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("proj")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.worker_prefetch_multiplier = 1
app.conf.broker_transport_options = {
    "priority_steps": list(range(10)),
    "sep": ":",
    "queue_order_strategy": "priority",
}


@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


app.autodiscover_tasks()


# @app.task(priority=0) == @app.task()
@app.task()
def critical_task():
    from time import sleep

    sleep(5)


@app.task(priority=4)
def regular_task():
    from time import sleep

    sleep(5)


@app.task(priority=4)
def regular_maybe_important_task():
    from time import sleep

    sleep(5)


@app.task(priority=9)
def not_so_important_task():
    from time import sleep

    sleep(5)


@shared_task(bind=True)
def priority_test_tasks(self, count=30):
    for i in range(0, count):
        not_so_important_task.delay()
        regular_task.delay()
        critical_task.delay()


@app.task(bind=True)
def debug_task(self):
    print(f"debug_task: Request: {self.request!r}")
    return True
