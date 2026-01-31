import logging

from apps.bijlagen.tasks import task_aanmaken_afbeelding_versies, task_verwijder_bestand
from apps.meldingen.managers import (
    afgesloten,
    gebeurtenis_toegevoegd,
    signaal_aangemaakt,
    status_aangepast,
    taakopdracht_aangemaakt,
    taakopdracht_notificatie,
    taakopdracht_uitgezet,
    taakopdracht_verwijderd,
    urgentie_aangepast,
    verwijderd,
)
from apps.meldingen.producers import (
    MeldingAangemaaktProducer,
    TaakopdrachtAangemaaktProducer,
    TaakopdrachtVeranderdProducer,
)
from apps.meldingen.tasks import (
    task_bijlages_voor_geselecteerde_meldingen_opruimen,
    task_notificatie_voor_signaal_melding_afgesloten,
    task_notificaties_voor_melding_veranderd_v2,
    task_vernieuw_melding_zoek_tekst,
)
from apps.status.models import Status
from apps.taken.models import Taakgebeurtenis
from apps.taken.tasks import task_taak_verwijderen
from celery import chord, states
from celery.signals import before_task_publish
from django.dispatch import receiver
from django_celery_results.models import TaskResult

logger = logging.getLogger(__name__)


@receiver(signaal_aangemaakt, dispatch_uid="melding_signaal_aangemaakt")
def signaal_aangemaakt_handler(sender, melding, signaal, *args, **kwargs):
    if kwargs.get("raw"):
        return
    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.si(bijlage.pk)
        for bijlage in signaal.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = (
        task_notificaties_voor_melding_veranderd_v2.si(
            melding_url=melding.get_absolute_url(),
            notificatie_type="signaal_aangemaakt",
        )
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()
    task_vernieuw_melding_zoek_tekst.delay(melding.id)

    if melding.meldinggebeurtenissen_voor_melding.count() == 1:
        melding_aangemaakt_producer = MeldingAangemaaktProducer()
        melding_aangemaakt_producer.publish(melding)


@receiver(status_aangepast, dispatch_uid="melding_status_aangepast")
def status_aangepast_handler(
    sender, melding, status, vorige_status, taakopdrachten, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    if melding.afgesloten_op and melding.status.is_afgesloten():
        afgesloten.send_robust(
            sender=sender,
            melding=melding,
            taakopdrachten=taakopdrachten,
        )
    else:
        task_notificaties_voor_melding_veranderd_v2.delay(
            melding_url=melding.get_absolute_url(),
            notificatie_type="status_aangepast",
        )


@receiver(urgentie_aangepast, dispatch_uid="melding_urgentie_aangepast")
def urgentie_aangepast_handler(sender, melding, vorige_urgentie, *args, **kwargs):
    if kwargs.get("raw"):
        return
    task_notificaties_voor_melding_veranderd_v2.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="urgentie_aangepast",
    )


@receiver(afgesloten, dispatch_uid="melding_afgesloten")
def afgesloten_handler(sender, melding, taakopdrachten=[], *args, **kwargs):
    if kwargs.get("raw"):
        return
    task_notificaties_voor_melding_veranderd_v2.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="afgesloten",
    )
    for taakopdracht in taakopdrachten:
        taakgebeurtenissen = taakopdracht.taakgebeurtenissen_voor_taakopdracht.filter(
            resolutie=Taakgebeurtenis.ResolutieOpties.GEANNULEERD
        )
        task_taak_verwijderen.delay(
            taakopdracht_id=taakopdracht.id,
            gebruiker=taakgebeurtenissen[0].gebruiker if taakgebeurtenissen else None,
        )

    if melding.status.naam == Status.NaamOpties.AFGEHANDELD:
        for signaal in melding.signalen_voor_melding.all():
            task_notificatie_voor_signaal_melding_afgesloten.delay(
                signaal_uuid=signaal.uuid
            )

        task_bijlages_voor_geselecteerde_meldingen_opruimen.delay([melding.id])


@receiver(gebeurtenis_toegevoegd, dispatch_uid="melding_gebeurtenis_toegevoegd")
def gebeurtenis_toegevoegd_handler(
    sender, meldinggebeurtenis, melding, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.si(bijlage.pk)
        for bijlage in meldinggebeurtenis.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = (
        task_notificaties_voor_melding_veranderd_v2.si(
            melding_url=melding.get_absolute_url(),
            notificatie_type="gebeurtenis_toegevoegd",
        )
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()

    if meldinggebeurtenis.locatie:
        task_vernieuw_melding_zoek_tekst.delay(melding.id)


@receiver(verwijderd, dispatch_uid="melding_verwijderd")
def melding_verwijderd_handler(
    sender, melding_url, bijlage_paden, samenvatting, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    logger.info(
        f"Melding verwijderd: melding_url={melding_url}, samenvatting={samenvatting}"
    )
    for pad in bijlage_paden:
        task_verwijder_bestand.delay(
            melding_url=melding_url,
            pad=pad,
        )
    task_notificaties_voor_melding_veranderd_v2.delay(
        melding_url=melding_url,
        notificatie_type="melding_verwijderd",
    )


@receiver(taakopdracht_aangemaakt, dispatch_uid="taakopdracht_aangemaakt")
def taakopdracht_aangemaakt_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    task_notificaties_voor_melding_veranderd_v2.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="taakopdracht_aangemaakt",
    )

    if taakopdracht.uitgezet_op:
        # taak aanmaken task aanmaken en Taskresult db instance relateren aan taakopdracht instance
        taakopdracht.start_task_taak_aanmaken()

    taakopdracht_aangemaakt_producer = TaakopdrachtAangemaaktProducer()
    taakopdracht_aangemaakt_producer.publish(melding, taakgebeurtenis)


@receiver(taakopdracht_notificatie, dispatch_uid="taakopdracht_notificatie")
def taakopdracht_status_aangepast_handler(
    sender,
    melding,
    taakopdracht,
    taakgebeurtenis,
    vervolg_taakopdrachten,
    *args,
    **kwargs,
):
    if kwargs.get("raw"):
        return

    for vervolg_taakopdracht in vervolg_taakopdrachten:
        vervolg_taakopdracht.start_task_taak_aanmaken()

    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.si(bijlage.pk)
        for bijlage in taakgebeurtenis.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = (
        task_notificaties_voor_melding_veranderd_v2.si(
            melding_url=melding.get_absolute_url(),
            notificatie_type="taakopdracht_notificatie",
        )
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()

    taakopdracht_veranderd_producer = TaakopdrachtVeranderdProducer()
    taakopdracht_veranderd_producer.publish(melding, taakgebeurtenis)


@receiver(taakopdracht_uitgezet, dispatch_uid="taakopdracht_uitgezet")
def taakopdracht_uitgezet_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    if kwargs.get("raw"):
        return

    taakopdracht.start_task_taak_aanmaken()


@receiver(taakopdracht_verwijderd, dispatch_uid="taakopdracht_verwijderd")
def taakopdracht_verwijderd_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    task_taak_verwijderen.delay(
        taakopdracht_id=taakopdracht.id,
    )
    task_notificaties_voor_melding_veranderd_v2.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="taakopdracht_aangemaakt",
    )


@before_task_publish.connect
def create_task_result_on_publish(sender=None, headers=None, body=None, **kwargs):
    if "task" not in headers:
        return

    TaskResult.objects.store_result(
        "application/json",
        "utf-8",
        headers["id"],
        None,
        states.PENDING,
        task_name=headers["task"],
        task_args=headers["argsrepr"],
        task_kwargs=headers["kwargsrepr"],
    )
