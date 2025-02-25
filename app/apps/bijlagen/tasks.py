import os

import celery
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6
RETRY_BACKOFF_MAX = 60 * 30
RETRY_BACKOFF = 120


class BaseTaskWithRetry(celery.Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY


class BaseTaskWithRetryBackoff(celery.Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY
    retry_backoff_max = RETRY_BACKOFF_MAX
    retry_backoff = RETRY_BACKOFF
    retry_jitter = True


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_aanmaken_afbeelding_versies(self, bijlage_id):
    from apps.bijlagen.models import Bijlage

    bijlage_instance = Bijlage.objects.get(id=bijlage_id)
    bijlage_instance.aanmaken_afbeelding_versies()
    bijlage_instance.save()

    return f"Bijlage id: {bijlage_instance.id}"


@shared_task(bind=True)
def task_verwijder_bestand(self, melding_url, pad):
    if os.path.isfile(pad):
        os.remove(pad)
    return f"Verwijder_bestand: melding_url={melding_url}, pad={pad}"


@shared_task(bind=True)
def task_minify_origineel_bijlage_bestand(self, bijlage_id):
    from apps.bijlagen.models import Bijlage

    bijlage_instance = Bijlage.objects.get(id=bijlage_id)
    origineel_bestand_path = bijlage_instance.minify_origineel_bestand()

    os.remove(origineel_bestand_path)

    bijlage_instance.save()

    return f"Bijlage id: {bijlage_instance.id}"
