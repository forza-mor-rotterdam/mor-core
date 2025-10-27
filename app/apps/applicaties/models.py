import logging
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from mor_api_services import SignaalapplicatieService, TaakapplicatieService
from utils.models import BasisModel

logger = logging.getLogger(__name__)


def encrypt_gebruiker_wachtwoord(wachtwoord_decrypted):
    f = Fernet(settings.FERNET_KEY)
    try:
        wachtwoord_encrypted = f.encrypt(wachtwoord_decrypted.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption with fernet key error: {e}")
    return wachtwoord_encrypted


class Applicatie(BasisModel):
    """
    Representeerd externe applicaite die de afhandling van de melden op zich nemen.
    """

    class ApplicatieTypes(models.TextChoices):
        TAAKAPPLICATIE = "taakapplicatie", "Taakapplicatie"
        SIGNAALAPPLICATIE = "signaalapplicatie", "Signaalapplicatie"

    naam = models.CharField(
        max_length=100,
        default="Applicatie",
    )
    basis_url = models.URLField(
        blank=True,
        null=True,
    )
    valide_basis_urls = ArrayField(
        base_field=models.URLField(),
        default=list,
    )
    gebruiker = models.ForeignKey(
        to=get_user_model(),
        related_name="applicaties_voor_gebruiker",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    applicatie_gebruiker_naam = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )
    applicatie_gebruiker_wachtwoord = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    applicatie_gebruiker_token_timeout = models.PositiveIntegerField(
        default=60 * 60,
    )
    applicatie_type = models.CharField(
        default=ApplicatieTypes.TAAKAPPLICATIE,
        choices=ApplicatieTypes.choices,
    )
    stuur_notificatie_melding_afgesloten = models.BooleanField(
        default=False,
        help_text="Deze notificatie is alleen van toepassing op signaalapplicaties",
    )
    stuur_notificatie_melding_veranderd = models.BooleanField(
        default=False,
        help_text="Deze notificatie is alleen van toepassing op taakapplicaties",
    )

    def api_service(self):
        f = Fernet(settings.FERNET_KEY)
        init_kwargs = {
            "basis_url": self.basis_url,
            "gebruikersnaam": self.applicatie_gebruiker_naam,
            "wachtwoord": f.decrypt(self.applicatie_gebruiker_wachtwoord).decode(),
            "token_timeout": self.applicatie_gebruiker_token_timeout,
        }
        if self.applicatie_type == Applicatie.ApplicatieTypes.TAAKAPPLICATIE:
            return TaakapplicatieService(**init_kwargs)
        if self.applicatie_type == Applicatie.ApplicatieTypes.SIGNAALAPPLICATIE:
            return SignaalapplicatieService(**init_kwargs)
        return None

    def __str__(self):
        return self.naam

    class ApplicatieWerdNietGevondenFout(Exception):
        ...

    @classmethod
    def vind_applicatie_obv_uri(cls, uri):
        url_o = urlparse(uri)
        applicaties = Applicatie.objects.filter(
            basis_url=f"{url_o.scheme}://{url_o.netloc}"
        )
        if not applicaties:
            applicaties = Applicatie.objects.filter(
                valide_basis_urls__contains=[f"{url_o.scheme}://{url_o.netloc}"]
            )
        if not applicaties:
            raise Applicatie.ApplicatieWerdNietGevondenFout(
                f"De applicatie voor deze uri kon niet worden gevonden: uri={uri}"
            )
        return applicaties[0]

    def encrypt_applicatie_gebruiker_wachtwoord(self, wachtwoord_decrypted):
        self.applicatie_gebruiker_wachtwoord = encrypt_gebruiker_wachtwoord(
            wachtwoord_decrypted
        )

    def haal_token(self):
        api_service = self.api_service()
        api_service_call = getattr(api_service, "haal_token", None)
        if callable(api_service_call):
            return api_service_call()
        return None

    def melding_veranderd_notificatie_voor_applicatie(
        self, melding_url, notificatie_type
    ):
        if not self.stuur_notificatie_melding_veranderd:
            return {}
        api_service = self.api_service()
        api_service_call = getattr(
            api_service, "melding_veranderd_notificatie_voor_applicatie", None
        )
        if callable(api_service_call):
            response = api_service_call(
                melding_url=melding_url,
                notificatie_type=notificatie_type,
            )
            return response
        logger.warning(
            f"API Service({api_service}) heeft geen methode 'melding_veranderd_notificatie_voor_applicatie'"
        )
        return {}

    def taak_aanmaken(self, data):
        api_service = self.api_service()
        api_service_call = getattr(api_service, "taak_aanmaken", None)
        if callable(api_service_call):
            return api_service_call(data=data)

        logger.warning(f"API Service({api_service}) heeft geen methode 'taak_aanmaken'")
        return {}

    def taak_verwijderen(self, url, gebruiker=None):
        api_service = self.api_service()
        api_service_call = getattr(api_service, "taak_verwijderen", None)
        if callable(api_service_call):
            return api_service_call(url, gebruiker=gebruiker)

        logger.warning(
            f"API Service({api_service}) heeft geen methode 'taak_verwijderen'"
        )
        return {}

    def taak_status_aanpassen(self, url, data):
        api_service = self.api_service()
        api_service_call = getattr(api_service, "taak_status_aanpassen", None)
        if callable(api_service_call):
            return api_service_call(url, data=data)

        logger.warning(
            f"API Service({api_service}) heeft geen methode 'taak_status_aanpassen'"
        )
        return {}

    def notificatie_melding_afgesloten(self, signaal_url):
        if not self.stuur_notificatie_melding_afgesloten:
            return {}
        api_service = self.api_service()
        api_service_call = getattr(api_service, "notificatie_melding_afgesloten", None)
        if callable(api_service_call):
            return api_service_call(signaal_url)

        logger.warning(
            f"API Service({api_service}) heeft geen methode 'notificatie_melding_afgesloten'"
        )
        return {}
