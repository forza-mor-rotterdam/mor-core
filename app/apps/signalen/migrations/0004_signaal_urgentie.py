# Generated by Django 3.2.19 on 2024-02-19 14:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signalen", "0003_auto_20240127_1706"),
    ]

    operations = [
        migrations.AddField(
            model_name="signaal",
            name="urgentie",
            field=models.FloatField(default=0.2),
        ),
    ]
