import copy

import requests_mock
from apps.applicaties.models import Applicatie
from apps.bijlagen.models import Bijlage
from apps.instellingen.models import Instelling
from apps.meldingen.models import Melding
from apps.status.models import Status
from apps.taken.models import Taakgebeurtenis
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker
from rest_framework import status
from rest_framework.test import APITestCase
from utils.unittest_helpers import get_authenticated_client, get_unauthenticated_client

B64_FILE = "e1xydGYxXGFuc2lcYW5zaWNwZzEyNTJcY29jb2FydGYyNTgwClxjb2NvYXRleHRzY2FsaW5nMFxjb2NvYXBsYXRmb3JtMHtcZm9udHRibFxmMFxmc3dpc3NcZmNoYXJzZXQwIEhlbHZldGljYTt9CntcY29sb3J0Ymw7XHJlZDI1NVxncmVlbjI1NVxibHVlMjU1O30Ke1wqXGV4cGFuZGVkY29sb3J0Ymw7O30KXHBhcGVydzExOTAwXHBhcGVyaDE2ODQwXG1hcmdsMTQ0MFxtYXJncjE0NDBcdmlld3cxMTUyMFx2aWV3aDg0MDBcdmlld2tpbmQwClxwYXJkXHR4NTY2XHR4MTEzM1x0eDE3MDBcdHgyMjY3XHR4MjgzNFx0eDM0MDFcdHgzOTY4XHR4NDUzNVx0eDUxMDJcdHg1NjY5XHR4NjIzNlx0eDY4MDNccGFyZGlybmF0dXJhbFxwYXJ0aWdodGVuZmFjdG9yMAoKXGYwXGZzMjQgXGNmMCBUZXN0IGZpbGV9Cg=="
B64_IMAGE = "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"
MOCK_URL = "https://mock.com/"


