# Generated by Django 3.2.19 on 2023-06-08 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("applicaties", "0006_auto_20230602_1526"),
    ]

    operations = [
        migrations.AddField(
            model_name="applicatie",
            name="applicatie_gebruiker_naam",
            field=models.CharField(blank=True, max_length=150, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="applicatie",
            name="applicatie_gebruiker_wachtwoord",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]