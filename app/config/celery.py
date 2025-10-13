import os

from celery import Celery, shared_task
from celery.signals import import_modules, setup_logging
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


@import_modules.connect
def import_modules_handler(*args, **kwargs):
    print("import_modules")
    print(args)
    print(kwargs)


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig

    # from django.conf import settings

    dictConfig(settings.LOGGING)


app.autodiscover_tasks()


# app.task_routes = {task: settings.TASK_LOW_PRIORITY_QUEUE for task in tasks}
# app.task_routes.update(
#     {
#         task: settings.TASK_DEFAULT_PRIORITY_QUEUE
#         for task in settings.DEFAULT_PRIORITY_TASKS
#     }
# )
# app.task_routes.update(
#     {task: settings.TASK_HIGH_PRIORITY_QUEUE for task in settings.HIGH_PRIORITY_TASKS}
# )
# app.task_routes.update(
#     {
#         task: settings.TASK_HIGHEST_PRIORITY_QUEUE
#         for task in settings.HIGHEST_PRIORITY_TASKS
#     }
# )


# app.conf.task_routes = {
#     task: {
#         "queue": settings.TASK_HIGH_PRIORITY_QUEUE,
#         "priority": 3,
#     }
#     for tasks in (registered_tasks if registered_tasks else [])
#     for task in tasks
# }


@app.task()
def critical_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task()
def urgent_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task()
def regular_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task()
def regular_maybe_important_task(sleep=5):
    import time

    time.sleep(sleep)


@app.task()
def not_so_important_task(sleep=5):
    import time

    time.sleep(sleep)


@shared_task(bind=True)
def test_mixed_priority_tasks(self, count=20, sleep=5):
    for i in range(0, count):
        not_so_important_task.delay(sleep=sleep)
        regular_task.delay(sleep=sleep)
        urgent_task.delay(sleep=sleep)
        critical_task.delay(sleep=sleep)


@shared_task(bind=True)
def test_low_priority_tasks(self, count=100, sleep=5):
    for i in range(0, count):
        not_so_important_task.delay(sleep=sleep)


@shared_task(bind=True)
def test_highest_priority_tasks(self, count=100, sleep=5):
    for i in range(0, count):
        critical_task.delay(sleep=sleep)


@shared_task(bind=True)
def test_high_priority_tasks(self, count=100, sleep=5):
    for i in range(0, count):
        urgent_task.delay(sleep=sleep)


@app.task(bind=True)
def debug_task(self):
    print(f"debug_task: Request: {self.request!r}")
    return True