class TaakopdrachtAanmakenApiTest(APITestCase):
    b64_file = "e1xydGYxXGFuc2lcYW5zaWNwZzEyNTJcY29jb2FydGYyNTgwClxjb2NvYXRleHRzY2FsaW5nMFxjb2NvYXBsYXRmb3JtMHtcZm9udHRibFxmMFxmc3dpc3NcZmNoYXJzZXQwIEhlbHZldGljYTt9CntcY29sb3J0Ymw7XHJlZDI1NVxncmVlbjI1NVxibHVlMjU1O30Ke1wqXGV4cGFuZGVkY29sb3J0Ymw7O30KXHBhcGVydzExOTAwXHBhcGVyaDE2ODQwXG1hcmdsMTQ0MFxtYXJncjE0NDBcdmlld3cxMTUyMFx2aWV3aDg0MDBcdmlld2tpbmQwClxwYXJkXHR4NTY2XHR4MTEzM1x0eDE3MDBcdHgyMjY3XHR4MjgzNFx0eDM0MDFcdHgzOTY4XHR4NDUzNVx0eDUxMDJcdHg1NjY5XHR4NjIzNlx0eDY4MDNccGFyZGlybmF0dXJhbFxwYXJ0aWdodGVuZmFjdG9yMAoKXGYwXGZzMjQgXGNmMCBUZXN0IGZpbGV9Cg=="
    tekst_meer_dan_5000 = "Lorem ipsum odor amet, consectetuer adipiscing elit. Fames ligula augue cubilia lacus auctor quam. Odio magna sodales torquent metus maecenas praesent. Id sapien fermentum morbi fusce integer. Neque quisque quisque potenti tortor aliquam curabitur aenean. Ipsum fames massa dolor adipiscing elit elit nibh. Mollis consequat ex ultricies natoque ridiculus sociosqu; ultricies risus consectetur. Hendrerit rhoncus sodales nam fringilla augue nullam. Orci lacinia euismod leo tempor ex sodales tellus. Donec inceptos aliquam volutpat aptent praesent mollis lectus! Sollicitudin condimentum congue torquent potenti sit; donec convallis. Rutrum turpis fringilla aliquet ornare amet viverra nulla sem. Risus vulputate facilisis suscipit vivamus molestie turpis interdum eu. Sagittis neque erat risus ridiculus lectus etiam vivamus. Parturient cursus aptent in cursus eleifend. Sit volutpat tempor nisl laoreet penatibus orci ultricies gravida. Nisi platea est sem nascetur sodales lobortis. Fringilla metus bibendum quis mauris porta etiam magnis varius. Vestibulum dictum volutpat nullam leo libero blandit ullamcorper blandit. Malesuada potenti gravida ante malesuada quis nulla suscipit. Malesuada taciti at suspendisse; netus potenti eros? Nostra primis magnis, quam aenean facilisis blandit facilisi. Fusce placerat mattis mollis nascetur sed vivamus. Mattis scelerisque efficitur cras suspendisse congue tellus. Fermentum vel tristique facilisi vel nulla sapien. Duis congue amet consectetur morbi, a sodales hendrerit lacus. Nibh finibus metus mattis; morbi magna molestie. Consectetur tincidunt gravida eget habitasse maximus vitae per. Habitasse metus a ipsum semper aliquam non eros nec nisi. Varius laoreet duis quis nec nostra per. Erat pretium eros sodales, nec montes consectetur vel suspendisse. Litora semper morbi lobortis lacus lacus auctor diam congue. Mi natoque senectus turpis per pretium ultricies senectus. Blandit quam donec aliquet luctus aliquam habitasse varius pharetra ac. Mus auctor fames lectus ullamcorper auctor accumsan hendrerit litora. Montes dictum arcu primis ac lorem aptent sit porta. Hendrerit sem malesuada cursus inceptos eros enim non. Eu vel duis consectetur lacus; turpis eu arcu. Dui proin aliquam euismod gravida nunc phasellus. Mauris vel suscipit rutrum adipiscing tincidunt magnis euismod taciti. Hendrerit sagittis ornare elit maximus pellentesque; id finibus sit. Arcu iaculis massa sollicitudin interdum ex imperdiet eget. Libero rutrum blandit senectus velit tempus vehicula fermentum pretium. Montes iaculis euismod varius dis vulputate maximus porttitor. Aptent inceptos proin laoreet dui accumsan. Sapien a maximus ut pellentesque imperdiet velit. In pellentesque vivamus facilisi quam condimentum nunc; risus nisl. Vitae facilisis felis vestibulum vitae fringilla eget. Dapibus lacus venenatis litora in sagittis integer enim himenaeos fames. Primis est imperdiet massa leo tellus vulputate interdum hendrerit malesuada. Dictum velit nunc curae quam placerat quis adipiscing. Volutpat etiam diam tempus vitae leo. Ultricies at maximus amet, finibus vel semper purus. Dis sodales netus suspendisse; ultrices cras hendrerit taciti? Praesent dolor maecenas ut non potenti feugiat lacinia malesuada. Nascetur mattis sapien mi tortor himenaeos faucibus. Ullamcorper diam laoreet congue tortor magnis. Dignissim penatibus sem, pharetra pretium nullam rutrum curae. Tincidunt interdum faucibus nec habitasse a. Nec scelerisque magnis posuere; augue et varius? Fringilla fames adipiscing senectus penatibus, platea nunc. Lacinia quisque porta ante montes arcu sapien egestas. Nisi morbi ex ultricies iaculis torquent finibus feugiat elementum. Enim mus litora purus scelerisque sagittis. Libero natoque nostra integer cras elementum massa, rutrum consequat. Pellentesque vulputate sapien ultrices platea velit morbi fringilla mi. Feugiat est dapibus vehicula sem eleifend sit. Inceptos magna dictum cras, iaculis nec scelerisque vivamus ex. Elit suscipit ipsum sociosqu sagittis vestibulum quam sociosqu magnis. Vivamus ullamcorper id sodales faucibus varius fusce efficitur. Erat platea potenti posuere sagittis elit sagittis dis ac feugiat. Metus quis dictumst sodales non lacus aptent lacus proin blandit. Tempus nascetur morbi magna facilisis platea. Molestie mus lacinia aliquet fames; habitasse in. Augue velit etiam nostra amet elit luctus maximus at. At pretium mollis sem fusce placerat inceptos habitant sodales viverra. Habitant convallis facilisi dis volutpat tellus imperdiet. Hendrerit condimentum dis ad convallis sociosqu massa. Enim ultricies faucibus egestas luctus, eleifend auctor mus. Gravida diam fermentum tempus eros diam porta per. Risus dui erat tincidunt non condimentum et potenti porta. Lectus magnis arcu facilisis mollis mi nunc ultricies hendrerit. Non adipiscing adipiscing natoque duis vitae donec dignissim quisque. Taciti tempus nam aenean, velit in cubilia tincidunt rhoncus. Platea ipsum euismod facilisis; dictum dui orci maecenas egestas. Ipsum dignissim eu donec mollis at. Scelerisque mattis euismod ligula varius nec odio mi facilisi aptent. Montes ultrices dui dis condimentum tincidunt penatibus dignissim nunc. Suspendisse nisl tortor suscipit torquent orci dignissim quis. Sociosqu urna nascetur morbi vulputate ut posuere quisque."
    tekst_tussen_500_en_5000 = "Lorem ipsum odor amet, consectetuer adipiscing elit. Fames ligula augue cubilia lacus auctor quam. Odio magna sodales torquent metus maecenas praesent.Id sapien fermentum morbi fusce integer. Neque quisque quisque potenti tortor aliquam curabitur aenean. Ipsum fames massa dolor adipiscing elit elit nibh. Mollis consequat ex ultricies natoque ridiculus sociosqu; ultricies risus consectetur. Hendrerit rhoncus sodales nam fringilla augue nullam. Orci lacinia euismod leo tempor ex sodales tellus. Donec inceptos aliquam volutpat aptent praesent mollis lectus! Sollicitudin condimentum congue torquent potenti sit; donec convallis."
    tekst_minder_dan_500 = "Lorem ipsum odor amet, consectetuer adipiscing elit. Fames ligula augue cubilia lacus auctor quam. Odio magna sodales torquent metus maecenas praesent."
    taakopdracht_data = {
        "titel": "mock_title",
        "taaktype": MOCK_URL,
        "bericht": tekst_minder_dan_500,
    }

    @requests_mock.Mocker()
    def setUp(self, m):
        m.get(MOCK_URL, json={}, status_code=200)
        baker.make(Melding, status=baker.make(Status))
        baker.make(Instelling, onderwerpen_basis_url=MOCK_URL)
        baker.make(
            Applicatie,
            naam="signaal_url",
            basis_url=MOCK_URL,
            valide_basis_urls=[MOCK_URL],
        )

    def test_taakopdracht_aanmaken_unauthenticated(self):
        client = get_unauthenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = self.taakopdracht_data
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_taakopdracht_aanmaken_authenticated(self):
        client = get_authenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = self.taakopdracht_data
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_taakopdracht_aanmaken_lang_bericht(self):
        client = get_authenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = copy.deepcopy(self.taakopdracht_data)
        data.update({"bericht": self.tekst_tussen_500_en_5000})
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_taakopdracht_aanmaken_te_lang_bericht(self):
        client = get_authenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = copy.deepcopy(self.taakopdracht_data)
        data.update({"bericht": self.tekst_meer_dan_5000})
        response = client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaakopdrachtStatusAanpassenApiTest(APITestCase):
    b64_file = "e1xydGYxXGFuc2lcYW5zaWNwZzEyNTJcY29jb2FydGYyNTgwClxjb2NvYXRleHRzY2FsaW5nMFxjb2NvYXBsYXRmb3JtMHtcZm9udHRibFxmMFxmc3dpc3NcZmNoYXJzZXQwIEhlbHZldGljYTt9CntcY29sb3J0Ymw7XHJlZDI1NVxncmVlbjI1NVxibHVlMjU1O30Ke1wqXGV4cGFuZGVkY29sb3J0Ymw7O30KXHBhcGVydzExOTAwXHBhcGVyaDE2ODQwXG1hcmdsMTQ0MFxtYXJncjE0NDBcdmlld3cxMTUyMFx2aWV3aDg0MDBcdmlld2tpbmQwClxwYXJkXHR4NTY2XHR4MTEzM1x0eDE3MDBcdHgyMjY3XHR4MjgzNFx0eDM0MDFcdHgzOTY4XHR4NDUzNVx0eDUxMDJcdHg1NjY5XHR4NjIzNlx0eDY4MDNccGFyZGlybmF0dXJhbFxwYXJ0aWdodGVuZmFjdG9yMAoKXGYwXGZzMjQgXGNmMCBUZXN0IGZpbGV9Cg=="
    tekst_meer_dan_5000 = "Lorem ipsum odor amet, consectetuer adipiscing elit. Fames ligula augue cubilia lacus auctor quam. Odio magna sodales torquent metus maecenas praesent. Id sapien fermentum morbi fusce integer. Neque quisque quisque potenti tortor aliquam curabitur aenean. Ipsum fames massa dolor adipiscing elit elit nibh. Mollis consequat ex ultricies natoque ridiculus sociosqu; ultricies risus consectetur. Hendrerit rhoncus sodales nam fringilla augue nullam. Orci lacinia euismod leo tempor ex sodales tellus. Donec inceptos aliquam volutpat aptent praesent mollis lectus! Sollicitudin condimentum congue torquent potenti sit; donec convallis. Rutrum turpis fringilla aliquet ornare amet viverra nulla sem. Risus vulputate facilisis suscipit vivamus molestie turpis interdum eu. Sagittis neque erat risus ridiculus lectus etiam vivamus. Parturient cursus aptent in cursus eleifend. Sit volutpat tempor nisl laoreet penatibus orci ultricies gravida. Nisi platea est sem nascetur sodales lobortis. Fringilla metus bibendum quis mauris porta etiam magnis varius. Vestibulum dictum volutpat nullam leo libero blandit ullamcorper blandit. Malesuada potenti gravida ante malesuada quis nulla suscipit. Malesuada taciti at suspendisse; netus potenti eros? Nostra primis magnis, quam aenean facilisis blandit facilisi. Fusce placerat mattis mollis nascetur sed vivamus. Mattis scelerisque efficitur cras suspendisse congue tellus. Fermentum vel tristique facilisi vel nulla sapien. Duis congue amet consectetur morbi, a sodales hendrerit lacus. Nibh finibus metus mattis; morbi magna molestie. Consectetur tincidunt gravida eget habitasse maximus vitae per. Habitasse metus a ipsum semper aliquam non eros nec nisi. Varius laoreet duis quis nec nostra per. Erat pretium eros sodales, nec montes consectetur vel suspendisse. Litora semper morbi lobortis lacus lacus auctor diam congue. Mi natoque senectus turpis per pretium ultricies senectus. Blandit quam donec aliquet luctus aliquam habitasse varius pharetra ac. Mus auctor fames lectus ullamcorper auctor accumsan hendrerit litora. Montes dictum arcu primis ac lorem aptent sit porta. Hendrerit sem malesuada cursus inceptos eros enim non. Eu vel duis consectetur lacus; turpis eu arcu. Dui proin aliquam euismod gravida nunc phasellus. Mauris vel suscipit rutrum adipiscing tincidunt magnis euismod taciti. Hendrerit sagittis ornare elit maximus pellentesque; id finibus sit. Arcu iaculis massa sollicitudin interdum ex imperdiet eget. Libero rutrum blandit senectus velit tempus vehicula fermentum pretium. Montes iaculis euismod varius dis vulputate maximus porttitor. Aptent inceptos proin laoreet dui accumsan. Sapien a maximus ut pellentesque imperdiet velit. In pellentesque vivamus facilisi quam condimentum nunc; risus nisl. Vitae facilisis felis vestibulum vitae fringilla eget. Dapibus lacus venenatis litora in sagittis integer enim himenaeos fames. Primis est imperdiet massa leo tellus vulputate interdum hendrerit malesuada. Dictum velit nunc curae quam placerat quis adipiscing. Volutpat etiam diam tempus vitae leo. Ultricies at maximus amet, finibus vel semper purus. Dis sodales netus suspendisse; ultrices cras hendrerit taciti? Praesent dolor maecenas ut non potenti feugiat lacinia malesuada. Nascetur mattis sapien mi tortor himenaeos faucibus. Ullamcorper diam laoreet congue tortor magnis. Dignissim penatibus sem, pharetra pretium nullam rutrum curae. Tincidunt interdum faucibus nec habitasse a. Nec scelerisque magnis posuere; augue et varius? Fringilla fames adipiscing senectus penatibus, platea nunc. Lacinia quisque porta ante montes arcu sapien egestas. Nisi morbi ex ultricies iaculis torquent finibus feugiat elementum. Enim mus litora purus scelerisque sagittis. Libero natoque nostra integer cras elementum massa, rutrum consequat. Pellentesque vulputate sapien ultrices platea velit morbi fringilla mi. Feugiat est dapibus vehicula sem eleifend sit. Inceptos magna dictum cras, iaculis nec scelerisque vivamus ex. Elit suscipit ipsum sociosqu sagittis vestibulum quam sociosqu magnis. Vivamus ullamcorper id sodales faucibus varius fusce efficitur. Erat platea potenti posuere sagittis elit sagittis dis ac feugiat. Metus quis dictumst sodales non lacus aptent lacus proin blandit. Tempus nascetur morbi magna facilisis platea. Molestie mus lacinia aliquet fames; habitasse in. Augue velit etiam nostra amet elit luctus maximus at. At pretium mollis sem fusce placerat inceptos habitant sodales viverra. Habitant convallis facilisi dis volutpat tellus imperdiet. Hendrerit condimentum dis ad convallis sociosqu massa. Enim ultricies faucibus egestas luctus, eleifend auctor mus. Gravida diam fermentum tempus eros diam porta per. Risus dui erat tincidunt non condimentum et potenti porta. Lectus magnis arcu facilisis mollis mi nunc ultricies hendrerit. Non adipiscing adipiscing natoque duis vitae donec dignissim quisque. Taciti tempus nam aenean, velit in cubilia tincidunt rhoncus. Platea ipsum euismod facilisis; dictum dui orci maecenas egestas. Ipsum dignissim eu donec mollis at. Scelerisque mattis euismod ligula varius nec odio mi facilisi aptent. Montes ultrices dui dis condimentum tincidunt penatibus dignissim nunc. Suspendisse nisl tortor suscipit torquent orci dignissim quis. Sociosqu urna nascetur morbi vulputate ut posuere quisque."
    tekst_tussen_500_en_5000 = "Lorem ipsum odor amet, consectetuer adipiscing elit. Fames ligula augue cubilia lacus auctor quam. Odio magna sodales torquent metus maecenas praesent.Id sapien fermentum morbi fusce integer. Neque quisque quisque potenti tortor aliquam curabitur aenean. Ipsum fames massa dolor adipiscing elit elit nibh. Mollis consequat ex ultricies natoque ridiculus sociosqu; ultricies risus consectetur. Hendrerit rhoncus sodales nam fringilla augue nullam. Orci lacinia euismod leo tempor ex sodales tellus. Donec inceptos aliquam volutpat aptent praesent mollis lectus! Sollicitudin condimentum congue torquent potenti sit; donec convallis."
    tekst_minder_dan_500 = "Lorem ipsum odor amet, consectetuer adipiscing elit. Fames ligula augue cubilia lacus auctor quam. Odio magna sodales torquent metus maecenas praesent."
    taakopdracht_data = {
        "titel": "mock_title",
        "taaktype": MOCK_URL,
        "bericht": tekst_minder_dan_500,
    }
    taakopdracht_notificatie_data = {
        "bijlagen": [
            {
                "bestand": b64_file,
            },
            {
                "bestand": b64_file,
            },
        ],
        "omschrijving_intern": tekst_tussen_500_en_5000,
    }
    taakopdracht_status_aanpassen_data = {
        "bijlagen": [
            {
                "bestand": b64_file,
            },
            {
                "bestand": b64_file,
            },
        ],
        "taakstatus": {
            "naam": "afgehandeld",
        },
        "resolutie": "opgelost",
        "omschrijving_intern": tekst_tussen_500_en_5000,
    }

    @requests_mock.Mocker()
    def setUp(self, m):
        m.get(MOCK_URL, json={}, status_code=200)
        baker.make(Melding, status=baker.make(Status))
        baker.make(Instelling, onderwerpen_basis_url=MOCK_URL)
        baker.make(
            Applicatie,
            naam="signaal_url",
            basis_url=MOCK_URL,
            valide_basis_urls=[MOCK_URL],
        )

    def test_taakopdracht_notificatie(self):
        client = get_authenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url_aanmaken = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = self.taakopdracht_data
        status_aanpassen_data = self.taakopdracht_status_aanpassen_data
        response = client.post(url_aanmaken, data=data, format="json")
        url_status_aanpassen = reverse(
            "app:melding-taakopdracht-notificatie",
            kwargs={
                "uuid": melding.uuid,
                "taakopdracht_uuid": response.json().get("uuid"),
            },
        )
        response_status_aanpassen = client.post(
            url_status_aanpassen, data=status_aanpassen_data, format="json"
        )
        self.assertEqual(response_status_aanpassen.status_code, status.HTTP_200_OK)

    def test_taakopdracht_notificatie_zelfde_notificatie(self):
        client = get_authenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url_aanmaken = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = self.taakopdracht_data
        taakopdracht_notificatie_data = copy.deepcopy(
            self.taakopdracht_notificatie_data
        )
        nu = timezone.now().isoformat()
        taakopdracht_notificatie_data["aangemaakt_op"] = nu
        response = client.post(url_aanmaken, data=data, format="json")
        url_notificatie = reverse(
            "app:melding-taakopdracht-notificatie",
            kwargs={
                "uuid": melding.uuid,
                "taakopdracht_uuid": response.json().get("uuid"),
            },
        )
        response_url_notificatie = client.post(
            url_notificatie, data=taakopdracht_notificatie_data, format="json"
        )
        self.assertEqual(response_url_notificatie.status_code, status.HTTP_200_OK)
        self.assertEqual(Taakgebeurtenis.objects.count(), 2)
        response_url_notificatie_2 = client.post(
            url_notificatie, data=taakopdracht_notificatie_data, format="json"
        )
        self.assertEqual(response_url_notificatie_2.status_code, status.HTTP_200_OK)
        self.assertEqual(Taakgebeurtenis.objects.count(), 2)

    def test_taakopdracht_notificatie_zelfde_status(self):
        client = get_authenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url_aanmaken = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = self.taakopdracht_data
        status_aanpassen_data = copy.deepcopy(self.taakopdracht_status_aanpassen_data)
        status_aanpassen_data.update({"taakstatus": {"naam": "nieuw"}})
        response = client.post(url_aanmaken, data=data, format="json")
        url_status_aanpassen = reverse(
            "app:melding-taakopdracht-notificatie",
            kwargs={
                "uuid": melding.uuid,
                "taakopdracht_uuid": response.json().get("uuid"),
            },
        )
        response_status_aanpassen = client.post(
            url_status_aanpassen, data=status_aanpassen_data, format="json"
        )
        self.assertEqual(response_status_aanpassen.status_code, status.HTTP_200_OK)

    def test_taakopdracht_notificatie_foute_bijlagen(self):
        client = get_authenticated_client()
        melding = baker.make(Melding, status=baker.make(Status))
        url_aanmaken = reverse(
            "app:melding-taakopdracht-aanmaken", kwargs={"uuid": melding.uuid}
        )
        data = self.taakopdracht_data
        status_aanpassen_data = copy.deepcopy(self.taakopdracht_status_aanpassen_data)
        status_aanpassen_data.update(
            {
                "bijlagen": [
                    {
                        "bestand": B64_FILE,
                    }
                ]
            }
        )
        response = client.post(url_aanmaken, data=data, format="json")
        url_status_aanpassen = reverse(
            "app:melding-taakopdracht-notificatie",
            kwargs={
                "uuid": melding.uuid,
                "taakopdracht_uuid": response.json().get("uuid"),
            },
        )
        client.post(url_status_aanpassen, data=status_aanpassen_data, format="json")
        taakgebeurtenissen = Taakgebeurtenis.objects.all()
        bijlagen = Bijlage.objects.all()
        self.assertEqual(taakgebeurtenissen.count(), 2)
        self.assertEqual(bijlagen.count(), 1)
