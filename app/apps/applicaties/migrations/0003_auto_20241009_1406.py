# Generated by Django 3.2.19 on 2024-10-09 12:06

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("applicaties", "0002_applicatie_valide_basis_urls"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="applicatie",
            name="onderwerpen",
        ),
        migrations.RemoveField(
            model_name="applicatie",
            name="taaktypes",
        ),
    ]