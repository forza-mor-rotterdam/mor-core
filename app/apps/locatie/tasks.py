from celery import Task, shared_task
from celery.utils.log import get_task_logger
from django.db import transaction

logger = get_task_logger(__name__)

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6
RETRY_BACKOFF_MAX = 60 * 30
RETRY_BACKOFF = 120


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY
    retry_backoff_max = RETRY_BACKOFF_MAX
    retry_backoff = RETRY_BACKOFF
    retry_jitter = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def update_locatie_zoek_field_task(self, locatie_ids, batch_size=1000):
    from apps.locatie.models import Locatie

    if locatie_ids is not None:
        queryset = Locatie.objects.filter(id__in=locatie_ids)
    else:
        queryset = Locatie.objects.all()

    total_count = queryset.count()
    processed = 0

    while processed < total_count:
        batch = queryset[processed : processed + batch_size]
        update_batch.delay([loc.id for loc in batch])
        processed += batch_size

    return f"Queued update for {total_count} locations in batches of {batch_size}"


@shared_task(bind=True, base=BaseTaskWithRetry)
def update_batch(self, locatie_ids):
    from apps.locatie.models import Locatie

    with transaction.atomic():
        locaties = Locatie.objects.filter(id__in=locatie_ids)
        for locatie in locaties:
            locatie.save()

    return f"Updated {len(locatie_ids)} locations"


@shared_task(bind=True)
def task_update_locatie_primair(self):
    from apps.locatie.models import Locatie

    locaties = Locatie.objects.filter(
        primair=True,
        gewicht=0.2,
    ).update(gewicht=0.25)

    return f"Aantal geupdate locaties {locaties}"
