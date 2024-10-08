import prometheus_client
from apps.authenticatie.auth import TokenAuthentication
from apps.meldingen.metrics_collectors import CustomCollector
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect


@login_required
def login_required_view(request):
    return HttpResponseRedirect(redirect_to="/admin/")


def serve_protected_media(request):
    user = TokenAuthentication().authenticate(request)
    if user or settings.ALLOW_UNAUTHORIZED_MEDIA_ACCESS:
        url = request.path.replace("media", "media-protected")
        response = HttpResponse("")
        response["X-Accel-Redirect"] = url
        response["Content-Type"] = ""
        return response
    return HttpResponseForbidden()


def prometheus_django_metrics(request):
    registry = prometheus_client.CollectorRegistry()
    registry.register(CustomCollector())
    metrics_page = prometheus_client.generate_latest(registry)
    return HttpResponse(
        metrics_page, content_type=prometheus_client.CONTENT_TYPE_LATEST
    )
