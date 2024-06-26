# Generated by Django 3.2.19 on 2024-01-26 10:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signalen", "0002_auto_20240125_1523"),
        ("meldingen", "0005_alter_meldinggebeurtenis_locatie"),
    ]

    operations = [
        migrations.AddField(
            model_name="meldinggebeurtenis",
            name="signaal",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="meldinggebeurtenissen_voor_signaal",
                to="signalen.signaal",
            ),
        ),
        migrations.AlterField(
            model_name="meldinggebeurtenis",
            name="gebeurtenis_type",
            field=models.CharField(
                choices=[
                    ("standaard", "Standaard"),
                    ("status_wijziging", "Status wijziging"),
                    ("melding_aangemaakt", "Melding aangemaakt"),
                    ("taakopdracht_aangemaakt", "Taakopdracht aangemaakt"),
                    ("taakopdracht_status_wijziging", "Taakopdracht status wijziging"),
                    ("locatie_aangemaakt", "Locatie aangemaakt"),
                    ("signaal_toegevoegd", "Signaal toegevoegd"),
                ],
                default="standaard",
                max_length=40,
            ),
        ),
    ]
