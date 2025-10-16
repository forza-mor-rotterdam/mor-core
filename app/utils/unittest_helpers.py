from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import management
from django.urls import reverse
from model_bakery import baker
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

AUTHENTICATED_CLIENT_EMAIL = "f.foo@foo.com"


class GenericAPITestCase:
    url_basename = None
    model_cls = None
    mock_instance = None

    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()

    def test_get_not_found(self):
        url = reverse(f"{self.url_basename}-detail", kwargs={"pk": 99})

        client = APIClient()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create(self):
        url = reverse(f"{self.url_basename}-list")

        client = APIClient()
        response = client.post(url, self.mock_instance)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get(self):
        instance = baker.make(self.model_cls)
        url = reverse(f"{self.url_basename}-detail", kwargs={"pk": instance.pk})

        client = APIClient()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_list(self):
        baker.make(self.model_cls, _quantity=2)

        url = reverse(f"{self.url_basename}-list")

        client = APIClient()
        response = client.get(url)
        data = response.json()

        self.assertEqual(len(data["results"]), 2)


def add_user_to_authorized_groups(user):
    """
    Adds users to the authorized groups configured in the OIDC_AUTHORIZED_GROUPS
    """
    realm_access_groups = settings.OIDC_AUTHORIZED_GROUPS

    all_permissions = Permission.objects.all()
    for realm_access_group in realm_access_groups:
        group, _ = Group.objects.get_or_create(name=realm_access_group)
        for permission in all_permissions:
            group.permissions.add(permission)
        group.user_set.add(user)


def get_test_user():
    """
    Creates and returns a test user
    """
    return get_user_model().objects.get_or_create(email=settings.DJANGO_TEST_EMAIL)[0]


def get_authenticated_client():
    """
    Returns an authenticated APIClient, for unit testing API requests
    """
    user = get_test_user()
    access_token = Token.objects.create(user=user)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token {}".format(access_token))
    return client


def get_authenticated_with_token_client(access_token):
    """
    Some endpoints can be accessed using a special designated token. This creates a client for such an authenticated request.
    """
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="{}".format(access_token))
    return client


def get_unauthenticated_client():
    """
    Returns an unauthenticated APIClient, for unit testing API requests
    """
    return APIClient()
