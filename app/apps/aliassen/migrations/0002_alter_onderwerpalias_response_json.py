# Generated by Django 3.2.19 on 2024-10-09 12:06

import utils.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("aliassen", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="onderwerpalias",
            name="response_json",
            field=utils.fields.DictJSONField(blank=True, default=dict, null=True),
        ),
    ]
