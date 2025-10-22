from datetime import datetime

from celery import Task, shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import OperationalError, transaction

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


def get_taak_data(taakopdracht):
    if taakopdracht.applicatie:
        taak_response = taakopdracht.applicatie._do_request(
            taakopdracht.taak_url if taakopdracht.taak_url else "/ditgaatmis"
        )
        if taak_response.status_code == 200:
            return taak_response.json()
        if taak_response.status_code == 404:
            logger.warning(
                f"Fix taakopdracht issues, Fixer taak not found for taakopdracht id: {taakopdracht.id}, taak_url: {taakopdracht.taak_url}, status code: {taak_response.status_code}"
            )
            return "404 Fixer taak not found"
        logger.error(
            f"Fix taakopdracht issues, Fixer taak ophalen error. Status code: {taak_response.status_code}, taakopdracht id: {taakopdracht.id}, taak_url: {taakopdracht.taak_url}, response_text={taak_response.text}"
        )
        taak_response.raise_for_status()


@shared_task(bind=True, base=BaseTaskWithRetry)
def move_resolutie_to_taakgebeurtenis(self):
    from apps.taken.models import Taakgebeurtenis, Taakopdracht

    for taakopdracht in Taakopdracht.objects.exclude(resolutie__isnull=True):
        taakgebeurtenis = Taakgebeurtenis.objects.filter(
            taakopdracht=taakopdracht, taakstatus__naam="voltooid"
        ).first()
        if taakgebeurtenis:
            taakgebeurtenis.resolutie = taakopdracht.resolutie
            taakgebeurtenis.save()


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_taak_aanmaken(self, taakgebeurtenis_id, check_taak_url=True):
    from apps.meldingen.managers import MeldingManager
    from apps.taken.models import Taakgebeurtenis, Taakopdracht

    with transaction.atomic():
        try:
            taakgebeurtenis = (
                Taakgebeurtenis.objects.using(settings.DEFAULT_DATABASE_KEY)
                .select_for_update(nowait=True)
                .get(id=taakgebeurtenis_id)
            )
        except ObjectDoesNotExist:
            logger.warning(f"Taakgebeurtenis met id {taakgebeurtenis_id} bestaat niet.")

        except OperationalError:
            raise MeldingManager.TaakgebeurtenisInGebruik(
                "De taakgebeurtenis is op dit moment in gebruik, probeer het later nog eens."
            )

        try:
            taakopdracht = (
                Taakopdracht.objects.using(settings.DEFAULT_DATABASE_KEY)
                .select_for_update(nowait=True)
                .get(id=taakgebeurtenis.taakopdracht.id)
            )
        except ObjectDoesNotExist:
            logger.warning(
                f"Taakopdracht met id {taakgebeurtenis.taakopdracht.id} bestaat niet."
            )
        except OperationalError:
            raise MeldingManager.TaakopdrachtInGebruik(
                "De taakopdracht is op dit moment in gebruik, probeer het later nog eens."
            )

        if taakopdracht.taak_url and check_taak_url:
            return f"Taak is al aangemaakt bij {taakopdracht.applicatie.naam}: taakopdracht_id: {taakopdracht.id}"

        eerste_taakgebeurtenis = (
            taakopdracht.taakgebeurtenissen_voor_taakopdracht.order_by(
                "aangemaakt_op"
            ).first()
        )
        if eerste_taakgebeurtenis != taakgebeurtenis:
            raise MeldingManager.TaakgebeurtenisOntbreekt(
                f"De eerste taakgebeurtenis moet de huidige zijn. taakopdracht_id: {taakopdracht.id}"
            )

        taakapplicatie_data = {
            "taaktype": taakopdracht.taaktype,
            "titel": taakopdracht.titel,
            "bericht": taakopdracht.bericht,
            "taakopdracht": taakopdracht.get_absolute_url(),
            "melding": taakopdracht.melding.get_absolute_url(),
            "gebruiker": taakgebeurtenis.gebruiker,
            "additionele_informatie": taakopdracht.additionele_informatie,
            "omschrijving_intern": taakgebeurtenis.omschrijving_intern,
        }
        taak_aanmaken_response = taakopdracht.applicatie.taak_aanmaken(
            taakapplicatie_data
        )

        error = taak_aanmaken_response.get("error")
        if error:
            raise Exception(
                f'De taak kon niet worden aangemaakt in {taakopdracht.applicatie.naam} o.b.v. taakopdracht met id {taakopdracht.id}, bericht: {error.get("bericht")} status code: {error.get("status_code")}'
            )

        taak_url = taak_aanmaken_response.get("_links", {}).get("self")
        logger.info(
            f'taakaaplicatie response _links: {taak_aanmaken_response.get("_links", {})}'
        )
        taakopdracht.taak_url = taak_url
        taakopdracht.save()
        additionele_informatie = {}
        additionele_informatie.update(taakgebeurtenis.additionele_informatie)
        additionele_informatie.update({"taak_url": taakopdracht.taak_url})
        taakgebeurtenis.additionele_informatie = additionele_informatie
        taakgebeurtenis.save()
        if taak_aanmaken_response.get("aangemaakt_op"):
            taakgebeurtenis.aangemaakt_op = datetime.fromisoformat(
                taak_aanmaken_response.get("aangemaakt_op")
            )
            taakgebeurtenis.save()

    return f"De taak is aangemaakt in {taakopdracht.applicatie.naam}, o.b.v. taakopdracht met id: {taakopdracht.id}, de taakapplicatie taak url is: {taakopdracht.taak_url}."


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_taak_aanmaken_v2(self, taakopdracht_uuid):
    import uuid

    from apps.meldingen.managers import MeldingManager
    from apps.taken.models import Taakopdracht
    from celery import states

    with transaction.atomic():
        try:
            taakopdracht = (
                Taakopdracht.objects.using(settings.DEFAULT_DATABASE_KEY)
                .select_for_update(nowait=True)
                .get(uuid=uuid.UUID(taakopdracht_uuid))
            )
        except ObjectDoesNotExist:
            logger.warning(f"Taakopdracht met uuid {taakopdracht_uuid} bestaat niet.")
        except OperationalError:
            raise MeldingManager.TaakopdrachtInGebruik(
                "De taakopdracht is op dit moment in gebruik, probeer het later nog eens."
            )

        if taakopdracht.taak_url:
            return f"Taak is al aangemaakt bij {taakopdracht.applicatie.naam}: taakopdracht_uuid: {taakopdracht_uuid}"

        if (
            taakopdracht.task_taak_aanmaken
            and taakopdracht.task_taak_aanmaken.status in [states.PENDING, states.RETRY]
        ):
            return f"De taakopdracht is nog niet gesynchroniseerd({taakopdracht.task_taak_aanmaken.status}) met de taakapplicatie({taakopdracht.applicatie.naam}): taakopdracht_uuid: {taakopdracht_uuid}"

        taakgebeurtenissen = taakopdracht.taakgebeurtenissen_voor_taakopdracht.order_by(
            "aangemaakt_op"
        )

        taakapplicatie_data = {
            "taaktype": taakopdracht.taaktype,
            "titel": taakopdracht.titel,
            "bericht": taakopdracht.bericht,
            "taakopdracht": taakopdracht.get_absolute_url(),
            "melding": taakopdracht.melding.get_absolute_url(),
            "gebruiker": taakgebeurtenissen[0].gebruiker
            if taakgebeurtenissen
            else None,
            "additionele_informatie": taakopdracht.additionele_informatie,
            "omschrijving_intern": taakgebeurtenissen[0].omschrijving_intern
            if taakgebeurtenissen
            else None,
        }
        taak_aanmaken_response = taakopdracht.applicatie.taak_aanmaken(
            taakapplicatie_data
        )

        error = taak_aanmaken_response.get("error")
        if error:
            raise Exception(
                f'De taak kon niet worden aangemaakt in {taakopdracht.applicatie.naam} o.b.v. taakopdracht met uuid {taakopdracht_uuid}, bericht: {error.get("bericht")} status code: {error.get("status_code")}'
            )

        taak_url = taak_aanmaken_response.get("_links", {}).get("self")
        logger.info(
            f'taakaaplicatie response _links: {taak_aanmaken_response.get("_links", {})}'
        )
        taakopdracht.taak_url = taak_url
        taakopdracht.save(update_fields=["taak_url"])
        if taak_aanmaken_response.get("aangemaakt_op") and taakgebeurtenissen:
            taakgebeurtenissen[0].aangemaakt_op = datetime.fromisoformat(
                taak_aanmaken_response.get("aangemaakt_op")
            )
            taakgebeurtenissen[0].save(update_fields=["aangemaakt_op"])

    return f"De taak is aangemaakt in {taakopdracht.applicatie.naam}, o.b.v. taakopdracht met uuid: {taakopdracht_uuid}, de taakapplicatie taak url is: {taakopdracht.taak_url}."


@shared_task(bind=True, base=BaseTaskWithRetry)
def task_taak_verwijderen(self, taakopdracht_id, gebruiker=None):
    from apps.taken.models import Taakopdracht

    taakopdracht = Taakopdracht.objects.get(id=taakopdracht_id)

    if not taakopdracht.taak_url:
        raise Exception(
            f"De taak kan niet worden verwijderd omdat de taak_url voor de taakapplicatie ontbreekt: taakaaplicatie={taakopdracht.applicatie.naam}, taakopdracht_id={taakopdracht.id}."
        )

    taak_verwijderen_response = taakopdracht.applicatie.taak_verwijderen(
        taakopdracht.taak_url,
        gebruiker=gebruiker,
    )
    error = taak_verwijderen_response.get("error")
    if error:
        raise Exception(
            f'Taak verwijderen is mislukt: taakopdracht.id={taakopdracht.id}, bericht={error.get("bericht")}, status code={error.get("status_code")}'
        )

    return f"De taak is verwijderd in {taakopdracht.applicatie.naam}, o.b.v. taakopdracht met id: {taakopdracht.id}."
