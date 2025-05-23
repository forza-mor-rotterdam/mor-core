# Generated by Django 4.2.15 on 2025-05-06 13:39

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("meldingen", "0020_melding_bijlage"),
    ]

    operations = [
        migrations.RunSQL("DROP VIEW IF EXISTS dwh_meldingen_melding;"),
        migrations.RunSQL(
            """CREATE VIEW dwh_meldingen_melding AS
                SELECT id,
                    uuid,
                    aangemaakt_op,
                    aangepast_op,
                    origineel_aangemaakt,
                    afgesloten_op,
                    meta - 'melderNaamField'::text - 'melderEmailField'::text - 'melderTelefoonField'::text - 'adoptantnummerField'::text AS meta,
                        CASE
                            WHEN (meta ->> 'melderEmailField'::text) ~~* '%@rotterdam.nl'::text THEN 1
                            ELSE 0
                        END AS rotterdam_email,
                        CASE
                            WHEN (meta ->> 'adoptantnummerField'::text) <> '0'::text AND (meta ->> 'adoptantnummerField'::text) <> ''::text THEN 1
                            ELSE 0
                        END AS has_adoptantnummer,
                    (meta ->> 'kanaalField'::text) AS meta__kanaal_field,
                    (meta ->> 'omschrijvingField'::text) AS meta__omschrijving_field,
                    (meta ->> 'meldingsnummerField'::text) AS meta__meldinsgnummer_field,
                    (meta ->> 'aanvullendeInformatieField'::text) AS meta__aanvullende_informatie_field,
                    resolutie,
                    status_id,
                    urgentie
                FROM meldingen_melding
            ;"""
        ),
        migrations.RunSQL("GRANT SELECT ON TABLE dwh_meldingen_melding TO dwh;"),
        migrations.RunSQL(
            "GRANT SELECT ON TABLE dwh_meldingen_melding TO CURRENT_ROLE;"
        ),
        migrations.RunSQL("DROP VIEW IF EXISTS dwh_status_status;"),
        migrations.RunSQL(
            """CREATE VIEW dwh_status_status AS
                SELECT
                    id,
                    uuid,
                    aangemaakt_op,
                    aangepast_op,
                    naam,
                    melding_id
                FROM status_status
            ;"""
        ),
        migrations.RunSQL("GRANT SELECT ON TABLE dwh_status_status TO dwh;"),
        migrations.RunSQL("GRANT SELECT ON TABLE dwh_status_status TO CURRENT_ROLE;"),
        migrations.RunSQL("DROP VIEW IF EXISTS dwh_locatie_locatie;"),
        migrations.RunSQL(
            """CREATE VIEW dwh_locatie_locatie AS
                SELECT id,
                    uuid,
                    aangemaakt_op,
                    aangepast_op,
                    locatie_type,
                    geometrie,
                    ST_Y(geometrie) AS lat,
                    ST_X(geometrie) AS lon,
                    bron,
                    naam,
                    straatnaam,
                    huisnummer,
                    huisletter,
                    toevoeging,
                    postcode,
                    lichtmast_id,
                    plaatsnaam,
                    begraafplaats,
                    grafnummer,
                    vak,
                    melding_id,
                    buurtnaam,
                    wijknaam,
                    gebruiker_id,
                    gewicht,
                    signaal_id
                FROM locatie_locatie
            ;"""
        ),
        migrations.RunSQL("GRANT SELECT ON TABLE dwh_locatie_locatie TO dwh;"),
        migrations.RunSQL("GRANT SELECT ON TABLE dwh_locatie_locatie TO CURRENT_ROLE;"),
    ]
