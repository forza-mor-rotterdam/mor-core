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
                for onderwerp in signaal.onderwerpen.all():
                    melding.onderwerpen.add(onderwerp)
                    onderwerp_response = OnderwerpenService().get_onderwerp(
                        onderwerp.bron_url
                    )
                    if onderwerp_response.get("priority") == "high":
                        melding.urgentie = 0.5

                for locatie in signaal.locaties_voor_signaal.all():
                    melding.locaties_voor_melding.add(locatie)

                status = Status()
                status.melding = melding
                status.save()

                melding.status = status
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
        from apps.taken.models import Taakgebeurtenis, Taakopdracht

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

            resolutie = serializer.validated_data.pop("resolutie", None)
            melding_gebeurtenis = serializer.save()

            locked_melding.afgesloten_op = None
            locked_melding.status = melding_gebeurtenis.status

            if locked_melding.status.is_afgesloten():
                try:
                    locked_taakopdrachten = (
                        locked_melding.taakopdrachten_voor_melding.all()
                        .select_for_update(nowait=True)
                        .filter(
                            afgesloten_op__isnull=True,
                        )
                    )
                except OperationalError:
                    raise MeldingManager.TaakopdrachtInGebruik(
                        "Eén van taken is op dit moment in gebruik, probeer het later nog eens."
                    )
                taakgebeurtenissen = []
                now = timezone.now()
                for to in locked_taakopdrachten:
                    to.verwijderd_op = now
                    to.afgesloten_op = now
                    if to.afgesloten_op and to.aangemaakt_op:
                        to.afhandeltijd = to.afgesloten_op - to.aangemaakt_op
                    else:
                        to.afhandeltijd = None
                    taakgebeurtenissen.append(
                        Taakgebeurtenis(
                            taakopdracht=to,
                            verwijderd_op=now,
                            afgesloten_op=now,
                            gebruiker=melding_gebeurtenis.gebruiker,
                        )
                    )
                Taakopdracht.objects.bulk_update(
                    locked_taakopdrachten,
                    ["verwijderd_op", "afgesloten_op", "afhandeltijd"],
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

                locked_melding.afgesloten_op = timezone.now()

            if resolutie in [ro[0] for ro in Melding.ResolutieOpties.choices]:
                locked_melding.resolutie = resolutie
            locked_melding.save()

            transaction.on_commit(
                lambda: status_aangepast.send_robust(
                    sender=self.__class__,
                    melding=locked_melding,
                    status=melding_gebeurtenis.status,
                    vorige_status=vorige_status,
                )
            )

    def gebeurtenis_toevoegen(self, serializer, melding, db="default"):
        from apps.meldingen.models import Melding

        if melding.afgesloten_op:
            raise MeldingManager.MeldingAfgeslotenFout(
                f"Voor een afgsloten melding kunnen geen gebeurtenissen worden aangemaakt. melding nummer: {melding.id}, melding uuid: {melding.uuid}"
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

            if locatie := serializer.validated_data.get("locatie"):
                locatie["melding"] = melding
                max_gewicht = melding.locaties_voor_melding.aggregate(Max("gewicht"))[
                    "gewicht__max"
                ]
                gewicht = (
                    round(max_gewicht + 0.1, 2) if max_gewicht is not None else 0.2
                )
                locatie["gewicht"] = gewicht

            meldinggebeurtenis = serializer.save(melding=melding, locatie=locatie)

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

            taak_data = {}
            taak_data.update(serializer.validated_data)
            # taakr_taaktype_url = Applicatie.vind_applicatie_obv_uri(
            #     taak_data.get("taakr_taaktype_url", "")  # requires implementation
            # )

            taakapplicatie_taaktype_url = Applicatie.vind_applicatie_obv_uri(
                taak_data.get("taaktype", "")
            )

            if not taakapplicatie_taaktype_url:
                raise Applicatie.ApplicatieWerdNietGevondenFout(
                    f"De applicatie voor dit taaktype kon niet worden gevonden: taaktype={taak_data.get('taaktype', '')}"
                )
            gebruiker = serializer.validated_data.pop("gebruiker", None)
            # We might want to include the taaktypeapplicatie taaktype url as well.
            taakopdracht = serializer.save(
                applicatie=taakapplicatie_taaktype_url,
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
                melding=locked_melding,
                gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_AANGEMAAKT,
                taakopdracht=taakopdracht,
                taakgebeurtenis=taakgebeurtenis_instance,
                gebruiker=gebruiker,
            )

            # zet status van de melding naar in_behandeling als dit niet de huidige status is
            if locked_melding.status.naam != Status.NaamOpties.IN_BEHANDELING:
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

            melding_gebeurtenis.save()
            locked_melding.save()
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
        serializer,
        db="default",
    ):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status
        from apps.taken.models import Taakopdracht, Taakstatus

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

            resolutie_opgelost_herzien = serializer.validated_data.pop(
                "resolutie_opgelost_herzien", False
            )
            taakgebeurtenis = serializer.save(
                taakopdracht=locked_taakopdracht,
            )
            resolutie = taakgebeurtenis.resolutie
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

            melding_gebeurtenis = Meldinggebeurtenis(
                melding=locked_melding,
                gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_STATUS_WIJZIGING,
                taakopdracht=locked_taakopdracht,
                taakgebeurtenis=taakgebeurtenis,
                gebruiker=taakgebeurtenis.gebruiker,
            )

            # zet status van de melding naar in_behandeling als dit niet de huidige status is
            locked_taakopdracht.save()

            if not locked_melding.actieve_taakopdrachten():
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

            now = timezone.now()

            taakgebeurtenis = Taakgebeurtenis(
                taakopdracht=locked_taakopdracht,
                gebruiker=nh3.clean(gebruiker),
                verwijderd_op=now,
                afgesloten_op=now,
            )
            taakgebeurtenis.save()

            locked_taakopdracht.verwijderd_op = now
            locked_taakopdracht.afgesloten_op = now

            melding_gebeurtenis = Meldinggebeurtenis(
                melding=locked_melding,
                gebeurtenis_type=Meldinggebeurtenis.GebeurtenisType.TAAKOPDRACHT_VERWIJDERD,
                taakopdracht=locked_taakopdracht,
                taakgebeurtenis=taakgebeurtenis,
                gebruiker=taakgebeurtenis.gebruiker,
            )

            # zet status van de melding naar in_behandeling als dit niet de huidige status is
            locked_taakopdracht.save()

            if not locked_melding.actieve_taakopdrachten():
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

            if not locked_melding.actieve_taakopdrachten():
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
