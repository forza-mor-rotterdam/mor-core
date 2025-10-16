from django.conf import settings
from django.utils import timezone


def general_settings(context):
    deploy_date_formatted = None
    if settings.DEPLOY_DATE:
        deploy_date = timezone.datetime.strptime(
            settings.DEPLOY_DATE, "%d-%m-%Y-%H-%M-%S"
        )
        deploy_date_formatted = deploy_date.strftime("%d-%m-%Y %H:%M:%S")
    return {
        "GIT_SHA": settings.GIT_SHA,
        "DEPLOY_DATE": deploy_date_formatted,
    }
