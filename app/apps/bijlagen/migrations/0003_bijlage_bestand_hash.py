# Generated by Django 4.2.15 on 2025-03-25 10:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bijlagen", "0002_bijlage_opgeruimd_op"),
    ]

    operations = [
        migrations.AddField(
            model_name="bijlage",
            name="bestand_hash",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
