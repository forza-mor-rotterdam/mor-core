import os
import shutil

from apps.bijlagen.models import Bijlage
from apps.meldingen.models import Melding
from django.test import TestCase
from django.utils import timezone


class BijlageCase(TestCase):
    # @override_settings(MEDIA_ROOT="/media")

    def setUp(self):
        shutil.copy2(
            "/app/apps/bijlagen/tests/bestanden/afbeelding.jpg", "/media/afbeelding.jpg"
        )

        melding = Melding.objects.create(origineel_aangemaakt=timezone.now())
        Bijlage.objects.create(
            bestand="/media/afbeelding.jpg",
            content_object=melding,
        )

    def test_aanmaken_afbeelding_versies(self):
        bijlage = Bijlage.objects.first()
        bijlage.aanmaken_afbeelding_versies()

        self.assertTrue(bijlage.afbeelding)
        self.assertTrue(bijlage.afbeelding_verkleind)

    def test_opruimen(self):
        bijlage = Bijlage.objects.first()

        # result = task_aanmaken_afbeelding_versies.delay(bijlage.id)
        # print(result)
        bijlage.aanmaken_afbeelding_versies()
        bijlage.save()

        import time

        time.sleep(5)
        bijlage = Bijlage.objects.get(id=bijlage.id)
        print(os.path.exists(bijlage.afbeelding.path))
        print(os.path.exists(bijlage.afbeelding_verkleind.path))
        print(bijlage.afbeelding.path)
        print(bijlage.afbeelding_verkleind.path)
        # while not os.path.exists(bijlage.afbeelding.path):
        # bijlage.save()
        # print(bijlage.afbeelding_verkleind.path)

        # from os import walk
        # time.sleep(5)
        # filenames = next(walk("/media/afbeeldingen/2025/03/03/"), (None, None, []))[2]  # [] if no file
        # filenames2 = next(walk("./media/afbeeldingen/2025/03/03/"), (None, None, []))[2]  # [] if no file
        # print(filenames)
        # print(filenames2)
        # import glob

        # print(glob.glob('/media/**/afbeelding_1480x1480.jpg', recursive=True))

        self.assertTrue(bijlage.afbeelding)
        self.assertTrue(bijlage.afbeelding_verkleind)

        # r = task_bijlage_opruimen.delay(bijlage.id)
        # print(r)
        bijlage.opruimen()

        # print(bijlage.afbeelding)
        # print(bijlage.afbeelding_verkleind)

        self.assertFalse(bijlage.afbeelding)
        self.assertFalse(bijlage.afbeelding_verkleind)
