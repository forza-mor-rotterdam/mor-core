# Generated by Django 3.2.18 on 2023-04-11 09:29

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("mor", "0003_auto_20230329_1622"),
    ]

    operations = [
        migrations.CreateModel(
            name="Status",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("aangemaakt_op", models.DateTimeField(auto_now_add=True)),
                ("aangepast_op", models.DateTimeField(auto_now=True)),
                (
                    "naam",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("gemeld", "Nieuw"),
                            ("afwachting", "In afwachting van behandeling"),
                            ("in_behandeling", "In behandeling"),
                            ("on_hold", "On hold"),
                            ("ingepland", "Ingepland"),
                            ("te_verzenden", "Extern: te verzenden"),
                            ("afgehandeld", "Afgehandeld"),
                            ("geannuleerd", "Geannuleerd"),
                            ("heropend", "Heropend"),
                            ("gesplitst", "Gesplitst"),
                            (
                                "verzoek_tot_afhandeling",
                                "Extern: verzoek tot afhandeling",
                            ),
                            ("Reactie gevraagd", "Reactie gevraagd"),
                            ("Reactie ontvangen", "Reactie ontvangen"),
                            ("verzonden", "Extern: verzonden"),
                            ("verzenden_mislukt", "Extern: mislukt"),
                            ("afgehandeld_extern", "Extern: afgehandeld"),
                            ("verzoek_tot_heropenen", "Verzoek tot heropenen"),
                        ],
                        default="gemeld",
                        help_text="Melding status",
                        max_length=50,
                    ),
                ),
                (
                    "omschrijving",
                    models.CharField(blank=True, max_length=5000, null=True),
                ),
                (
                    "melding",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="statussen_voor_melding",
                        to="mor.melding",
                    ),
                ),
            ],
            options={
                "ordering": ("aangemaakt_op",),
            },
        ),
    ]