from datetime import timedelta

import celery
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django_celery_beat.models import ClockedSchedule, PeriodicTask

logger = get_task_logger(__name__)

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6


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

    for applicatie in Applicatie.objects.filter(
        applicatie_type=Applicatie.ApplicatieTypes.TAAKAPPLICATIE
    ):
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
    error = notificatie_response.get("error")
    if error:
        logger.error(
            f'task_notificatie_voor_melding_veranderd: applicatie:  {applicatie.naam}, bericht: {error.get("bericht")}, status code: {error.get("status_code")}'
        )
    return f"Applicatie naam: {applicatie.naam}, melding_url={melding_url}, notificatie_type={notificatie_type}"


@shared_task(bind=True)
def task_bijlages_voor_geselecteerde_meldingen_opruimen(self, melding_ids):
    from apps.meldingen.models import Melding

    for melding_id in melding_ids:
        # alle melding bijlages op termijn opruimen
        melding = Melding.objects.filter(
            id=melding_id,
            afgesloten_op__isnull=False,
        ).first()
        if not melding:
            return f"Melding met id={melding.id}, is nog niet afgesloten"

        periodic_task_name = (
            f"clocked_periodic_task_bijlages_voor_melding_opruimen_{melding.id}"
        )
        existing_task = PeriodicTask.objects.filter(name=periodic_task_name).first()
        if existing_task:
            existing_task.delete()
        clocked_schedule = ClockedSchedule.objects.create(
            clocked_time=melding.afgesloten_op
            + timedelta(seconds=settings.MELDING_AFGESLOTEN_BIJLAGE_OPRUIMEN_SECONDS)
        )
        PeriodicTask.objects.create(
            clocked=clocked_schedule,
            name=periodic_task_name,
            task="apps.meldingen.tasks.task_bijlages_voor_melding_opruimen",
            one_off=True,
            args=[melding.id],
        )

    return melding_ids


@shared_task(bind=True)
def task_bijlages_voor_melding_opruimen(self, melding_id):
    from apps.bijlagen.tasks import task_bijlage_opruimen
    from apps.meldingen.models import Melding

    melding = Melding.objects.filter(
        id=melding_id,
        afgesloten_op__isnull=False,
    ).first()
    if not melding:
        return f"Melding met id={melding.id}, is nog niet afgesloten"

    bijlagen = []

    for bijlage in melding.bijlagen.all():
        bijlagen.append(bijlage)

    for bijlage in [
        bijlage
        for meldinggebeurtenis in melding.meldinggebeurtenissen_voor_melding.all()
        for bijlage in meldinggebeurtenis.bijlagen.all()
    ]:
        bijlagen.append(bijlage)

    for bijlage in [
        bijlage
        for signaal in melding.signalen_voor_melding.all()
        for bijlage in signaal.bijlagen.all()
    ]:
        bijlagen.append(bijlage)

    for bijlage in [
        bijlage
        for taakopdracht in melding.taakopdrachten_voor_melding.all()
        for taakgebeurtenis in taakopdracht.taakgebeurtenissen_voor_taakopdracht.all()
        for bijlage in taakgebeurtenis.bijlagen.all()
    ]:
        bijlagen.append(bijlage)

    for bijlage in bijlagen:
        logger.info(f"bijlage opruimen: id={bijlage.id}")
        task_bijlage_opruimen.delay(bijlage.id)
        # if instantaan:
        # else:
        #     periodic_task_name = f"clocked_periodic_task_bijlage_opruimen_{bijlage.id}"
        #     existing_task = PeriodicTask.objects.filter(name=periodic_task_name).first()
        #     if existing_task:
        #         existing_task.delete()
        #     clocked_schedule = ClockedSchedule.objects.create(
        #         clocked_time=now + timedelta(seconds=settings.MELDING_AFGESLOTEN_BIJLAGE_OPRUIMEN_SECONDS)
        #     )
        #     PeriodicTask.objects.create(
        #         clocked=clocked_schedule,
        #         name=periodic_task_name,
        #         task="apps.bijlagen.tasks.task_bijlage_opruimen",
        #         one_off=True,
        #         args=[bijlage.id],
        #     )
