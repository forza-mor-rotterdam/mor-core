import logging

from apps.applicaties.models import Applicatie
from django.contrib import admin, messages
from django.core.cache import cache

logger = logging.getLogger(__name__)


class TaakapplicatieAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "naam",
        "gebruiker",
    )

    def save_model(self, request, obj, form, change):
        if obj.pk:
            logger.info(f"Delete cache key: obj pk: {obj.pk}")
            cache.delete(obj.get_token_cache_key())
            logger.info(f"Get application object: obj pk: {obj.pk}")
            orig_obj = Applicatie.objects.get(pk=obj.pk)
            if (
                obj.applicatie_gebruiker_wachtwoord
                != orig_obj.applicatie_gebruiker_wachtwoord
            ):
                logger.info(f"Try to encrypt password: obj pk: {obj.pk}")
                try:
                    obj.encrypt_applicatie_gebruiker_wachtwoord(
                        obj.applicatie_gebruiker_wachtwoord
                    )
                except Exception as e:
                    logger.error(f"Encryption error: {e}, obj pk: {obj.pk}")

        elif obj.applicatie_gebruiker_wachtwoord:
            try:
                obj.encrypt_applicatie_gebruiker_wachtwoord(
                    obj.applicatie_gebruiker_wachtwoord
                )
            except Exception as e:
                logger.error(f"Encryption error: {e}")

        try:
            if obj._get_token():
                messages.success(request, "Connectie met de applicatie is gelukt")
            else:
                messages.error(request, "Connectie met de applicatie is mislukt!")
        except Exception:
            messages.error(request, "Connectie met de applicatie is mislukt!")

        obj.save()


admin.site.register(Applicatie, TaakapplicatieAdmin)
