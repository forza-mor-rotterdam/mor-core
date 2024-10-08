import logging
from urllib.parse import urlencode, urlparse

import requests
import urllib3
from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from requests import Request, Response
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

    def __str__(self):
        return self.naam

    class ApplicationAuthResponseException(Exception):
        ...

    class ApplicatieBasisUrlFout(Exception):
        ...

    class ApplicatieWerdNietGevondenFout(Exception):
        ...

    class NotificatieVoorApplicatieFout(Exception):
        ...

    class TaaktypesOphalenFout(Exception):
        ...

    class AntwoordFout(Exception):
        ...

    @classmethod
    def vind_applicatie_obv_uri(cls, uri):
        url_o = urlparse(uri)
        applicatie = Applicatie.objects.filter(
            basis_url=f"{url_o.scheme}://{url_o.netloc}"
        ).first()
        if not applicatie:
            applicatie = Applicatie.objects.filter(
                valide_basis_urls__contains=[f"{url_o.scheme}://{url_o.netloc}"]
            ).first()
        if not applicatie:
            logger.warning(f"Er is geen Applicatie gevonden bij deze url: url={uri}")
        return applicatie

    def encrypt_applicatie_gebruiker_wachtwoord(self, wachtwoord_decrypted):
        self.applicatie_gebruiker_wachtwoord = encrypt_gebruiker_wachtwoord(
            wachtwoord_decrypted
        )

    def _get_timeout(self):
        return (10, 20)

    def get_token_cache_key(self):
        return f"applicatie_{self.uuid}_token"

    def _get_token(self):
        f = Fernet(settings.FERNET_KEY)
        applicatie_token = cache.get(self.get_token_cache_key())
        if (
            not applicatie_token
            and self.applicatie_gebruiker_naam
            and self.applicatie_gebruiker_wachtwoord
        ):
            json_data = {
                "username": self.applicatie_gebruiker_naam,
                "password": f.decrypt(self.applicatie_gebruiker_wachtwoord).decode(),
            }
            token_response = None
            try:
                token_response = requests.post(
                    f"{self.basis_url}{settings.TOKEN_API_RELATIVE_URL}",
                    json=json_data,
                    headers={
                        "user-agent": urllib3.util.SKIP_HEADER,
                    },
                )
            except Exception as e:
                logger.error(f"Token request mislukt: e: {e}")

            if token_response and token_response.status_code == 200:
                applicatie_token = token_response.json().get("token")
                cache.set(
                    self.get_token_cache_key(),
                    applicatie_token,
                    settings.MELDINGEN_TOKEN_TIMEOUT,
                )
            elif token_response:
                logger.error(
                    f"Token request mislukt: status code: {token_response.status_code}, text: {token_response.text}"
                )

        return applicatie_token

    def _get_url(self, url):
        url_o = urlparse(url)
        if not url_o.scheme and not url_o.netloc:
            nieuwe_url = f"{self.basis_url}{url}"
            return nieuwe_url
        if (
            f"{url_o.scheme}://{url_o.netloc}" == self.basis_url
            or f"{url_o.scheme}://{url_o.netloc}" in self.valide_basis_urls
        ):
            nieuwe_url = (
                f"{self.basis_url}{url_o.path}{'?' if url_o.query else ''}{url_o.query}"
            )
            return nieuwe_url
        raise Applicatie.ApplicatieBasisUrlFout(
            f"url: {url}, basis_url: {self.basis_url}"
        )

    def _get_headers(self):
        token = self._get_token()
        headers = {
            "user-agent": urllib3.util.SKIP_HEADER,
        }
        if token:
            headers.update(
                {
                    "Authorization": f"Token {token}",
                }
            )
        return headers

    def _do_request(
        self, url, method="get", data={}, params={}, raw_response=True, cache_timeout=0
    ):
        action: Request = getattr(requests, method)
        url = self._get_url(url)
        action_params: dict = {
            "url": url,
            "headers": self._get_headers(),
            "json": data,
            "params": params,
            "timeout": self._get_timeout(),
        }
        if cache_timeout and method == "get":
            cache_key = f"{url}?{urlencode(params)}"
            response = cache.get(cache_key)
            if not response:
                try:
                    response: Response = action(**action_params)
                except Exception as e:
                    logger.error(f"error: {e}")
                    raise Applicatie.AntwoordFout(
                        f"Er is iets mis gegaan met de verbinding tussen MOR-Core en {self.naam}"
                    )
                if int(response.status_code) == 200:
                    cache.set(cache_key, response, cache_timeout)
        else:
            try:
                response: Response = action(**action_params)
            except Exception as e:
                logger.error(f"error: {e}")
                raise Applicatie.AntwoordFout(
                    f"Er is iets mis gegaan met de verbinding tussen MOR-Core en {self.naam}"
                )
        if raw_response:
            return response
        return response.json()

    def melding_veranderd_notificatie_voor_applicatie(
        self, melding_url, notificatie_type
    ):
        return self._do_request(
            settings.MELDING_VERANDERD_NOTIFICATIE_URL,
            params={
                "melding_url": melding_url,
                "notificatie_type": notificatie_type,
            },
        )

    def taak_aanmaken(self, data):
        return self._do_request("/api/v1/taak/", method="post", data=data)

    def taak_verwijderen(self, url, gebruiker=None):
        return self._do_request(url, method="delete", params={"gebruiker": gebruiker})

    def taaktypes_halen(self, cache_timeout=60):
        if self.basis_url:
            taaktypes_response = self._do_request(
                "/api/v1/taaktype/",
                params={"limit": 200},
                method="get",
                cache_timeout=cache_timeout,
            )
            if taaktypes_response.status_code == 200:
                return taaktypes_response.json().get("results", [])
            if taaktypes_response.status_code == 404:
                error = f"De taaktypes voor {self.naam} konden niet worden opgehaald: fout code={taaktypes_response.status_code}"
            elif taaktypes_response.status_code != 200:
                try:
                    error = f"De taaktypes voor {self.naam} konden niet worden opgehaald: fout code={taaktypes_response.status_code}, antwoord={taaktypes_response.json().get('detail', taaktypes_response.json())}"
                except Exception:
                    error = f"De taaktypes voor {self.naam} konden niet worden opgehaald: fout code={taaktypes_response.status_code}"
                logger.error(error)
                raise Applicatie.TaaktypesOphalenFout(error)

        else:
            error = f"taaktypes voor applicatie '{self.naam}' konden niet worden opgehaald: basis_url ontbreekt"
        logger.error(error)
        return []

    def fetch_taaktype_data(self, url):
        try:
            response = self._do_request(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching taaktype data from {url}: {e}")
            return None

    def taak_status_aanpassen(self, url, data):
        return self._do_request(url, method="patch", data=data)

    def notificatie_melding_afgesloten(self, signaal_uri):
        melding_afgesloten_url = f"{signaal_uri}melding-afgesloten/"
        response = self._do_request(melding_afgesloten_url)
        if response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                logger.warning(
                    f"Melding is waarschijnlijk goed afgesloten, maar response is niet van het type json: url='{melding_afgesloten_url}', response tekst={response.text}, error={e}"
                )

        if response.status_code == 404:
            logger.warning(
                f"Melding kon niet worden afgesloten, vermoedelijk ondersteund de applicatie 'melding afgesloten' niet. url='{melding_afgesloten_url}', status code={response.status_code}, response tekst={response.text}"
            )

        logger.error(
            f"Melding kon niet worden afgesloten. '{melding_afgesloten_url}', status code: {response.status_code}, response tekst={response.text}"
        )
