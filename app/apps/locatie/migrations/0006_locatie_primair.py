# Generated by Django 3.2.19 on 2024-09-11 17:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("locatie", "0005_auto_20240822_1150"),
    ]

    operations = [
        migrations.AddField(
            model_name="locatie",
            name="primair",
            field=models.BooleanField(default=False),
        ),
    ]
