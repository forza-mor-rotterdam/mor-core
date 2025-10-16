import prometheus_client
from apps.authenticatie.auth import TokenAuthentication
from apps.meldingen.metrics_collectors import CustomCollector
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect


def root(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect("/admin/")
    if request.user.is_authenticated:
        return HttpResponse("Geen rechten")
    return HttpResponse("Niet geauthentiseerd, ga naar /login/")


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
    # from django.shortcuts import redirect, render
    # return render(request, "base.html", {"content": metrics_page})
    return HttpResponse(
        metrics_page, content_type=prometheus_client.CONTENT_TYPE_LATEST
    )
