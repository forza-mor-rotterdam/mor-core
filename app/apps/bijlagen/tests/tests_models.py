import os
import shutil

from apps.bijlagen.models import Bijlage
from apps.meldingen.models import Melding
from django.test import TestCase, override_settings
from django.utils import timezone


class BijlageCase(TestCase):
    @override_settings(THUMBNAIL_DEBUG=True, THUMBNAIL_CACHE_TIMEOUT=0)
    def setUp(self):
        shutil.copy2(
            "/app/apps/bijlagen/tests/bestanden/afbeelding.jpg", "/media/afbeelding.jpg"
        )
        shutil.copy2(
            "/app/apps/bijlagen/tests/bestanden/IMG_1714.HEIC", "/media/afbeelding.heic"
        )
        melding = Melding.objects.create(origineel_aangemaakt=timezone.now())
        Bijlage.objects.create(
            bestand="/media/afbeelding.jpg",
            content_object=melding,
        )

    def test_bestand_exists(self):
        bijlage = Bijlage.objects.first()

        self.assertTrue(bijlage.bestand)
        self.assertTrue(os.path.exists(bijlage.bestand.path))

    def test_aanmaken_afbeelding_versie(self):
        bijlage = Bijlage.objects.first()
        bijlage.filefield_leegmaken(bijlage.afbeelding)
        bijlage.filefield_leegmaken(bijlage.afbeelding_verkleind)
        bijlage.save()
        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        self.assertTrue(bijlage.afbeelding)
        self.assertTrue(os.path.exists(bijlage.afbeelding.path))

    def test_aanmaken_afbeelding_verkleind_versie(self):
        bijlage = Bijlage.objects.first()
        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        self.assertTrue(bijlage.afbeelding_verkleind)
        self.assertTrue(os.path.exists(bijlage.afbeelding_verkleind.path))

    def test_aanmaken_afbeelding_versies_empty_imagefields(self):
        bijlage = Bijlage.objects.first()
        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        bijlage.afbeelding = None
        bijlage.afbeelding_verkleind = None
        bijlage.save()

        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        self.assertTrue(bijlage.afbeelding)
        self.assertTrue(bijlage.afbeelding_verkleind)
        self.assertTrue(os.path.exists(bijlage.afbeelding.path))
        self.assertTrue(os.path.exists(bijlage.afbeelding_verkleind.path))

    def test_aanmaken_afbeelding_versies_file_removed(self):
        bijlage = Bijlage.objects.first()
        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        os.remove(bijlage.afbeelding.path)
        os.remove(bijlage.afbeelding_verkleind.path)

        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        self.assertTrue(bijlage.afbeelding)
        self.assertTrue(bijlage.afbeelding_verkleind)
        self.assertTrue(os.path.exists(bijlage.afbeelding.path))
        self.assertTrue(os.path.exists(bijlage.afbeelding_verkleind.path))

    def test_opruimen_jpg(self):
        bijlage = Bijlage.objects.first()

        bijlage.filefield_leegmaken(bijlage.afbeelding)
        bijlage.filefield_leegmaken(bijlage.afbeelding_verkleind)
        bijlage.save()
        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        bijlage = Bijlage.objects.get(id=bijlage.id)

        verwijder_bestanden = bijlage.opruimen()
        bijlage.save()

        self.assertTrue(bijlage.afbeelding)
        self.assertTrue(bijlage.afbeelding_verkleind)
        self.assertEqual(len(verwijder_bestanden), 0)

    def test_opruimen_heic(self):
        melding = Melding.objects.first()
        bijlage = Bijlage.objects.create(
            bestand="/media/afbeelding.heic",
            content_object=melding,
        )

        bijlage.filefield_leegmaken(bijlage.afbeelding)
        bijlage.filefield_leegmaken(bijlage.afbeelding_verkleind)
        bijlage.save()
        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        bijlage = Bijlage.objects.get(id=bijlage.id)

        verwijder_bestanden = bijlage.opruimen()
        bijlage.save()

        self.assertTrue(bijlage.afbeelding)
        self.assertTrue(bijlage.afbeelding_verkleind)
        self.assertEqual(len(verwijder_bestanden), 1)
