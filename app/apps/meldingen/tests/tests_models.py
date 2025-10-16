import requests_mock
from apps.meldingen.managers import MeldingManager
from apps.meldingen.models import Melding
from apps.meldingen.serializers import MeldingGebeurtenisStatusSerializer
from apps.meldingen.tests.factories import (
    MeldingFactory,
    OnderwerpAliasFactory,
    StatusFactory,
)
from django.db import transaction
from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError


class MeldingTransactionTest(TransactionTestCase):
    databases = {"default", "alternate"}
    DB1 = "default"
    DB2 = "alternate"

    @requests_mock.Mocker()
    def setUp(self, m):
        m.get("http://mock_url", json={}, status_code=200)
        onderwerp_alias = OnderwerpAliasFactory()
        melding = MeldingFactory()
        melding.onderwerpen.set([onderwerp_alias])
        status = StatusFactory(melding=melding)
        data = {
            "melding": melding.id,
            "status": {
                "naam": status.naam,
                "melding": status.melding.id,
            },
            "gebeurtenis_type": "your_gebeurtenis_type_value",
            "resolutie": "your_resolutie_value",
            "bijlagen": [],
            "omschrijving_intern": "your_intern_description",
            "omschrijving_extern": "your_extern_description",
            "gebruiker": "your_gebruiker_value",
        }
        self.serializer = MeldingGebeurtenisStatusSerializer(data=data)
        self.serializer.is_valid()
        self.melding = melding

    def test_dubbele_status_verandering_serieel(self):
        with transaction.atomic(using=self.DB1):
            melding = Melding.objects.using(self.DB1).get(id=self.melding.id)
            Melding.acties.status_aanpassen(self.serializer, melding, self.DB1)
        with transaction.atomic(using=self.DB2):
            melding = Melding.objects.using(self.DB2).get(id=self.melding.id)
            with self.assertRaises(ValidationError):
                Melding.acties.status_aanpassen(self.serializer, melding, self.DB1)

    def test_dubbele_status_verandering_parallel(self):
        with transaction.atomic(using=self.DB1):
            melding = Melding.objects.using(self.DB1).get(id=self.melding.id)
            Melding.acties.status_aanpassen(self.serializer, melding, self.DB1)
            with transaction.atomic(using=self.DB2):
                melding = Melding.objects.using(self.DB2).get(id=self.melding.id)
                with self.assertRaises(MeldingManager.MeldingInGebruik):
                    Melding.acties.status_aanpassen(self.serializer, melding, self.DB2)
