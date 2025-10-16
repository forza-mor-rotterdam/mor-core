import logging
import os

from celery import Celery, shared_task
from celery.signals import setup_logging
from django.conf import settings

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("proj")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.worker_prefetch_multiplier = 1


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig

    from django.conf import settings as local_settings

    dictConfig(local_settings.LOGGING)


app.autodiscover_tasks()

queue_name_by_priority = {
    priority: queue_name for queue_name, priority in settings.TASK_QUEUES
}
queues_by_queue_name = {
    queue_name: {
        "queue": queue_name,
        "priority": priority,
    }
    for queue_name, priority in settings.TASK_QUEUES
}
priority_tasks = (
    (settings.TASK_HIGHEST_PRIORITY_QUEUE_NAME, settings.HIGHEST_PRIORITY_TASKS),
    (settings.TASK_HIGH_PRIORITY_QUEUE_NAME, settings.HIGH_PRIORITY_TASKS),
    (settings.TASK_DEFAULT_PRIORITY_QUEUE_NAME, settings.DEFAULT_PRIORITY_TASKS),
    (settings.TASK_LOW_PRIORITY_QUEUE_NAME, settings.LOW_PRIORITY_TASKS),
)


def task_router(name, args, kwargs, options, task=None, **kw):
    queue = (
        queues_by_queue_name.get(options.get("queue").name)
        if options.get("queue")
        else None
    )
    if queue:
        logger.info(f'{name} -> {queue["queue"]}: found by queue')
        return queue
    queue_name = queue_name_by_priority.get(options.get("priority"))
    if queue_name:
        logger.info(f"{name} -> {queue_name}: found by priority")
        return queues_by_queue_name[queue_name]

    queues = [queue_name for queue_name, tasks in priority_tasks if name in tasks]
    if queues:
        logger.info(f"{name} -> {queues[0]}: found by settings")
        return queues_by_queue_name[queues[0]]
    logger.info(f"{name} -> {settings.TASK_LOW_PRIORITY_QUEUE_NAME}: fallback found")
    return queues_by_queue_name[settings.TASK_LOW_PRIORITY_QUEUE_NAME]


@app.task()
def test_critical_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task()
def test_urgent_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task()
def test_regular_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task(queue="highest_priority")
def test_regular_made_important_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task()
def test_not_so_important_task(sleep=5):
    import time

    time.sleep(sleep)


@shared_task(bind=True)
def test_mixed_priority_tasks(self, count=20, sleep=5):
    for i in range(0, count):
        test_not_so_important_task.delay(sleep=sleep)
        test_regular_task.delay(sleep=sleep)
        test_urgent_task.delay(sleep=sleep)
        test_critical_task.delay(sleep=sleep)


@shared_task(bind=True)
def test_mixed_dynamic_priority_tasks(self, count=20, sleep=4):
    for i in range(0, count):
        test_not_so_important_task.delay(sleep=sleep)
        # task made high prio
        test_not_so_important_task.apply_async(
            kwargs={"sleep": 8}, queue="high_priority"
        )
        test_regular_task.delay(sleep=sleep)
        test_critical_task.delay(sleep=sleep)


@shared_task(bind=True)
def test_low_priority_tasks(self, count=100, sleep=5):
    for i in range(0, count):
        test_not_so_important_task.delay(sleep=sleep)


@shared_task(bind=True)
def test_default_priority_tasks(self, count=100, sleep=5, priority=6):
    for i in range(0, count):
        test_regular_task.apply_async(sleep=sleep, priority=priority)


@shared_task(bind=True)
def test_highest_priority_tasks(self, count=100, sleep=5):
    for i in range(0, count):
        test_critical_task.delay(sleep=sleep)


@shared_task(bind=True)
def test_high_priority_tasks(self, count=100, sleep=5):
    for i in range(0, count):
        test_urgent_task.delay(sleep=sleep)


@app.task(bind=True)
def debug_task(self):
    print(f"debug_task: Request: {self.request!r}")
    return True
