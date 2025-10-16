from django.db import migrations, models


def calculate_afhandeltijd(apps, schema_editor):
    taakopdracht_model = apps.get_model("taken", "Taakopdracht")
    for taakopdracht in taakopdracht_model.objects.all():
        if taakopdracht.afgesloten_op and taakopdracht.aangemaakt_op:
            taakopdracht.afhandeltijd = (
                taakopdracht.afgesloten_op - taakopdracht.aangemaakt_op
            )
        else:
            taakopdracht.afhandeltijd = None
        taakopdracht.save()


class Migration(migrations.Migration):
    dependencies = [
        ("taken", "0007_auto_20231214_1732"),
    ]

    operations = [
        migrations.AddField(
            model_name="taakopdracht",
            name="afhandeltijd",
            field=models.DurationField(blank=True, null=True),
        ),
        migrations.RunPython(calculate_afhandeltijd),
    ]
