# Generated by Django 4.2.15 on 2025-05-06 12:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "locatie",
            "0007_locatie_buurtnaam_wijknaam_idx_locatie_buurtnaam_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddIndex(
            model_name="locatie",
            index=models.Index(fields=["begraafplaats"], name="begraafplaats_idx"),
        ),
        migrations.AddIndex(
            model_name="locatie",
            index=models.Index(fields=["grafnummer"], name="grafnummer_idx"),
        ),
        migrations.AddIndex(
            model_name="locatie",
            index=models.Index(fields=["vak"], name="vak_idx"),
        ),
    ]
