import logging

from apps.bijlagen.tasks import task_aanmaken_afbeelding_versies
from apps.meldingen.managers import (
    afgesloten,
    gebeurtenis_toegevoegd,
    signaal_aangemaakt,
    status_aangepast,
    taakopdracht_aangemaakt,
    taakopdracht_status_aangepast,
    urgentie_aangepast,
)
from apps.meldingen.tasks import (
    task_notificatie_voor_signaal_melding_afgesloten,
    task_notificaties_voor_melding_veranderd,
)
from apps.status.models import Status
from apps.taken.models import Taakgebeurtenis, Taakstatus
from apps.taken.tasks import task_taak_aanmaken, task_taak_status_aanpassen
from celery import chord
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(signaal_aangemaakt, dispatch_uid="melding_signaal_aangemaakt")
def signaal_aangemaakt_handler(sender, melding, signaal, *args, **kwargs):
    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.s(bijlage.pk)
        for bijlage in signaal.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = task_notificaties_voor_melding_veranderd.s(
        melding_url=melding.get_absolute_url(),
        notificatie_type="signaal_aangemaakt",
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()


@receiver(status_aangepast, dispatch_uid="melding_status_aangepast")
def status_aangepast_handler(sender, melding, status, vorige_status, *args, **kwargs):
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
    task_notificaties_voor_melding_veranderd.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="urgentie_aangepast",
    )


@receiver(afgesloten, dispatch_uid="melding_afgesloten")
def afgesloten_handler(sender, melding, *args, **kwargs):
    task_notificaties_voor_melding_veranderd.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="afgesloten",
    )

    for taakgebeurtenis in Taakgebeurtenis.objects.filter(
        taakstatus__naam=Taakstatus.NaamOpties.VOLTOOID,
        taakopdracht__melding=melding,
        additionele_informatie__taak_url__isnull=True,
    ):
        task_taak_status_aanpassen.delay(
            taakgebeurtenis_id=taakgebeurtenis.id,
        )

    if melding.status.naam == Status.NaamOpties.AFGEHANDELD:
        for signaal in melding.signalen_voor_melding.all():
            task_notificatie_voor_signaal_melding_afgesloten.delay(signaal.pk)


@receiver(gebeurtenis_toegevoegd, dispatch_uid="melding_gebeurtenis_toegevoegd")
def gebeurtenis_toegevoegd_handler(
    sender, meldinggebeurtenis, melding, *args, **kwargs
):
    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.s(bijlage.pk)
        for bijlage in meldinggebeurtenis.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = task_notificaties_voor_melding_veranderd.s(
        melding_url=melding.get_absolute_url(),
        notificatie_type="gebeurtenis_toegevoegd",
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()


@receiver(taakopdracht_aangemaakt, dispatch_uid="taakopdracht_aangemaakt")
def taakopdracht_aangemaakt_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    task_notificaties_voor_melding_veranderd.delay(
        melding_url=melding.get_absolute_url(),
        notificatie_type="taakopdracht_aangemaakt",
    )
    task_taak_aanmaken.delay(
        taakgebeurtenis_id=taakgebeurtenis.id,
    )


@receiver(taakopdracht_status_aangepast, dispatch_uid="taakopdracht_status_aangepast")
def taakopdracht_status_aangepast_handler(
    sender, melding, taakopdracht, taakgebeurtenis, *args, **kwargs
):
    task_taak_status_aanpassen.delay(
        taakgebeurtenis_id=taakgebeurtenis.id,
    )

    bijlages_aanmaken = [
        task_aanmaken_afbeelding_versies.s(bijlage.pk)
        for bijlage in taakgebeurtenis.bijlagen.all()
    ]
    notificaties_voor_melding_veranderd = task_notificaties_voor_melding_veranderd.s(
        melding_url=melding.get_absolute_url(),
        notificatie_type="taakopdracht_status_aangepast",
    )
    chord(bijlages_aanmaken, notificaties_voor_melding_veranderd)()
