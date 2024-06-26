# Generated by Django 3.2.19 on 2023-06-29 13:48

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Melder",
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
                ("naam", models.CharField(blank=True, max_length=100, null=True)),
                ("voornaam", models.CharField(blank=True, max_length=50, null=True)),
                ("achternaam", models.CharField(blank=True, max_length=50, null=True)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                (
                    "telefoonnummer",
                    models.CharField(blank=True, max_length=17, null=True),
                ),
            ],
            options={
                "verbose_name": "Melder",
                "verbose_name_plural": "Melders",
            },
        ),
    ]
