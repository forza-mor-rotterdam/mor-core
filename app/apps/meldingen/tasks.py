import celery
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6

LOCK_EXPIRE = 5


class BaseTaskWithRetry(celery.Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_notificatie_voor_signaal_melding_afgesloten(self, signaal_id):
    from apps.signalen.models import Signaal

    signaal_instantie = Signaal.objects.get(pk=signaal_id)
    signaal_instantie.notificatie_melding_afgesloten()

    return f"Signaal id: {signaal_instantie.pk}"


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_notificaties_voor_melding_veranderd(*args, **kwargs):
    from apps.applicaties.models import Applicatie

    melding_url = kwargs.get("melding_url")
    notificatie_type = kwargs.get("notificatie_type")
    if not melding_url or not notificatie_type:
        return "melding_url en notificatie_type zijn verplicht"

    for applicatie in Applicatie.objects.all():
        task_notificatie_voor_melding_veranderd.delay(
            applicatie.id,
            melding_url,
            notificatie_type,
        )
    return f"Applicaties aantal: {Applicatie.objects.all().count()}, melding_url={melding_url}, notificatie_type={notificatie_type}"


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_notificatie_voor_melding_veranderd(
    self, applicatie_id, melding_url, notificatie_type
):
    from apps.applicaties.models import Applicatie

    applicatie = Applicatie.objects.get(pk=applicatie_id)
    notificatie_response = applicatie.melding_veranderd_notificatie_voor_applicatie(
        melding_url,
        notificatie_type,
    )
    return f"Applicatie id: {applicatie.naam}, melding_url={melding_url}, notificatie_type={notificatie_type}, status code={notificatie_response.status_code}"
