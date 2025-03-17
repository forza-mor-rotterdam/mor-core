from datetime import datetime, timedelta

import requests_mock
from apps.aliassen.models import OnderwerpAlias
from apps.applicaties.models import Applicatie
from apps.bijlagen.models import Bijlage
from apps.instellingen.models import Instelling
from apps.locatie.models import Adres
from apps.meldingen.models import Melding
from apps.status.models import Status
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils.timezone import get_current_timezone, make_aware
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APITestCase
from utils.unittest_helpers import get_authenticated_client, get_unauthenticated_client

B64_FILE = "e1xydGYxXGFuc2lcYW5zaWNwZzEyNTJcY29jb2FydGYyNTgwClxjb2NvYXRleHRzY2FsaW5nMFxjb2NvYXBsYXRmb3JtMHtcZm9udHRibFxmMFxmc3dpc3NcZmNoYXJzZXQwIEhlbHZldGljYTt9CntcY29sb3J0Ymw7XHJlZDI1NVxncmVlbjI1NVxibHVlMjU1O30Ke1wqXGV4cGFuZGVkY29sb3J0Ymw7O30KXHBhcGVydzExOTAwXHBhcGVyaDE2ODQwXG1hcmdsMTQ0MFxtYXJncjE0NDBcdmlld3cxMTUyMFx2aWV3aDg0MDBcdmlld2tpbmQwClxwYXJkXHR4NTY2XHR4MTEzM1x0eDE3MDBcdHgyMjY3XHR4MjgzNFx0eDM0MDFcdHgzOTY4XHR4NDUzNVx0eDUxMDJcdHg1NjY5XHR4NjIzNlx0eDY4MDNccGFyZGlybmF0dXJhbFxwYXJ0aWdodGVuZmFjdG9yMAoKXGYwXGZzMjQgXGNmMCBUZXN0IGZpbGV9Cg=="
B64_IMAGE = "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"
MOCK_URL = "https://mock.com"


