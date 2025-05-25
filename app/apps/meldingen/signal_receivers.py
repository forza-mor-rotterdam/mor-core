import logging

from apps.bijlagen.tasks import task_aanmaken_afbeelding_versies, task_verwijder_bestand
from apps.meldingen.managers import (
    afgesloten,
    gebeurtenis_toegevoegd,
    signaal_aangemaakt,
    status_aangepast,
    taakopdracht_aangemaakt,
    taakopdracht_notificatie,
    taakopdracht_verwijderd,
    urgentie_aangepast,
    verwijderd,
)
from apps.meldingen.tasks import (
    task_bijlages_voor_geselecteerde_meldingen_opruimen,
    task_notificatie_voor_signaal_melding_afgesloten,
    task_notificaties_voor_melding_veranderd,
    task_vernieuw_melding_zoek_tekst,
)
from apps.status.models import Status
from apps.taken.models import Taakgebeurtenis, Taakstatus
from apps.taken.tasks import task_taak_aanmaken, task_taak_verwijderen
from celery import chord
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(signaal_aangemaakt, dispatch_uid="melding_signaal_aangemaakt")
def signaal_aangemaakt_handler(sender, melding, signaal, *args, **kwargs):
    if kwargs.get("raw"):
        return
    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.s(bijlage.pk)
        for bijlage in signaal.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = task_notificaties_voor_melding_veranderd.s(
        melding_url=melding.get_absolute_url(),
        notificatie_type="signaal_aangemaakt",
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()
    task_vernieuw_melding_zoek_tekst.delay(melding.id)


@receiver(status_aangepast, dispatch_uid="melding_status_aangepast")
def status_aangepast_handler(sender, melding, status, vorige_status, *args, **kwargs):
    if kwargs.get("raw"):
        return
    if melding.afgesloten_op and melding.status.is_afgesloten():
        afgesloten.send_robust(
            sender=sender,
            melding=melding,
        )
    else:
        task_notificaties_voor_melding_veranderd.delay(
            melding_url=melding.get_absolute_url(),
            notificatie_type="status_aangepast",
        )


@receiver(urgentie_aangepast, dispatch_uid="melding_urgentie_aangepast")
def urgentie_aangepast_handler(sender, melding, vorige_urgentie, *args, **kwargs):
    if kwargs.get("raw"):
        return
    task_notificaties_voor_melding_veranderd.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="urgentie_aangepast",
    )


@receiver(afgesloten, dispatch_uid="melding_afgesloten")
def afgesloten_handler(sender, melding, *args, **kwargs):
    if kwargs.get("raw"):
        return
    task_notificaties_voor_melding_veranderd.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="afgesloten",
    )

    for taakgebeurtenis in Taakgebeurtenis.objects.filter(
        taakstatus__naam__in=[
            Taakstatus.NaamOpties.VOLTOOID,
            Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK,
        ],
        taakopdracht__melding=melding,
        additionele_informatie__taak_url__isnull=True,
    ):
        task_taak_verwijderen.delay(
            taakopdracht_id=taakgebeurtenis.taakopdracht.id,
            gebruiker=taakgebeurtenis.gebruiker,
        )

    if melding.status.naam == Status.NaamOpties.AFGEHANDELD:
        for signaal in melding.signalen_voor_melding.all():
            task_notificatie_voor_signaal_melding_afgesloten.delay(signaal.pk)

        task_bijlages_voor_geselecteerde_meldingen_opruimen.delay([melding.id])


@receiver(gebeurtenis_toegevoegd, dispatch_uid="melding_gebeurtenis_toegevoegd")
def gebeurtenis_toegevoegd_handler(
    sender, meldinggebeurtenis, melding, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.s(bijlage.pk)
        for bijlage in meldinggebeurtenis.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = task_notificaties_voor_melding_veranderd.s(
        melding_url=melding.get_absolute_url(),
        notificatie_type="gebeurtenis_toegevoegd",
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
    task_notificaties_voor_melding_veranderd.delay(
        melding_url=melding_url,
        notificatie_type="melding_verwijderd",
    )


@receiver(taakopdracht_aangemaakt, dispatch_uid="taakopdracht_aangemaakt")
def taakopdracht_aangemaakt_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    task_notificaties_voor_melding_veranderd.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="taakopdracht_aangemaakt",
    )
    task_taak_aanmaken.delay(
        taakgebeurtenis_id=taakgebeurtenis.id,
    )


@receiver(taakopdracht_notificatie, dispatch_uid="taakopdracht_notificatie")
def taakopdracht_status_aangepast_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    if kwargs.get("raw"):
        return

    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.s(bijlage.pk)
        for bijlage in taakgebeurtenis.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = task_notificaties_voor_melding_veranderd.s(
        melding_url=melding.get_absolute_url(),
        notificatie_type="taakopdracht_notificatie",
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()


@receiver(taakopdracht_verwijderd, dispatch_uid="taakopdracht_verwijderd")
def taakopdracht_verwijderd_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    if kwargs.get("raw"):
        return
    task_taak_verwijderen.delay(
        taakopdracht_id=taakopdracht.id,
    )
