import logging
import os

from celery import Celery
from celery.signals import setup_logging

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("proj")
app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig

    from django.conf import settings

    dictConfig(settings.LOGGING)


app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    from resource import RUSAGE_SELF, getrusage

    logger.info(f"Mem RUSAGE_SELF ru_maxrss: {getrusage(RUSAGE_SELF).ru_maxrss}KB")
    print(f"debug_task: Request: {self.request!r}")
    return True
