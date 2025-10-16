import logging
import uuid

from apps.applicaties.models import Applicatie
from django.conf import settings
from django.db import DatabaseError, IntegrityError
from health_check.backends import BaseHealthCheckBackend
from health_check.db.models import TestModel
from health_check.exceptions import ServiceReturnedUnexpectedResult, ServiceUnavailable

logger = logging.getLogger(__name__)


class ApplicatieTokenAPIHealthCheck(BaseHealthCheckBackend):
    critical_service = True

    def check_status(self):
        results = []
        result_waardes = (
            "Niet compleet",
            "Ok",
            "Niet ok",
        )
        result_waardes_niet_ok = (
            # result_waardes[0],
            result_waardes[2],
        )
        for applicatie in Applicatie.objects.all():
            r = {
                "token": None,
                "naam": applicatie.naam,
                "applicatie_data_exists": (
                    applicatie.applicatie_gebruiker_naam
                    and applicatie.applicatie_gebruiker_wachtwoord
                    and applicatie.basis_url
                ),
                "result": None,
            }
            try:
                r["token"] = applicatie.haal_token()
            except Exception as e:
                logger.error(
                    f"Error fetching token for applicatie={applicatie.naam}, e={e}"
                )
            r["result"] = (
                result_waardes[0]
                if not r.get("applicatie_data_exists")
                else result_waardes[2]
                if not r.get("token") and r.get("applicatie_data_exists")
                else result_waardes[1]
            )
            results.append(r)

        niet_ok_results = ", ".join(
            [
                f"{r.get('naam')}({r.get('result')})"
                for r in results
                if r.get("result") in result_waardes_niet_ok
            ]
        )
        if niet_ok_results:
            raise ServiceUnavailable(niet_ok_results)

    def identifier(self):
        return self.__class__.__name__


class ReadonlyDatabaseBackend(BaseHealthCheckBackend):
    def check_status(self):
        title = uuid.uuid4()
        obj = None
        try:
            obj = TestModel.objects.using(settings.DEFAULT_DATABASE_KEY).create(
                title=title
            )
        except IntegrityError:
            raise ServiceReturnedUnexpectedResult("Integrity Error")
        except DatabaseError:
            raise ServiceUnavailable("Database error")
        try:
            TestModel.objects.using(settings.READONLY_DATABASE_KEY).get(title=title)
        except IntegrityError:
            raise ServiceReturnedUnexpectedResult("Integrity Error")
        except DatabaseError:
            raise ServiceUnavailable("Database error")
        except TestModel.DoesNotExist:
            raise ServiceReturnedUnexpectedResult(
                "Object not found in readonly database"
            )

        if obj:
            obj.delete()
