import uuid
from datetime import timedelta

import celery
from celery import shared_task, states
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db.models import OuterRef, Q, Subquery
from django_celery_beat.models import ClockedSchedule, PeriodicTask
from django_celery_results.models import TaskResult

logger = get_task_logger(__name__)

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6


class BaseTaskWithRetry(celery.Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_notificatie_voor_signaal_melding_afgesloten(self, signaal_uuid):
    from apps.signalen.models import Signaal

    signaal_instantie = Signaal.objects.get(uuid=signaal_uuid)
    response = signaal_instantie.notificatie_melding_afgesloten()
    error = response.get("error", {})
    if error.get("status_code") in [404]:
        logger.warning(
            f"task_notificatie_voor_signaal_melding_afgesloten: signaal_uuid={signaal_uuid} is niet gevonden"
        )
    if error.get("status_code") and error.get("status_code") not in [404]:
        raise Exception(
            f"task_notificatie_voor_signaal_melding_afgesloten error: {error}, signaal_uuid={signaal_uuid}"
        )

    return f"Signaal uuid: {signaal_instantie.uuid}"


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
def task_notificaties_voor_melding_veranderd_v2(self, melding_url, notificatie_type):
    from apps.applicaties.models import Applicatie

    applicaties = Applicatie.objects.filter(stuur_notificatie_melding_veranderd=True)

    for applicatie in applicaties:
        taskresults = TaskResult.objects.filter(
            Q(task_kwargs__contains=str(applicatie.uuid))
            & Q(task_kwargs__contains=melding_url)
            & Q(status__in=[states.PENDING, states.RETRY, states.STARTED])
        )
        if not taskresults:
            task_notificatie_voor_melding_veranderd_v2.delay(
                applicatie_uuid=str(applicatie.uuid),
                melding_url=melding_url,
                notificatie_type=notificatie_type,
            )
    return {
        "applicatie_count": applicaties.count(),
        "melding_url": melding_url,
        "notificatie_type": notificatie_type,
    }


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


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_notificatie_voor_melding_veranderd_v2(
    self, applicatie_uuid, melding_url, notificatie_type
):
    from apps.applicaties.models import Applicatie

    applicatie = Applicatie.objects.get(uuid=uuid.UUID(applicatie_uuid))
    notificatie_response = applicatie.melding_veranderd_notificatie_voor_applicatie(
        melding_url,
        notificatie_type,
    )
    error = notificatie_response.get("error")
    if error:
        logger.error(
            f'task_notificatie_voor_melding_veranderd: applicatie:  {applicatie.naam}, bericht: {error.get("bericht")}, status code: {error.get("status_code")}'
        )
    return {
        "applicatie_naam": applicatie.naam,
        "melding_url": melding_url,
        "notificatie_type": notificatie_type,
    }


@shared_task(bind=True)
def task_bijlages_voor_meldingen_reeks_opruimen(
    self, start_index=None, eind_index=None, order_by="id"
):
    from apps.meldingen.models import Melding

    melding_ids = list(
        Melding.objects.all().order_by(order_by).values_list("id", flat=True)
    )[start_index:eind_index]
    task_bijlages_voor_geselecteerde_meldingen_opruimen.delay(melding_ids)


@shared_task(bind=True)
def task_bijlages_voor_geselecteerde_meldingen_opruimen(self, melding_ids):
    from apps.meldingen.models import Melding

    for melding_id in melding_ids:
        # alle melding bijlages op termijn opruimen
        meldingen = Melding.objects.filter(
            id=melding_id,
            afgesloten_op__isnull=False,
        )
        if not meldingen:
            logger.warning(f"Melding met id={melding_id}, is nog niet afgesloten")
            continue
        melding = meldingen[0]

        periodic_task_name = (
            f"clocked_periodic_task_bijlages_voor_melding_opruimen_{melding.id}"
        )
        existing_tasks = PeriodicTask.objects.filter(name=periodic_task_name)
        if existing_tasks:
            existing_tasks[0].delete()
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

    meldingen = Melding.objects.filter(
        id=melding_id,
        afgesloten_op__isnull=False,
    )
    if not meldingen:
        return f"Melding met id={melding_id}, is nog niet afgesloten"
    melding = meldingen[0]

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

    return {"bijlagen_aantal": len(bijlagen)}


@shared_task(bind=True)
def task_vernieuw_melding_zoek_tekst_voor_melding_reeks(
    self, start_index=None, eind_index=None, order_by="id", melding_ids=[]
):
    from apps.meldingen.models import Melding

    if not melding_ids:
        melding_ids = list(
            Melding.objects.all().order_by(order_by).values_list("id", flat=True)
        )[start_index:eind_index]
    for melding_id in melding_ids:
        task_vernieuw_melding_zoek_tekst.delay(melding_id)

    return f"Melding zoek tekst vernieuwen voor, start_index={start_index}, eind_index={eind_index}, melding_ids={len(melding_ids)}"


@shared_task(bind=True)
def task_vernieuw_melding_zoek_tekst(self, melding_id):
    from apps.meldingen.models import Melding

    meldingen = Melding.objects.filter(id=melding_id)

    if not meldingen:
        return f"Melding met id={melding_id}, is nog niet gevonden"
    melding = meldingen[0]

    melding.zoek_tekst = melding.get_zoek_tekst()
    melding.save(update_fields=["zoek_tekst"])

    return f"Melding zoek tekst vernieuwd voor melding_id={melding_id}"


@shared_task(bind=True)
def task_set_melding_referentie_locatie_melding_voor_reeks(
    self, start_index=None, eind_index=None, order_by="id", melding_ids=[]
):
    from apps.meldingen.models import Melding

    if not melding_ids:
        melding_ids = list(
            Melding.objects.all().order_by(order_by).values_list("id", flat=True)
        )[start_index:eind_index]
    for melding_id in melding_ids:
        task_set_melding_referentie_locatie_voor_melding.delay(melding_id)

    return f"Melding referentie locaties vernieuwen voor, start_index={start_index}, eind_index={eind_index}, melding_ids={len(melding_ids)}"


@shared_task(bind=True)
def task_set_melding_referentie_locatie_voor_melding(self, melding_id):
    from apps.locatie.models import Locatie
    from apps.meldingen.models import Melding

    locaties = Locatie.objects.filter(
        melding=melding_id,
        locatie_type__in=["adres", "graf"],
    ).order_by("-gewicht")

    meldingen = Melding.objects.filter(
        referentie_locatie__isnull=True,
        id=melding_id,
    )

    if meldingen and locaties:
        meldingen[0].referentie_locatie = locaties[0]
        meldingen[0].save(update_fields=["referentie_locatie"])

    return f"Referentie locatie set voor melding: {melding_id}"


@shared_task(bind=True)
def task_set_melding_referentie_locatie(self):
    from apps.locatie.models import Locatie
    from apps.meldingen.models import Melding

    locaties = Locatie.objects.filter(
        melding=OuterRef("pk"),
        locatie_type__in=["adres", "graf"],
    ).order_by("-gewicht")

    meldingen = Melding.objects.filter(
        referentie_locatie__isnull=True,
    ).annotate(
        primair_locatie_id=Subquery(locaties.values("id")[:1]),
    )

    update_list = []
    for melding in meldingen:
        melding.referentie_locatie_id = melding.primair_locatie_id
        update_list.append(melding)

    Melding.objects.bulk_update(update_list, ["referentie_locatie"])

    return f"Aantal geupdate locaties {len(meldingen)}"


@shared_task(bind=True)
def task_set_melding_thumbnail_afbeelding_voor_melding_reeks(
    self, start_index=None, eind_index=None, order_by="id", melding_ids=[]
):
    from apps.meldingen.models import Melding

    if not melding_ids:
        melding_ids = list(
            Melding.objects.all().order_by(order_by).values_list("id", flat=True)
        )[start_index:eind_index]
    for melding_id in melding_ids:
        task_set_melding_thumbnail_afbeelding.delay(melding_id)

    return f"Set thumbnail_afbeelding voor melding indexes, start_index={start_index}, eind_index={eind_index}, melding_ids={len(melding_ids)}"


@shared_task(bind=True)
def task_set_melding_thumbnail_afbeelding(self, melding_id):
    from apps.meldingen.models import Melding

    melding = Melding.objects.get(id=melding_id)

    melding_bijlagen = melding.get_bijlagen()
    if melding_bijlagen:
        melding.thumbnail_afbeelding = melding_bijlagen[0]
        melding.save(update_fields=["thumbnail_afbeelding"])
        return f"Bijlage {melding_bijlagen[0]}, voor melding_id={melding_id}"
    return f"Geen bijlage voor melding_id={melding_id}"
