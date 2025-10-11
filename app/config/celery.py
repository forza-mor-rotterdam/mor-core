import os

from celery import Celery, shared_task
from celery.signals import setup_logging
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("proj")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.worker_prefetch_multiplier = 1
# app.conf.broker_transport_options = {
#     "priority_steps": list(range(10)),
#     "sep": ":",
#     "queue_order_strategy": "priority",
# }


@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig

    # from django.conf import settings

    dictConfig(settings.LOGGING)


app.autodiscover_tasks()

celery_inspect = app.control.inspect()
registered_tasks = celery_inspect.registered_tasks()
tasks = list(
    set(
        task
        for tasks_list in (registered_tasks.values() if registered_tasks else [])
        for task in tasks_list
    )
)

app.task_routes = {task: settings.TASK_LOW_PRIORITY_QUEUE for task in tasks}
app.task_routes.update(
    {
        task: settings.TASK_DEFAULT_PRIORITY_QUEUE
        for task in settings.DEFAULT_PRIORITY_TASKS
    }
)
app.task_routes.update(
    {task: settings.TASK_HIGH_PRIORITY_QUEUE for task in settings.HIGH_PRIORITY_TASKS}
)
app.task_routes.update(
    {
        task: settings.TASK_HIGHEST_PRIORITY_QUEUE
        for task in settings.HIGHEST_PRIORITY_TASKS
    }
)


@app.task()
def critical_task():
    from time import sleep

    sleep(4)


@app.task()
def urgent_task():
    from time import sleep

    sleep(4)


@app.task()
def regular_task():
    from time import sleep

    sleep(4)


@app.task()
def regular_maybe_important_task():
    from time import sleep

    sleep(4)


@app.task()
def not_so_important_task():
    from time import sleep

    sleep(5)


@shared_task(bind=True)
def priority_test_tasks(self, count=20):
    for i in range(0, count):
        not_so_important_task.delay()
        regular_task.delay()
        urgent_task.delay()
        critical_task.delay()


@app.task(bind=True)
def debug_task(self):
    print(f"debug_task: Request: {self.request!r}")
    return True
