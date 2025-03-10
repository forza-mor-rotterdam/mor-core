import logging
import mimetypes
import os
import shutil
from os.path import exists

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.sites.models import Site
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener
from rest_framework.reverse import reverse
from sorl.thumbnail import get_thumbnail
from utils.images import get_upload_path
from utils.models import BasisModel

logger = logging.getLogger(__name__)


class Bijlage(BasisModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    bestand = models.FileField(
        upload_to=get_upload_path, null=False, blank=False, max_length=255
    )
    afbeelding = models.ImageField(
        upload_to=get_upload_path, null=True, blank=True, max_length=255
    )
    afbeelding_verkleind = models.ImageField(
        upload_to=get_upload_path, null=True, blank=True, max_length=255
    )

    mimetype = models.CharField(max_length=30, blank=False, null=False)
    is_afbeelding = models.BooleanField(default=False)
    opgeruimd_op = models.DateTimeField(null=True, blank=True)

    class BestandPadFout(Exception):
        ...

    class AfbeeldingVersiesAanmakenFout(Exception):
        ...

    class MinifyOrigeelBestandFout(Exception):
        ...

    def _is_afbeelding(self):
        try:
            Image.open(self.bestand)
        except UnidentifiedImageError:
            return False
        return True

    def _heic_to_jpeg(self, file_field):
        register_heif_opener()

        with Image.open(file_field.path) as image:
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Remove .heic extension and add .jpg
            new_file_name = f"{os.path.splitext(file_field.name)[0]}.jpg"

            image.save(os.path.join(settings.MEDIA_ROOT, new_file_name), "JPEG")

        return new_file_name

    def bijlage_paded(self):
        paden = []
        for f in ["bestand", "afbeelding", "afbeelding_verkleind"]:
            field = getattr(self, f)
            if field:
                if os.path.isfile(field.path):
                    paden.append(field.path)
        return paden

    @property
    def afbeelding_versies_ontbreken(self):
        return (
            not self.afbeelding.name
            or not self.afbeelding.storage.exists(self.afbeelding.name)
        ) or (
            not self.afbeelding_verkleind.name
            or not self.afbeelding_verkleind.storage.exists(
                self.afbeelding_verkleind.name
            )
        )

    def opruimen(self):
        verwijder_bestanden = []
        if self.is_afbeelding and self.afbeelding and not self.opgeruimd_op:
            bestand_path = self.bestand.path
            afbeelding_path = self.afbeelding.path
            bestand_name = self.bestand.name
            if os.path.getsize(bestand_path) > os.path.getsize(afbeelding_path):
                new_bestand_name = f"{os.path.splitext(bestand_name)[0]}.jpg"
                new_bestand_path = os.path.join(settings.MEDIA_ROOT, new_bestand_name)
                shutil.copy2(afbeelding_path, new_bestand_path)
                self.bestand = new_bestand_name
                _, ext = os.path.splitext(bestand_path)
                if ext == ".heic":
                    verwijder_bestanden.append(bestand_path)
            self.opgeruimd_op = timezone.now()
        return verwijder_bestanden

    def filefield_leegmaken(self, field):
        if bool(field.name) and field.storage.exists(field.name):
            os.remove(field.path)
        field.name = None

    def aanmaken_afbeelding_versies(self):
        mt = mimetypes.guess_type(self.bestand.path, strict=True)
        if exists(self.bestand.path):
            bestand = self.bestand.path
            self.is_afbeelding = self._is_afbeelding()
            if mt:
                self.mimetype = mt[0]
            if self.mimetype == "image/heic":
                bestand = self._heic_to_jpeg(self.bestand)
                self.is_afbeelding = True
            if self.is_afbeelding:
                try:
                    self.afbeelding_verkleind.name = get_thumbnail(
                        bestand,
                        settings.THUMBNAIL_KLEIN,
                        format="JPEG",
                        quality=99,
                    ).name
                    self.afbeelding.name = get_thumbnail(
                        bestand,
                        settings.THUMBNAIL_STANDAARD,
                        format="JPEG",
                        quality=80,
                    ).name
                    if self.mimetype == "image/heic":
                        print(f"remove: {bestand}")
                        os.remove(os.path.join(settings.MEDIA_ROOT, bestand))
                except Exception as e:
                    raise Bijlage.AfbeeldingVersiesAanmakenFout(
                        f"aanmaken_afbeelding_versies: get_thumbnail fout: {e}"
                    )
        else:
            raise Bijlage.BestandPadFout(
                f"aanmaken_afbeelding_versies: bestand path bestaat niet, bijlage id: {self.pk}"
            )

    def get_absolute_url(self):
        domain = Site.objects.get_current().domain
        url_basis = f"{settings.PROTOCOL}://{domain}{settings.PORT}"
        pad = reverse(
            "v1:bijlage-detail",
            kwargs={"uuid": self.uuid},
        )
        return f"{url_basis}{pad}"

    class Meta:
        verbose_name = "Bijlage"
        verbose_name_plural = "Bijlagen"
