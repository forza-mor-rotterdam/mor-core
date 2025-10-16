import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    exception_class = exc.__class__.__name__

    handlers = {
        "MeldingAfgeslotenFout": [str(exc), status.HTTP_405_METHOD_NOT_ALLOWED],
        "MeldingInGebruik": [str(exc), status.HTTP_423_LOCKED],
        "TaakAanmakenFout": [str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR],
        "TaakStatusAanpassenFout": [str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR],
        "TaaktypesOphalenFout": [str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR],
        "TaakopdrachtInGebruik": [str(exc), status.HTTP_423_LOCKED],
        "UrlFout": [str(exc), status.HTTP_406_NOT_ACCEPTABLE],
        "ApplicatieWerdNietGevondenFout": [
            str(exc),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ],
        "AntwoordFout": [str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR],
    }
    custom_handler = handlers.get(
        exception_class, ["Er ging iets mis", status.HTTP_500_INTERNAL_SERVER_ERROR]
    )

    response = exception_handler(exc, context)

    logger.error(f"exception={str(exc)}")
    if response:
        return response
    return Response({"detail": custom_handler[0]}, status=custom_handler[1])
