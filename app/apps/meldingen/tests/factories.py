import factory
from apps.aliassen.models import OnderwerpAlias
from apps.meldingen.models import Melding, Meldinggebeurtenis
from apps.signalen.models import Signaal
from apps.status.models import Status


class OnderwerpAliasFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OnderwerpAlias

    bron_url = "http://mock_url"


class SignaalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Signaal

    signaal_url = "http://example.com"
    melding = factory.SubFactory("factories.MeldingFactory")

    onderwerpen = factory.RelatedFactoryList(
        "factories.OnderwerpAliasFactory", factory_related_name="signaal"
    )
    # Add other fields as needed


class MeldingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Melding

    origineel_aangemaakt = factory.Faker("date_time_this_decade")
    # Add other fields as needed


class StatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Status

    naam = Status.NaamOpties.CONTROLE
    melding = factory.SubFactory(MeldingFactory)


class MeldinggebeurtenisFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Meldinggebeurtenis

    gebeurtenis_type = Meldinggebeurtenis.GebeurtenisType.STATUS_WIJZIGING
    omschrijving_intern = factory.Faker("text", max_nb_chars=5000)
    omschrijving_extern = factory.Faker("text", max_nb_chars=2000)
    gebruiker = factory.Faker("name")
    melding = factory.SubFactory(MeldingFactory)
    status = factory.SubFactory(StatusFactory)
    # Add other fields as needed
