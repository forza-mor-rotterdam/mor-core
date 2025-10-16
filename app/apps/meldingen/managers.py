import logging

import nh3
from apps.applicaties.models import Applicatie
from apps.services.onderwerpen import OnderwerpenService
from django.contrib.gis.db import models
from django.db import OperationalError, transaction
from django.db.models import Max
from django.dispatch import Signal as DjangoSignal
from django.utils import timezone

logger = logging.getLogger(__name__)

signaal_aangemaakt = DjangoSignal()
status_aangepast = DjangoSignal()
urgentie_aangepast = DjangoSignal()
afgesloten = DjangoSignal()
verwijderd = DjangoSignal()
gebeurtenis_toegevoegd = DjangoSignal()
taakopdracht_aangemaakt = DjangoSignal()
taakopdracht_status_aangepast = DjangoSignal()
taakopdracht_notificatie = DjangoSignal()
taakopdracht_verwijderd = DjangoSignal()


class MeldingManager(models.Manager):
    class OnderwerpenNietValide(Exception):
        pass

    class StatusVeranderingNietToegestaan(Exception):
        pass

    class MeldingInGebruik(Exception):
        pass

    class TaakopdrachtInGebruik(Exception):
        pass

    class TaakgebeurtenisInGebruik(Exception):
        pass

    class TaakgebeurtenisNietGevonden(Exception):
        pass

    class TaakopdrachtNietGevonden(Exception):
        pass

    class TaakVerwijderenFout(Exception):
        pass

    class TaakStatusAanpassenFout(Exception):
        pass

    class TaakAanmakenFout(Exception):
        pass

    class MeldingAfgeslotenFout(Exception):
        pass

    class TaakopdrachtAfgeslotenFout(Exception):
        pass

    class TaakopdrachtUrlOntbreekt(Exception):
        pass

    class TaakgebeurtenisOntbreekt(Exception):
        pass

    class TaakgebeurtenisFout(Exception):
        pass

    def signaal_aanmaken(self, serializer, db="default"):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status

        with transaction.atomic():
            signaal = serializer.save()
            melding = signaal.melding
            melding_gebeurtenis_data = {}

            if not melding:
                # Als het signaal geen melding relatie heeft, wordt een nieuwe melding aangemaakt
                melding = self.create(
                    origineel_aangemaakt=signaal.origineel_aangemaakt,
                    urgentie=signaal.urgentie,
                )
                eerste_onderwerp = signaal.onderwerpen.first()
                if eerste_onderwerp:
                    melding.onderwerp = eerste_onderwerp.bron_url
                for onderwerp in signaal.onderwerpen.all():
                    melding.onderwerpen.add(onderwerp)
                    onderwerp_response = OnderwerpenService().get_onderwerp(
                        onderwerp.bron_url
                    )
                    if onderwerp_response.get("priority") == "high":
                        melding.urgentie = 0.5

                for locatie in signaal.locaties_voor_signaal.all():
                    melding.locaties_voor_melding.add(locatie)

                first_locatie = signaal.locaties_voor_signaal.filter(
                    locatie_type__in=["graf", "adres"],
                ).first()
                if first_locatie:
                    melding.referentie_locatie = first_locatie
                    first_locatie.primair = True
                    first_locatie.gewicht = 0.25
                    first_locatie.save()

                status = Status()
                status.melding = melding
                status.save()

                melding.status = status
                if not melding.thumbnail_afbeelding and signaal.bijlagen:
                    melding.thumbnail_afbeelding = signaal.bijlagen.first()
                melding.save()
                signaal.melding = melding
                signaal.save()

                melding_gebeurtenis_data.update(
                    {
                        "gebeurtenis_type": Meldinggebeurtenis.GebeurtenisType.MELDING_AANGEMAAKT,
                        "omschrijving_intern": "Melding aangemaakt",
                        "signaal": signaal,
                        "status": status,
                    }
                )
            else:
                # Als het signaal al een melding relatie heeft, wordt een 'dubbele melding' aangemaakt
                melding_gebeurtenis_data.update(
                    {
                        "gebeurtenis_type": Meldinggebeurtenis.GebeurtenisType.SIGNAAL_TOEGEVOEGD,
                        "omschrijving_intern": signaal.bron_signaal_id,
                        "signaal": signaal,
                    }
                )
                if signaal.urgentie > melding.urgentie:
                    try:
                        locked_melding = (
                            Melding.objects.using(db)
                            .select_for_update(nowait=True)
                            .get(pk=melding.pk)
                        )
                    except OperationalError:
                        raise MeldingManager.MeldingInGebruik(
                            f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
                        )
                    locked_melding.urgentie = signaal.urgentie
                    locked_melding.save()

            melding_gebeurtenis_data.update(
                {
                    "melding": melding,
                }
            )
            melding_gebeurtenis = Meldinggebeurtenis(**melding_gebeurtenis_data)
            melding_gebeurtenis.save()
            transaction.on_commit(
                lambda: signaal_aangemaakt.send_robust(
                    sender=self.__class__,
                    melding=melding,
                    signaal=signaal,
                )
            )
        return signaal

    def urgentie_aanpassen(self, serializer, melding, db="default"):
        from apps.meldingen.models import Melding

        if melding.afgesloten_op:
            raise MeldingManager.MeldingAfgeslotenFout(
                f"De urgentie van een afgesloten melding kan niet meer worden veranderd. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
            )

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik(
                    f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
                )

            melding_gebeurtenis = serializer.save()
            vorige_urgentie = locked_melding.urgentie
            locked_melding.urgentie = melding_gebeurtenis.urgentie
            locked_melding.save()
            transaction.on_commit(
                lambda: urgentie_aangepast.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    vorige_urgentie=vorige_urgentie,
                )
            )

    def status_aanpassen(self, serializer, melding, db="default", heropen=False):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.taken.models import Taakgebeurtenis, Taakopdracht, Taakstatus

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik(
                    f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
                )

            vorige_status = locked_melding.status

            melding_gebeurtenis = serializer.save()

            locked_melding.afgesloten_op = None
            locked_melding.resolutie = None
            locked_melding.afhandelreden = None
            locked_melding.specificatie = None
            locked_melding.status = melding_gebeurtenis.status

            locked_taakopdrachten = None
            if locked_melding.status.is_afgesloten():
                try:
                    locked_taakopdrachten = (
                        locked_melding.taakopdrachten_voor_melding.all()
                        .select_for_update(nowait=True)
                        .filter(
                            afgesloten_op__isnull=True,
                            verwijderd_op__isnull=True,
                        )
                    )
                except OperationalError:
                    raise MeldingManager.TaakopdrachtInGebruik(
                        "Eén van taken is op dit moment in gebruik, probeer het later nog eens."
                    )
                taakgebeurtenissen = []
                for to in locked_taakopdrachten:
                    taakstatus = Taakstatus.objects.create(
                        naam=Taakstatus.NaamOpties.VOLTOOID, taakopdracht=to
                    )
                    to.status = taakstatus
                    to.resolutie = Taakopdracht.ResolutieOpties.GEANNULEERD
                    to.afgesloten_op = timezone.now()
                    if to.afgesloten_op and to.aangemaakt_op:
                        to.afhandeltijd = to.afgesloten_op - to.aangemaakt_op
                    else:
                        to.afhandeltijd = None
                    taakgebeurtenissen.append(
                        Taakgebeurtenis(
                            taakopdracht=to,
                            taakstatus=taakstatus,
                            resolutie=Taakgebeurtenis.ResolutieOpties.GEANNULEERD,
                            gebruiker=melding_gebeurtenis.gebruiker,
                        )
                    )
                Taakopdracht.objects.bulk_update(
                    locked_taakopdrachten,
                    ["status", "resolutie", "afgesloten_op", "afhandeltijd"],
                )
                aangemaakte_taakgebeurtenissen = Taakgebeurtenis.objects.bulk_create(
                    taakgebeurtenissen
                )
                meldinggebeurtenissen = [
                    Meldinggebeurtenis(
                        gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_STATUS_WIJZIGING,
                        taakgebeurtenis=taakgebeurtenis,
                        taakopdracht=taakgebeurtenis.taakopdracht,
                        melding=locked_melding,
                    )
                    for taakgebeurtenis in aangemaakte_taakgebeurtenissen
                ]
                Meldinggebeurtenis.objects.bulk_create(meldinggebeurtenissen)

                afgesloten_op = timezone.now()

                locked_melding.afgesloten_op = afgesloten_op
                locked_melding.resolutie = melding_gebeurtenis.resolutie
                locked_melding.afhandelreden = melding_gebeurtenis.afhandelreden
                locked_melding.specificatie = melding_gebeurtenis.specificatie

                melding_gebeurtenis.aangemaakt_op = afgesloten_op
                melding_gebeurtenis.save()

            locked_melding.save()

            transaction.on_commit(
                lambda: status_aangepast.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    status=melding_gebeurtenis.status,
                    vorige_status=vorige_status,
                    taakopdrachten=locked_taakopdrachten,
                )
            )

    def gebeurtenis_toevoegen(
        self, serializer, melding, db="default", gebeurtenis_type=None
    ):
        from apps.meldingen.models import Melding

        if melding.afgesloten_op:
            raise MeldingManager.MeldingAfgeslotenFout(
                f"Voor een afgesloten melding kunnen geen gebeurtenissen worden aangemaakt. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
            )

        with transaction.atomic():
            locked_melding = melding

            if locatie := serializer.validated_data.get("locatie"):
                locatie["melding"] = locked_melding
                locked_melding.locaties_voor_melding.update(primair=False)
                max_gewicht = locked_melding.locaties_voor_melding.aggregate(
                    Max("gewicht")
                )["gewicht__max"]
                gewicht = (
                    round(max_gewicht + 0.1, 2) if max_gewicht is not None else 0.2
                )
                locatie["gewicht"] = gewicht
                locatie["primair"] = True

            meldinggebeurtenis = serializer.save(
                melding=locked_melding, locatie=locatie
            )
            if gebeurtenis_type is not None:
                meldinggebeurtenis.gebeurtenis_type = gebeurtenis_type
                meldinggebeurtenis.save()

            if meldinggebeurtenis.locatie or (
                not locked_melding.thumbnail_afbeelding and meldinggebeurtenis.bijlagen
            ):
                try:
                    locked_melding = (
                        Melding.objects.using(db)
                        .select_for_update(nowait=True)
                        .get(pk=melding.pk)
                    )
                except OperationalError:
                    raise MeldingManager.MeldingInGebruik(
                        f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
                    )
                if (
                    not locked_melding.thumbnail_afbeelding
                    and meldinggebeurtenis.bijlagen
                ):
                    locked_melding.thumbnail_afbeelding = (
                        meldinggebeurtenis.bijlagen.last()
                    )
                if meldinggebeurtenis.locatie:
                    locked_melding.referentie_locatie = meldinggebeurtenis.locatie
                locked_melding.save()

            transaction.on_commit(
                lambda: gebeurtenis_toegevoegd.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    meldinggebeurtenis=meldinggebeurtenis,
                )
            )

    def melding_verwijderen(self, melding, db="default"):
        from apps.bijlagen.models import Bijlage
        from apps.meldingen.models import Melding
        from django.contrib.admin.utils import NestedObjects

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik(
                    f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
                )
            melding_url = locked_melding.get_absolute_url()

            collector = NestedObjects(using=db)
            collector.collect([locked_melding])
            alle_bestands_paden = [
                pad
                for model, instance in collector.data.items()
                if model == Bijlage
                for i in list(instance)
                for pad in i.bijlage_paded()
            ]
            samenvatting = locked_melding.delete()

            transaction.on_commit(
                lambda: verwijderd.send_robust(
                    sender=self.__class__,
                    melding_url=melding_url,
                    bijlage_paden=alle_bestands_paden,
                    samenvatting=samenvatting,
                )
            )

        return True

    def taakopdracht_aanmaken(self, serializer, melding, request, db="default"):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status
        from apps.taken.models import Taakgebeurtenis, Taakstatus

        if melding.afgesloten_op or melding.status.is_gepauzeerd():
            raise MeldingManager.MeldingAfgeslotenFout(
                f"Voor een afgesloten of gepauzeerde melding kunnen geen taken worden aangemaakt. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
            )

        with transaction.atomic():
            locked_melding = melding

            taak_data = {}
            taak_data.update(serializer.validated_data)
            # taakr_taaktype_url = Applicatie.vind_applicatie_obv_uri(
            #     taak_data.get("taakr_taaktype_url", "")  # requires implementation
            # )

            taakapplicatie = Applicatie.vind_applicatie_obv_uri(
                taak_data.get("taaktype", "")
            )

            if not taakapplicatie:
                raise Applicatie.ApplicatieWerdNietGevondenFout(
                    f"De applicatie voor dit taaktype kon niet worden gevonden: taaktype={taak_data.get('taaktype', '')}"
                )
            gebruiker = serializer.validated_data.pop("gebruiker", None)
            # We might want to include the taaktypeapplicatie taaktype url as well.
            taakopdracht = serializer.save(
                applicatie=taakapplicatie,
                melding=melding,
            )
            taakstatus_instance = Taakstatus(
                taakopdracht=taakopdracht,
            )
            taakstatus_instance.save()

            taakopdracht.status = taakstatus_instance
            taakopdracht.save()

            bericht = (
                serializer.validated_data.get("bericht")
                if serializer.validated_data.get("bericht")
                else ""
            )
            taakgebeurtenis_instance = Taakgebeurtenis(
                taakopdracht=taakopdracht,
                taakstatus=taakstatus_instance,
                omschrijving_intern=bericht,
                gebruiker=gebruiker,
            )
            taakgebeurtenis_instance.save()

            melding_gebeurtenis = Meldinggebeurtenis(
                melding=melding,
                gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_AANGEMAAKT,
                taakopdracht=taakopdracht,
                taakgebeurtenis=taakgebeurtenis_instance,
                gebruiker=gebruiker,
            )

            # zet status van de melding naar in_behandeling als dit niet de huidige status is
            if melding.status.naam != Status.NaamOpties.IN_BEHANDELING:
                try:
                    locked_melding = (
                        Melding.objects.using(db)
                        .select_for_update(nowait=True)
                        .get(pk=melding.pk)
                    )
                except OperationalError:
                    raise MeldingManager.MeldingInGebruik(
                        f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
                    )
                status_instance = Status(naam=Status.NaamOpties.IN_BEHANDELING)
                status_instance.melding = locked_melding
                status_instance.save()
                locked_melding.status = status_instance
                melding_gebeurtenis.status = status_instance
                melding_gebeurtenis.omschrijving_extern = (
                    "De melding is in behandeling."
                )
                melding_gebeurtenis.gebeurtenis_type = (
                    Meldinggebeurtenis.GebeurtenisType.STATUS_WIJZIGING
                )
                locked_melding.save()

            melding_gebeurtenis.save()
            transaction.on_commit(
                lambda: taakopdracht_aangemaakt.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    taakopdracht=taakopdracht,
                    taakgebeurtenis=taakgebeurtenis_instance,
                )
            )

        return taakopdracht

    def taakopdracht_notificatie(
        self,
        taakopdracht,
        data,
        db="default",
    ):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status
        from apps.taken.models import Taakopdracht
        from apps.taken.serializers import TaakopdrachtNotificatieSaveSerializer

        serializer = TaakopdrachtNotificatieSaveSerializer(
            data=data,
        )
        if not serializer.is_valid():
            logger.warning(
                f"taakopdracht_notificatie: serializer.errors={serializer.errors}"
            )
            return

        if taakopdracht.taakgebeurtenissen_voor_taakopdracht.filter(
            aangemaakt_op=serializer.validated_data.get("aangemaakt_op")
        ):
            logger.warning("taakopdracht_notificatie: deze Taakgebeurtenis bestaat al")
            return

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=taakopdracht.melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik(
                    f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {taakopdracht.melding.id}, melding uuid: {taakopdracht.melding.uuid}"
                )
            try:
                locked_taakopdracht = (
                    Taakopdracht.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=taakopdracht.pk)
                )
            except OperationalError:
                raise MeldingManager.TaakopdrachtInGebruik(
                    f"De taak is op dit moment in gebruik, probeer het later nog eens. melding nummer: {taakopdracht.id}, melding uuid: {taakopdracht.uuid}"
                )

            taakgebeurtenis_aangemaakt_op = serializer.validated_data.pop(
                "aangemaakt_op", timezone.now()
            )
            resolutie_opgelost_herzien = serializer.validated_data.pop(
                "resolutie_opgelost_herzien", False
            )
            taakgebeurtenis = serializer.save(
                taakopdracht=locked_taakopdracht,
            )
            if not locked_melding.thumbnail_afbeelding and taakgebeurtenis.bijlagen:
                locked_melding.thumbnail_afbeelding = taakgebeurtenis.bijlagen.last()
                locked_melding.save()

            taakgebeurtenis.aangemaakt_op = taakgebeurtenis_aangemaakt_op
            taakgebeurtenis.save()

            laatste_taakgebeurtenis_voor_taak = (
                locked_taakopdracht.taakgebeurtenissen_voor_taakopdracht.order_by(
                    "aangemaakt_op"
                ).last()
            )
            if (
                laatste_taakgebeurtenis_voor_taak == taakgebeurtenis
                and taakgebeurtenis.taakstatus
            ):
                locked_taakopdracht.status = taakgebeurtenis.taakstatus
                if locked_taakopdracht.is_voltooid:
                    locked_taakopdracht.afgesloten_op = taakgebeurtenis_aangemaakt_op
                    locked_taakopdracht.valideer_en_set_resolutie(
                        taakgebeurtenis.resolutie
                    )
                locked_taakopdracht.save()

            # Heropenen van melding
            if locked_melding.status.is_afgesloten() and resolutie_opgelost_herzien:
                melding_gebeurtenis_heropenen = Meldinggebeurtenis(
                    melding=locked_melding,
                    gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.MELDING_HEROPEND,
                    gebruiker=taakgebeurtenis.gebruiker,
                    omschrijving_intern=f"Melding heropend wegens niet kunnen oplossen van taak door externe instantie: {taakgebeurtenis.omschrijving_intern}",
                )
                # Heropenen melding.
                status_instance = Status(naam=Status.NaamOpties.OPENSTAAND)
                status_instance.melding = locked_melding
                status_instance.save()
                locked_melding.status = status_instance
                locked_melding.afgesloten_op = None
                melding_gebeurtenis_heropenen.status = status_instance
                melding_gebeurtenis_heropenen.save()
                melding_gebeurtenis_heropenen.aangemaakt_op = (
                    taakgebeurtenis_aangemaakt_op
                )
                melding_gebeurtenis_heropenen.save(update_fields=["aangemaakt_op"])
                locked_melding.save()

            melding_gebeurtenis = Meldinggebeurtenis(
                melding=locked_melding,
                gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_STATUS_WIJZIGING
                if taakgebeurtenis.taakstatus
                else Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_NOTIFICATIE,
                taakopdracht=locked_taakopdracht,
                taakgebeurtenis=taakgebeurtenis,
                gebruiker=taakgebeurtenis.gebruiker,
            )

            # zet status van de melding naar in_behandeling als dit niet de huidige status is
            if not locked_melding.actieve_taakopdrachten:
                status_instance = Status(naam=Status.NaamOpties.CONTROLE)
                status_instance.melding = locked_melding
                status_instance.save()
                locked_melding.status = status_instance
                melding_gebeurtenis.status = status_instance
                melding_gebeurtenis.gebeurtenis_type = (
                    Meldinggebeurtenis.GebeurtenisType.STATUS_WIJZIGING
                )
                locked_melding.save()

            melding_gebeurtenis.save()
            melding_gebeurtenis.aangemaakt_op = taakgebeurtenis_aangemaakt_op
            melding_gebeurtenis.save(update_fields=["aangemaakt_op"])

            transaction.on_commit(
                lambda: taakopdracht_notificatie.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    taakopdracht=locked_taakopdracht,
                    taakgebeurtenis=taakgebeurtenis,
                )
            )
        return taakgebeurtenis

    def taakopdracht_verwijderen(
        self,
        taakopdracht,
        gebruiker,
        db="default",
    ):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status
        from apps.taken.models import Taakgebeurtenis, Taakopdracht

        with transaction.atomic():
            try:
                locked_taakopdracht = (
                    Taakopdracht.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=taakopdracht.pk)
                )
            except OperationalError:
                raise MeldingManager.TaakopdrachtInGebruik(
                    f"De taak is op dit moment in gebruik, probeer het later nog eens. melding nummer: {taakopdracht.id}, melding uuid: {taakopdracht.uuid}"
                )

            locked_melding = locked_taakopdracht.melding
            now = timezone.now()

            taakgebeurtenis = Taakgebeurtenis(
                taakopdracht=locked_taakopdracht,
                gebruiker=nh3.clean(gebruiker),
                verwijderd_op=now,
                afgesloten_op=now,
            )
            taakgebeurtenis.save()

            locked_taakopdracht.verwijderd_op = now

            melding_gebeurtenis = Meldinggebeurtenis(
                melding=taakopdracht.melding,
                gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_VERWIJDERD,
                taakopdracht=locked_taakopdracht,
                taakgebeurtenis=taakgebeurtenis,
                gebruiker=taakgebeurtenis.gebruiker,
            )

            # zet status van de melding naar in_behandeling als dit niet de huidige status is
            locked_taakopdracht.save(update_fields=["verwijderd_op"])

            if not taakopdracht.melding.actieve_taakopdrachten:
                try:
                    locked_melding = (
                        Melding.objects.using(db)
                        .select_for_update(nowait=True)
                        .get(pk=taakopdracht.melding.pk)
                    )
                except OperationalError:
                    raise MeldingManager.MeldingInGebruik(
                        f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {taakopdracht.melding.id}, melding uuid: {taakopdracht.melding.uuid}"
                    )
                status_instance = Status(naam=Status.NaamOpties.CONTROLE)
                status_instance.melding = locked_melding
                status_instance.save()
                locked_melding.status = status_instance
                melding_gebeurtenis.status = status_instance
                melding_gebeurtenis.gebeurtenis_type = (
                    Meldinggebeurtenis.GebeurtenisType.STATUS_WIJZIGING
                )
                locked_melding.save()

            melding_gebeurtenis.save()

            transaction.on_commit(
                lambda: taakopdracht_verwijderd.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    taakopdracht=locked_taakopdracht,
                    taakgebeurtenis=taakgebeurtenis,
                )
            )
        return taakgebeurtenis

    def taakopdracht_status_aanpassen(
        self,
        serializer,
        taakopdracht,
        request,
        db="default",
        externr_niet_opgelost=False,
    ):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status
        from apps.taken.models import Taakopdracht, Taakstatus

        if taakopdracht.afgesloten_op and not externr_niet_opgelost:
            raise MeldingManager.TaakopdrachtAfgeslotenFout(
                "De status van een afgsloten taakopdracht kan niet meer worden veranderd"
            )

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=taakopdracht.melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik(
                    f"De melding is op dit moment in gebruik, probeer het later nog eens. melding nummer: {taakopdracht.melding.id}, melding uuid: {taakopdracht.melding.uuid}"
                )
            try:
                locked_taakopdracht = (
                    Taakopdracht.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=taakopdracht.pk)
                )
            except OperationalError:
                raise MeldingManager.TaakopdrachtInGebruik(
                    f"De taak is op dit moment in gebruik, probeer het later nog eens. melding nummer: {taakopdracht.id}, melding uuid: {taakopdracht.uuid}"
                )
            resolutie = serializer.validated_data.pop("resolutie", None)
            taakgebeurtenis = serializer.save(
                taakopdracht=locked_taakopdracht,
            )

            locked_taakopdracht.status = taakgebeurtenis.taakstatus
            if locked_taakopdracht.status.naam in [
                Taakstatus.NaamOpties.VOLTOOID_MET_FEEDBACK,
                Taakstatus.NaamOpties.VOLTOOID,
            ]:
                locked_taakopdracht.afgesloten_op = timezone.now()
                if resolutie in [ro[0] for ro in Taakopdracht.ResolutieOpties.choices]:
                    locked_taakopdracht.resolutie = resolutie
                    taakgebeurtenis.resolutie = resolutie
                    taakgebeurtenis.save()

            # Heropenen van melding
            if locked_melding.status.is_afgesloten() and externr_niet_opgelost:
                melding_gebeurtenis_heropenen = Meldinggebeurtenis(
                    melding=locked_melding,
                    gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.MELDING_HEROPEND,
                    gebruiker=taakgebeurtenis.gebruiker,
                    omschrijving_intern=f"Melding heropend wegens niet kunnen oplossen van taak door externe instantie: {taakgebeurtenis.omschrijving_intern}",
                )
                # Heropenen melding.
                status_instance = Status(naam=Status.NaamOpties.OPENSTAAND)
                status_instance.melding = locked_melding
                status_instance.save()
                locked_melding.status = status_instance
                locked_melding.afgesloten_op = None
                melding_gebeurtenis_heropenen.status = status_instance
                melding_gebeurtenis_heropenen.save()

            melding_gebeurtenis = Meldinggebeurtenis(
                melding=locked_melding,
                gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_STATUS_WIJZIGING,
                taakopdracht=locked_taakopdracht,
                taakgebeurtenis=taakgebeurtenis,
                gebruiker=taakgebeurtenis.gebruiker,
            )

            # zet status van de melding naar in_behandeling als dit niet de huidige status is
            locked_taakopdracht.save()

            if not locked_melding.actieve_taakopdrachten:
                status_instance = Status(naam=Status.NaamOpties.CONTROLE)
                status_instance.melding = locked_melding
                status_instance.save()
                locked_melding.status = status_instance
                melding_gebeurtenis.status = status_instance
                melding_gebeurtenis.gebeurtenis_type = (
                    Meldinggebeurtenis.GebeurtenisType.STATUS_WIJZIGING
                )

            melding_gebeurtenis.save()

            locked_melding.save()
            transaction.on_commit(
                lambda: taakopdracht_status_aangepast.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    taakopdracht=locked_taakopdracht,
                    taakgebeurtenis=taakgebeurtenis,
                )
            )

        return taakopdracht
