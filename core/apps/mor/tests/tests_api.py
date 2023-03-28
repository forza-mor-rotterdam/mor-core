import base64
import io
import os

from apps.mor.models import (
    Bijlage,
    Melding,
    MeldingGebeurtenis,
    MeldingGebeurtenisType,
    Signaal,
    TaakApplicatie,
)
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

B64_FILE = "e1xydGYxXGFuc2lcYW5zaWNwZzEyNTJcY29jb2FydGYyNTgwClxjb2NvYXRleHRzY2FsaW5nMFxjb2NvYXBsYXRmb3JtMHtcZm9udHRibFxmMFxmc3dpc3NcZmNoYXJzZXQwIEhlbHZldGljYTt9CntcY29sb3J0Ymw7XHJlZDI1NVxncmVlbjI1NVxibHVlMjU1O30Ke1wqXGV4cGFuZGVkY29sb3J0Ymw7O30KXHBhcGVydzExOTAwXHBhcGVyaDE2ODQwXG1hcmdsMTQ0MFxtYXJncjE0NDBcdmlld3cxMTUyMFx2aWV3aDg0MDBcdmlld2tpbmQwClxwYXJkXHR4NTY2XHR4MTEzM1x0eDE3MDBcdHgyMjY3XHR4MjgzNFx0eDM0MDFcdHgzOTY4XHR4NDUzNVx0eDUxMDJcdHg1NjY5XHR4NjIzNlx0eDY4MDNccGFyZGlybmF0dXJhbFxwYXJ0aWdodGVuZmFjdG9yMAoKXGYwXGZzMjQgXGNmMCBUZXN0IGZpbGV9Cg=="
B64_IMAGE = "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"


# class TaakApplicatieApiTest(APITestCase, GenericAPITestCase):
#     url_basename = "app:taak_applicatie"
#     model_cls = TaakApplicatie
#     mock_instance = {"naam": "mock"}


class SignaalApiTest(APITestCase):
    def test_create(self):
        url = reverse("app:signaal-list")
        client = APIClient()

        file = "tekst.rtf"
        b64_file = "e1xydGYxXGFuc2lcYW5zaWNwZzEyNTJcY29jb2FydGYyNTgwClxjb2NvYXRleHRzY2FsaW5nMFxjb2NvYXBsYXRmb3JtMHtcZm9udHRibFxmMFxmc3dpc3NcZmNoYXJzZXQwIEhlbHZldGljYTt9CntcY29sb3J0Ymw7XHJlZDI1NVxncmVlbjI1NVxibHVlMjU1O30Ke1wqXGV4cGFuZGVkY29sb3J0Ymw7O30KXHBhcGVydzExOTAwXHBhcGVyaDE2ODQwXG1hcmdsMTQ0MFxtYXJncjE0NDBcdmlld3cxMTUyMFx2aWV3aDg0MDBcdmlld2tpbmQwClxwYXJkXHR4NTY2XHR4MTEzM1x0eDE3MDBcdHgyMjY3XHR4MjgzNFx0eDM0MDFcdHgzOTY4XHR4NDUzNVx0eDUxMDJcdHg1NjY5XHR4NjIzNlx0eDY4MDNccGFyZGlybmF0dXJhbFxwYXJ0aWdodGVuZmFjdG9yMAoKXGYwXGZzMjQgXGNmMCBUZXN0IGZpbGV9Cg=="
        base_dir = os.path.dirname(os.path.realpath(__file__))
        with open(f"{base_dir}/bestanden/{file}", "rb") as fp:
            fio = io.FileIO(fp.fileno())
            fio.name = fp.name

        with open(f"{base_dir}/bestanden/{file}", "rb") as binary_file:
            binary_file_data = binary_file.read()
            base64_encoded_data = base64.b64encode(binary_file_data)
            base64_encoded_data.decode("utf-8")

        data = {
            "melder": {
                "voornaam": "string",
                "achternaam": "string",
                "email": "user@example.com",
                "telefoonnummer": "string",
            },
            "bijlagen": [
                {
                    "bestand": b64_file,
                }
            ],
            "origineel_aangemaakt": "2023-03-09T11:56:04.036Z",
            "tekst": "string",
            "meta": {
                "additionalProp1": "string",
                "additionalProp2": "string",
                "additionalProp3": "string",
            },
            "bron": "mock_bron",
            "onderwerp": "mock_onderwerp",
            "graven": [
                {
                    "bron": "string",
                    "plaatsnaam": "string",
                    "begraafplaats": "string",
                    "grafnummer": "string",
                    "vak": "string",
                    "geometrieen": [],
                }
            ],
        }
        response = client.post(url, data=data, format="json")
        melding = Melding.objects.all()

        self.assertEqual(Bijlage.objects.all().count(), 2)
        self.assertEqual(melding.first().locaties.all().count(), 1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class MeldingApiTest(APITestCase):
    def test_get_not_found(self):
        url = reverse("app:melding-detail", kwargs={"pk": 99})

        client = APIClient()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get(self):
        instance = baker.make(Melding)
        url = reverse("app:melding-detail", kwargs={"pk": instance.pk})

        client = APIClient()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_list(self):
        baker.make(Melding, _quantity=2)

        url = reverse("app:melding-list")

        client = APIClient()
        response = client.get(url)
        data = response.json()

        self.assertEqual(len(data["results"]), 2)
