import logging
import os
import re
import sys

from apps.applicaties.models import Applicatie, encrypt_gebruiker_wachtwoord
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates applications according to the MOR-CORE env vars."
    requires_migrations_checks = True
    stealth_options = ("stdin",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.UserModel = get_user_model()
        self.username_field = self.UserModel._meta.get_field(
            self.UserModel.USERNAME_FIELD
        )

    def execute(self, *args, **options):
        self.stdin = options.get("stdin", sys.stdin)  # Used for testing
        return super().execute(*args, **options)

    def handle(self, *args, **options):
        name_pattern = re.compile(r"\w+_APPLICATIE_NAME")
        for key, val in os.environ.items():
            if name_pattern.match(key):
                try:
                    app_name = os.environ.get(key)
                    app_url = os.environ.get(f"{app_name.upper()}_APPLICATIE_URL")

                    if Applicatie.objects.filter(naam=app_name).exists():
                        self.logger.info(
                            f"Skipping creation of application {app_name} because it already exists."
                        )
                        continue

                    app_user = self.UserModel.objects.filter(
                        email__icontains=app_name
                    ).first()

                    if not app_user:
                        self.logger.error(
                            f"Application user for {app_name} does not exist."
                        )
                        continue

                    app = Applicatie.objects.create(
                        naam=app_name,
                        basis_url=app_url,
                        valide_basis_urls=[app_url],
                        gebruiker=app_user,
                        applicatie_gebruiker_naam=f"{os.environ.get(f'{app_name.upper()}_USER_USERNAME')}@forzamor.nl",
                        applicatie_gebruiker_wachtwoord=encrypt_gebruiker_wachtwoord(
                            os.environ.get(f"{app_name.upper()}_USER_PASSWORD")
                        ),
                    )
                    app.save()

                    self.logger.info(
                        "Successfully created application: {}".format(app_name)
                    )
                except Exception as e:
                    self.logger.error(e)
