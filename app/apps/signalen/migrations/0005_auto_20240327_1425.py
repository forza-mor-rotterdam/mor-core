# Generated by Django 3.2.19 on 2024-03-27 13:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signalen", "0004_signaal_urgentie"),
    ]

    operations = [
        migrations.RenameField(
            model_name="signaal",
            old_name="omschrijving",
            new_name="aanvullende_informatie",
        ),
        migrations.RenameField(
            model_name="signaal",
            old_name="omschrijving_kort",
            new_name="omschrijving_melder",
        ),
        migrations.AddField(
            model_name="signaal",
            name="aanvullende_vragen",
            field=models.JSONField(default=list),
        ),
    ]