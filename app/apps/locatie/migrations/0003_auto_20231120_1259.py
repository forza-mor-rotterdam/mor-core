# Generated by Django 3.2.19 on 2023-11-20 11:59

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("locatie", "0002_auto_20230825_0942"),
    ]

    operations = [
        migrations.AddField(
            model_name="locatie",
            name="gebruiker",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="locatie_voor_gebruiker",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="locatie",
            name="gewicht",
            field=models.FloatField(default=0.2),
        ),
    ]