class SignaalApiTest(APITestCase):
    b64_file = "e1xydGYxXGFuc2lcYW5zaWNwZzEyNTJcY29jb2FydGYyNTgwClxjb2NvYXRleHRzY2FsaW5nMFxjb2NvYXBsYXRmb3JtMHtcZm9udHRibFxmMFxmc3dpc3NcZmNoYXJzZXQwIEhlbHZldGljYTt9CntcY29sb3J0Ymw7XHJlZDI1NVxncmVlbjI1NVxibHVlMjU1O30Ke1wqXGV4cGFuZGVkY29sb3J0Ymw7O30KXHBhcGVydzExOTAwXHBhcGVyaDE2ODQwXG1hcmdsMTQ0MFxtYXJncjE0NDBcdmlld3cxMTUyMFx2aWV3aDg0MDBcdmlld2tpbmQwClxwYXJkXHR4NTY2XHR4MTEzM1x0eDE3MDBcdHgyMjY3XHR4MjgzNFx0eDM0MDFcdHgzOTY4XHR4NDUzNVx0eDUxMDJcdHg1NjY5XHR4NjIzNlx0eDY4MDNccGFyZGlybmF0dXJhbFxwYXJ0aWdodGVuZmFjdG9yMAoKXGYwXGZzMjQgXGNmMCBUZXN0IGZpbGV9Cg=="
    signaal_data = {
        "signaal_url": MOCK_URL,
        "bron_id": "mock_bron_id",
        "bron_signaal_id": "mock_bron_signaal_id",
        "melder": {
            "naam": "string",
            "email": "user@example.com",
            "telefoonnummer": "string",
        },
        "origineel_aangemaakt": "2023-03-09T11:56:04.036Z",
        "onderwerpen": [{"bron_url": MOCK_URL}],
        "omschrijving_melder": "string",
        "aanvullende_informatie": "string",
        "aanvullende_vragen": [
            {
                "question": "Wat voor grofvuil ligt er?",
                "answers": ["Karton", "Iets anders"],
            },
            {"question": "Waar ligt het grofvuil?", "answers": ["Op straat"]},
        ],
        "meta": {
            "additionalProp1": "string",
            "additionalProp2": "string",
            "additionalProp3": "string",
        },
        "meta_uitgebreid": {},
        "adressen": [
            {
                "plaatsnaam": "Rotterdam",
                "straatnaam": "Coolsingel",
                "huisnummer": None,
                "buurtnaam": "centrum",
                "wijknaam": "centrum",
                "geometrie": {
                    "type": "Point",
                    "coordinates": [4.43995901, 51.93254212],
                },
            },
        ],
        "bijlagen": [
            {
                "bestand": b64_file,
            },
            {
                "bestand": b64_file,
            },
        ],
    }

    @requests_mock.Mocker()
    def setUp(self, m):
        m.get(MOCK_URL, json={}, status_code=200)
        baker.make(OnderwerpAlias, bron_url=MOCK_URL)
        baker.make(Instelling, onderwerpen_basis_url=MOCK_URL)
        baker.make(
            Applicatie,
            naam="signaal_url",
            basis_url=MOCK_URL,
            valide_basis_urls=[MOCK_URL],
        )

    def test_create_signaal_unauthenticated(self):
        client = get_unauthenticated_client()
        url = reverse("app:signaal-list")
        data = {}
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @requests_mock.Mocker()
    def test_create_signaal_authenticated(self, m):
        m.get(MOCK_URL, json={}, status_code=200)
        client = get_authenticated_client()
        url = reverse("app:signaal-list")

        response = client.post(url, data=self.signaal_data, format="json")
        melding = Melding.objects.all()

        self.assertEqual(Bijlage.objects.all().count(), 2)
        self.assertEqual(melding.first().locaties_voor_melding.all().count(), 1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_download_afbeelding_unauthenticated(self, m):
        m.get(MOCK_URL, json={}, status_code=200)
        client = get_authenticated_client()
        unauthenticated_client = get_unauthenticated_client()
        signaal_url = reverse("app:signaal-list")
        client.post(signaal_url, data=self.signaal_data, format="json")
        melding = Melding.objects.first()
        melding_url = reverse("app:melding-detail", kwargs={"uuid": melding.uuid})
        melding_response = client.get(melding_url, format="json")
        unauthenticated_response = unauthenticated_client.get(
            melding_response.json()
            .get("signalen_voor_melding", [])[0]
            .get("bijlagen", [])[0]
            .get("bestand")
        )
        self.assertEqual(
            unauthenticated_response.status_code, status.HTTP_403_FORBIDDEN
        )

    @requests_mock.Mocker()
    def test_download_afbeelding_authenticated(self, m):
        m.get(MOCK_URL, json={}, status_code=200)
        client = get_authenticated_client()
        signaal_url = reverse("app:signaal-list")

        client.post(signaal_url, data=self.signaal_data, format="json")
        melding = Melding.objects.first()
        melding_url = reverse("app:melding-detail", kwargs={"uuid": melding.uuid})
        melding_response = client.get(melding_url, format="json")
        authenticated_response = client.get(
            melding_response.json()
            .get("signalen_voor_melding", [])[0]
            .get("bijlagen", [])[0]
            .get("bestand")
        )
        self.assertEqual(authenticated_response.status_code, status.HTTP_200_OK)


class MeldingApiTest(APITestCase):
    def test_get_melding_unauthenticated(self):
        client = get_unauthenticated_client()
        instance = baker.make(Melding)
        url = reverse("app:melding-detail", kwargs={"uuid": instance.uuid})

        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_melding_authenticated(self):
        client = get_authenticated_client()
        instance = baker.make(Melding)
        url = reverse("app:melding-detail", kwargs={"uuid": instance.uuid})

        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_melding_not_found(self):
        client = get_authenticated_client()
        url = reverse("app:melding-detail", kwargs={"uuid": 99})

        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_melding_list(self):
        client = get_authenticated_client()
        baker.make(Melding, _quantity=3)

        url = reverse("app:melding-list")

        response = client.get(url)
        data = response.json()

        self.assertEqual(len(data["results"]), 3)

    def test_filter_melding_within_distance(self):
        reference_lat = 51.924409
        reference_lon = 4.477736
        d = 30

        client = get_authenticated_client()
        m1 = baker.make(Melding)
        baker.make(Adres, geometrie=Point(reference_lon, reference_lat), melding=m1)
        m2 = baker.make(Melding)
        baker.make(Adres, geometrie=Point(4.478122, 51.924488), melding=m2)

        url = reverse("app:melding-list")

        response = client.get(
            f"{url}?within=lat:{reference_lat},lon:{reference_lon},d:{d}"
        )
        data = response.json()

        self.assertEqual(len(data["results"]), 2)

    def test_filter_melding_not_within_distance(self):
        reference_lat = 51.924409
        reference_lon = 4.477736
        d = 20

        client = get_authenticated_client()
        m1 = baker.make(Melding)
        baker.make(Adres, geometrie=Point(reference_lon, reference_lat), melding=m1)
        m2 = baker.make(Melding)
        baker.make(Adres, geometrie=Point(4.478122, 51.924488), melding=m2)

        url = reverse("app:melding-list")

        response = client.get(
            f"{url}?within=lat:{reference_lat},lon:{reference_lon},d:{d}"
        )
        data = response.json()

        self.assertEqual(len(data["results"]), 1)

    def test_filter_melding_with_mutiple_locations_within_distance(self):
        reference_lat = 51.924409
        reference_lon = 4.477736
        d = 30

        client = get_authenticated_client()
        m1 = baker.make(Melding)
        baker.make(
            Adres, geometrie=Point(reference_lon, reference_lat), melding=m1, gewicht=1
        )
        baker.make(Adres, geometrie=Point(4.479677, 51.924818), melding=m1, gewicht=0.5)
        m2 = baker.make(Melding)
        baker.make(Adres, geometrie=Point(4.478122, 51.924488), melding=m2, gewicht=1)
        baker.make(Adres, geometrie=Point(4.475525, 51.924012), melding=m2, gewicht=0.5)

        url = reverse("app:melding-list")

        response = client.get(
            f"{url}?within=lat:{reference_lat},lon:{reference_lon},d:{d}"
        )
        data = response.json()

        self.assertEqual(len(data["results"]), 2)

    @requests_mock.Mocker()
    def test_filter_ontdubbel_melding(self, m):
        client = get_authenticated_client()
        url = reverse("app:melding-list")

        tz = get_current_timezone()
        melding_1_dt = make_aware(datetime(2000, 1, 1, 0, 0, 20), tz)
        melding_2_dt = make_aware(datetime(2000, 1, 1, 0, 0, 10), tz)
        zoek_dt = make_aware(datetime(2000, 1, 1, 0, 0, 30), tz) - timedelta(seconds=15)

        d = 10

        p1 = [4.477737, 51.924411]
        # diff: 9.94 meters from p1
        p2 = [4.477592, 51.924411]
        # diff: 10.08 meters from p1
        p3 = [4.477590, 51.924411]

        onderwerp_1_url = "https://onderwerpen.com/mock_onderwerp_1"
        onderwerp_2_url = "https://onderwerpen.com/mock_onderwerp_2"
        m.get(onderwerp_1_url, json={}, status_code=200)
        m.get(onderwerp_2_url, json={}, status_code=200)
        onderwerp_1 = baker.make(OnderwerpAlias, bron_url=onderwerp_1_url)
        onderwerp_2 = baker.make(OnderwerpAlias, bron_url=onderwerp_2_url)

        status_naam_1 = "openstaand"
        status_naam_2 = "afgehandeld"

        # melding 1
        melding_1_status = baker.make(Status, naam=status_naam_1)
        m1 = melding_1_status.melding
        m1.origineel_aangemaakt = melding_1_dt
        m1.status = melding_1_status
        m1.onderwerpen.add(onderwerp_1)
        m1.save()
        baker.make(Adres, geometrie=Point(*p1), melding=m1, gewicht=1)

        # melding 2
        # change origineel_aangemaakt
        melding_2_status = baker.make(Status, naam=status_naam_1)
        m2 = melding_2_status.melding
        m2.origineel_aangemaakt = melding_2_dt
        m2.status = melding_2_status
        m2.onderwerpen.add(onderwerp_1)
        m2.save()
        baker.make(Adres, geometrie=Point(*p2), melding=m2, gewicht=1)

        # melding 3
        # change status
        melding_3_status = baker.make(Status, naam=status_naam_2)
        m3 = melding_3_status.melding
        m3.origineel_aangemaakt = melding_1_dt
        m3.status = melding_3_status
        m3.onderwerpen.add(onderwerp_1)
        m3.save()
        baker.make(Adres, geometrie=Point(*p2), melding=m3, gewicht=1)

        # melding 4
        # change onderwerp
        melding_4_status = baker.make(Status, naam=status_naam_1)
        m4 = melding_4_status.melding
        m4.origineel_aangemaakt = melding_1_dt
        m4.status = melding_4_status
        m4.onderwerpen.add(onderwerp_2)
        m4.save()
        baker.make(Adres, geometrie=Point(*p2), melding=m4, gewicht=1)

        # melding 5
        # change point to p3 (uitside range)
        melding_5_status = baker.make(Status, naam=status_naam_1)
        m5 = melding_5_status.melding
        m5.origineel_aangemaakt = melding_1_dt
        m5.status = melding_5_status
        m5.onderwerpen.add(onderwerp_1)
        m5.save()
        baker.make(Adres, geometrie=Point(*p3), melding=m5, gewicht=1)
        baker.make(Adres, geometrie=Point(*p2), melding=m5, gewicht=0.8)
        baker.make(Adres, geometrie=Point(*p1), melding=m5, gewicht=0.5)

        data = {
            "within": f"lat:{p1[1]},lon:{p1[0]},d:{d}",
            "onderwerp_url": onderwerp_1_url,
            "origineel_aangemaakt_gt": zoek_dt.isoformat(),
            "status": [
                "openstaand",
                "in_behandeling",
                "controle",
                "wachten_melder",
                "pauze",
            ],
            "ordering": "origineel_aangemaakt",
            "limit": "5",
        }
        response = client.get(url, data=data)
        data = response.json()

        self.assertEqual(Melding.objects.count(), 5)
        self.assertEqual(len(data["results"]), 1)
