import logging

from apps.applicaties.models import Applicatie
from apps.services.onderwerpen import OnderwerpenService
from django.contrib.gis.db import models
from django.db import OperationalError, transaction
from django.db.models import Max
from django.dispatch import Signal as DjangoSignal
from django.utils import timezone
from rest_framework.reverse import reverse

logger = logging.getLogger(__name__)

signaal_aangemaakt = DjangoSignal()
status_aangepast = DjangoSignal()
urgentie_aangepast = DjangoSignal()
afgesloten = DjangoSignal()
gebeurtenis_toegevoegd = DjangoSignal()
taakopdracht_aangemaakt = DjangoSignal()
taakopdracht_status_aangepast = DjangoSignal()


class MeldingManager(models.Manager):
    class OnderwerpenNietValide(Exception):
        pass

    class StatusVeranderingNietToegestaan(Exception):
        pass

    class MeldingInGebruik(Exception):
        pass

    class TaakopdrachtInGebruik(Exception):
        pass

    class TaakVerwijderenFout(Exception):
        pass

    class TaakStatusAanpassenFout(Exception):
        pass

    class MeldingAfgeslotenFout(Exception):
        pass

    class TaakopdrachtAfgeslotenFout(Exception):
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
                        raise MeldingManager.MeldingInGebruik
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
                "De urgentie van een afgesloten melding kan niet meer worden veranderd"
            )

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik

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
        from apps.meldingen.models import Melding
        from apps.taken.models import Taakgebeurtenis, Taakopdracht, Taakstatus

        # Blocks the ability to reopen a melding so commented
        # if melding.afgesloten_op:
        #     raise MeldingManager.MeldingAfgeslotenFout(
        #         "De status van een afgesloten melding kan niet meer worden veranderd"
        #     )

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik

            vorige_status = locked_melding.status

            resolutie = serializer.validated_data.pop("resolutie", None)
            melding_gebeurtenis = serializer.save()

            locked_melding.status = melding_gebeurtenis.status

            # TODO: hoe willen we checken dat de melding afgehandeld wordt
            # Sluiten van melding en bijbehorende open taken. Zet afgesloten_op.
            # When reopening "openstaand" is the only volgende status.
            if (
                len(locked_melding.status.volgende_statussen()) == 1
                and locked_melding.status.volgende_statussen()[0] == "openstaand"
            ) or not locked_melding.status.volgende_statussen():
                try:
                    locked_taakopdrachten = (
                        Taakopdracht.objects.using(db)
                        .select_for_update(nowait=True)
                        .filter(
                            melding=locked_melding.pk,
                            resolutie__isnull=True,
                        )
                    )
                except OperationalError:
                    raise MeldingManager.TaakopdrachtInGebruik

                taak_urls = locked_taakopdrachten.values_list("taak_url", flat=True)
                for taak_url in taak_urls:
                    taakapplicatie = Applicatie.vind_applicatie_obv_uri(taak_url)
                    taak_status_aanpassen_data = {
                        "taakstatus": {"naam": "voltooid"},
                        "resolutie": "geannuleerd",
                        "bijlagen": [],
                        "gebruiker": melding_gebeurtenis.gebruiker,
                    }
                    response = taakapplicatie.taak_status_aanpassen(
                        f"{taak_url}status-aanpassen/",
                        data=taak_status_aanpassen_data,
                    )
                    if response.status_code not in [200, 404]:
                        raise MeldingManager.TaakStatusAanpassenFout
                taakgebeurtenissen = []
                for to in locked_taakopdrachten:
                    taakstatus = Taakstatus.objects.create(
                        naam="voltooid", taakopdracht=to
                    )
                    to.status = taakstatus
                    to.resolutie = "geannuleerd"
                    to.afgesloten_op = timezone.now()
                    taakgebeurtenissen.append(
                        Taakgebeurtenis(
                            taakopdracht=to,
                            taakstatus=taakstatus,
                            gebruiker=melding_gebeurtenis.gebruiker,
                        )
                    )
                Taakopdracht.objects.bulk_update(
                    locked_taakopdrachten, ["status", "resolutie"]
                )
                Taakgebeurtenis.objects.bulk_create(taakgebeurtenissen)

                locked_melding.afgesloten_op = timezone.now()
                if resolutie in [ro[0] for ro in Melding.ResolutieOpties.choices]:
                    locked_melding.resolutie = resolutie
            # When reopening melding set afgesloten op to None
            if heropen:
                locked_melding.afgesloten_op = None
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
                "Voor een afgsloten melding kunnen gebeurtenissen niet worden aangemaakt"
            )

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik

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

    def taakopdracht_aanmaken(self, serializer, melding, request, db="default"):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status
        from apps.taken.models import Taakgebeurtenis, Taakstatus

        if melding.afgesloten_op:
            raise MeldingManager.MeldingAfgeslotenFout(
                "Voor een afgsloten melding kunnen taakopdrachten niet worden aangemaakt"
            )

        with transaction.atomic():
            try:
                locked_melding = (
                    Melding.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=melding.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik

            taak_data = {}
            taak_data.update(serializer.validated_data)
            applicatie = Applicatie.vind_applicatie_obv_uri(
                taak_data.get("taaktype", "")
            )

            if not applicatie:
                raise Exception(
                    f"De applicatie kon niet worden gevonden op basis van dit taaktype: {taak_data.get('taaktype', '')}"
                )
            gebruiker = serializer.validated_data.pop("gebruiker", None)
            taakopdracht = serializer.save(
                applicatie=applicatie,
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
                else "Taak aangemaakt"
            )
            taakgebeurtenis_instance = Taakgebeurtenis(
                taakopdracht=taakopdracht,
                taakstatus=taakstatus_instance,
                omschrijving_intern=bericht,
                gebruiker=gebruiker,
            )
            taakgebeurtenis_instance.save()

            # verzamel taak aanmaken data voor taakapplicatie
            taakapplicatie_data = serializer.__class__(
                taakopdracht, context={"request": request}
            ).data
            taakapplicatie_data["melding"] = taakapplicatie_data.get("_links", {}).get(
                "melding"
            )
            taakapplicatie_data["taakopdracht"] = reverse(
                "v1:taakopdracht-detail",
                kwargs={"uuid": taakopdracht.uuid},
                request=request,
            )
            taakapplicatie_data["gebruiker"] = gebruiker
            taak_aanmaken_response = applicatie.taak_aanmaken(taakapplicatie_data)

            if taak_aanmaken_response.status_code == 201:
                taakopdracht.taak_url = (
                    taak_aanmaken_response.json().get("_links", {}).get("self")
                )
                taakopdracht.save()
            else:
                raise Exception(
                    f"De taak kon niet worden aangemaakt in de applicatie: {taak_aanmaken_response.status_code}"
                )

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
                    taakopdracht=taakopdracht,
                    melding=locked_melding,
                )
            )

        return taakopdracht

    def taakopdracht_status_aanpassen(
        self, serializer, taakopdracht, request, db="default"
    ):
        from apps.meldingen.models import Melding, Meldinggebeurtenis
        from apps.status.models import Status
        from apps.taken.models import Taakopdracht, Taakstatus

        if taakopdracht.afgesloten_op:
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
                locked_taakopdracht = (
                    Taakopdracht.objects.using(db)
                    .select_for_update(nowait=True)
                    .get(pk=taakopdracht.pk)
                )
            except OperationalError:
                raise MeldingManager.MeldingInGebruik

            resolutie = serializer.validated_data.pop("resolutie", None)
            uitvoerder = serializer.validated_data.pop("uitvoerder", None)
            taakgebeurtenis = serializer.save(
                taakopdracht=locked_taakopdracht,
                additionele_informatie={"uitvoerder": uitvoerder},
            )

            locked_taakopdracht.status = taakgebeurtenis.taakstatus
            if taakgebeurtenis.taakstatus.naam == Taakstatus.NaamOpties.TOEGEWEZEN:
                locked_taakopdracht.additionele_informatie = {"uitvoerder": uitvoerder}
            elif taakgebeurtenis.taakstatus.naam == Taakstatus.NaamOpties.OPENSTAAND:
                locked_taakopdracht.additionele_informatie["uitvoerder"] = None

            if not locked_taakopdracht.status.volgende_statussen():
                locked_taakopdracht.afgesloten_op = timezone.now()
                if resolutie in [ro[0] for ro in Taakopdracht.ResolutieOpties.choices]:
                    locked_taakopdracht.resolutie = resolutie

            taak_status_aanpassen_data = {
                "taakstatus": {"naam": taakgebeurtenis.taakstatus.naam},
                "bijlagen": [
                    reverse(
                        "v1:bijlage-detail",
                        kwargs={"uuid": bijlage.uuid},
                        request=request,
                    )
                    for bijlage in taakgebeurtenis.bijlagen.all()
                ],
                "resolutie": resolutie,
                "omschrijving_intern": taakgebeurtenis.omschrijving_intern,
                "gebruiker": taakgebeurtenis.gebruiker,
                "uitvoerder": uitvoerder,
            }
            taak_status_aanpassen_response = (
                locked_taakopdracht.applicatie.taak_status_aanpassen(
                    f"{locked_taakopdracht.taak_url}status-aanpassen/",
                    data=taak_status_aanpassen_data,
                )
            )

            if taak_status_aanpassen_response.status_code not in [200, 404]:
                raise Exception(
                    f"De taakstatus kon niet worden aangepast: {locked_taakopdracht.taak_url}status-aanpassen/"
                )

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
