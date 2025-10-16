"""
Management utility to create superusers.
"""

import base64
import os
import random

import requests
import urllib3
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from faker import Faker


class NotRunningInTTYException(Exception):
    pass


PASSWORD_FIELD = "password"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--token",
            help="Gebruiker token",
        )
        parser.add_argument(
            "--env-url",
            help="Waar moeten de meldingen aangemaakt worden",
        )
        parser.add_argument(
            "--aantal",
            help="Hoeveel meldingen moeten er aangemaakt worden",
        )

    def handle(self, *args, **options):
        base_url = options.get("env_url")
        aantal = options.get("aantal", 1) if options.get("aantal") else 1

        data = {
            "melder": {
                "voornaam": "string",
                "achternaam": "string",
                "email": "user@example.com",
                "telefoonnummer": "string",
            },
            "origineel_aangemaakt": "2023-03-09T11:56:04.036Z",
            "tekst": "string",
            "ruwe_informatie": {
                "vak": "kuhi",
                "labels": {
                    "vak": {"label": "Vak", "choices": None},
                    "fotos": {"label": "Foto's", "choices": None},
                    "aannemer": {
                        "label": "Wie heeft het verzoek aangenomen?",
                        "choices": {
                            "": "Selecteer een medewerker",
                            "onbekend": "Onbekend",
                        },
                    },
                    "no_email": {
                        "label": "De melder beschikt niet over een e-mailadres.",
                        "choices": None,
                    },
                    "categorie": {
                        "label": "Categorie",
                        "choices": {
                            "1": "Verzakking eigen graf",
                            "2": "Verzakking algemeen",
                            "3": "Snoeien",
                            "4": "Beplanting",
                            "5": "Schoonmaken",
                            "6": "Verdwenen materiaal",
                            "7": "Gaten",
                            "8": "Wespennest",
                            "9": "Konijnen",
                            "10": "Muizen",
                            "11": "Zerk reinigen",
                            "12": "Overig",
                        },
                    },
                    "grafnummer": {"label": "Grafnummer", "choices": None},
                    "naam_melder": {"label": "Naam", "choices": None},
                    "toelichting": {"label": "Toelichting", "choices": None},
                    "email_melder": {"label": "E-mailadres", "choices": None},
                    "begraafplaats": {
                        "label": "Begraafplaats",
                        "choices": {
                            "": "Selecteer een begraafplaats",
                            "1": "Begraafplaats Crooswijk",
                            "2": "Begraafplaats Hoek van Holland",
                            "3": "Begraafplaats en crematorium Hofwijk",
                            "4": "Begraafplaats Oudeland, Hoogvliet",
                            "5": "Begraafplaats Oud-Hoogvliet",
                            "6": "Begraafplaats Oud-Overschie",
                            "7": "Begraafplaats Oud-Pernis",
                            "8": "Begraafplaats Oud-Schiebroek",
                            "9": "Begraafplaats Pernis",
                            "10": "Begraafplaats Rozenburg",
                            "11": "Zuiderbegraafplaats",
                        },
                    },
                    "rechthebbende": {
                        "label": "Is deze persoon de rechthebbende of belanghebbende?",
                        "choices": {"0": "Nee", "1": "Ja", "2": "Onbekend"},
                    },
                    "specifiek_graf": {
                        "label": "Betreft het verzoek een specifiek graf?",
                        "choices": {"0": "Nee", "1": "Ja"},
                    },
                    "naam_overledene": {
                        "label": "Naam overledene",
                        "choices": None,
                    },
                    "telefoon_melder": {
                        "label": "Telefoonnummer",
                        "choices": None,
                    },
                    "terugkoppeling_gewenst": {
                        "label": "Is terugkoppeling gewenst?",
                        "choices": {"0": "Nee", "11": "Ja"},
                    },
                },
                "aannemer": "onbekend",
                "no_email": False,
                "categorie": ["1", "4"],
                "grafnummer": "jhgnjk",
                "naam_melder": "mliuyi",
                "toelichting": "lmiuyi",
                "email_melder": "m@m.nl",
                "begraafplaats": "2",
                "rechthebbende": "0",
                "specifiek_graf": "1",
                "naam_overledene": "mkh",
                "telefoon_melder": "kuhiuo",
                "terugkoppeling_gewenst2": "0",
            },
            "bron": "mock_bron",
        }

        def randomize(d):
            onderwerpen_choices = (
                d.get("ruwe_informatie", {})
                .get("labels", {})
                .get("categorie", {})
                .get("choices", {})
            )
            begraafplaats_choices = (
                d.get("ruwe_informatie", {})
                .get("labels", {})
                .get("begraafplaats", {})
                .get("choices", {})
            )
            medewerker_choices = {
                "1": "C.M. Hendriks",
                "2": "A. van de Graaf",
                "3": "I. Addicks",
                "4": "A.J. Verhoeven",
                "5": "M. van Berkum",
                "onbekend": "Onbekend",
            }
            begraafplaats_choices.pop("", None)
            d["onderwerpen"] = [
                f"{base_url}/api/v1/onderwerp/{slugify(onderwerpen_choices.get(random.choice(list(onderwerpen_choices.keys()))))}/"
            ]
            d["onderwerpen"] = (
                d["onderwerpen"]
                + [
                    f"{base_url}/api/v1/onderwerp/{slugify(onderwerpen_choices.get(random.choice(list(onderwerpen_choices.keys()))))}/"
                ]
                if random.choice([0, 0, 0, 1])
                else d["onderwerpen"]
            )
            d["ruwe_informatie"]["begraafplaats"] = random.choice(
                list(begraafplaats_choices.keys())
            )
            d["ruwe_informatie"]["grafnummer"] = str(random.choice(range(1, 200)))
            d["ruwe_informatie"]["specifiek_graf"] = str(random.choice(["Ja", "Nee"]))
            d["ruwe_informatie"]["aannemer"] = medewerker_choices.get(
                random.choice(list(medewerker_choices.keys()))
            )
            d["ruwe_informatie"]["terugkoppeling_gewenst"] = str(
                random.choice(["Ja", "Nee"])
            )
            d["ruwe_informatie"]["rechthebbende"] = str(
                random.choice(["Ja", "Nee", "Onbekend"])
            )
            d["ruwe_informatie"]["vak"] = str(random.choice(list("ABCDEFGHIJKLMNOP")))
            d["ruwe_informatie"]["naam_overledene"] = get_name()
            d["ruwe_informatie"]["naam_melder"] = get_name()
            d["ruwe_informatie"]["email_melder"] = get_email()
            d["ruwe_informatie"]["telefoon_melder"] = get_phone_number()
            d["melder"]["voornaam"] = ""
            d["melder"]["achternaam"] = ""
            d["melder"]["email"] = get_email()
            d["melder"]["naam"] = get_name()
            d["melder"]["telefoonnummer"] = get_phone_number()
            d["ruwe_informatie"]["toelichting"] = get_paragraph()
            d["tekst"] = get_paragraph()
            d["origineel_aangemaakt"] = get_past_datetime().isoformat()
            d["bijlagen"] = [{"bestand": _to_base64(random.choice(files))}]

            return d

        headers = {
            "Authorization": f"Token {options['token']}",
            "user-agent": urllib3.util.SKIP_HEADER,
        }

        dir_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "bestanden/"
        )
        files = [
            os.path.join(dir_path, f)
            for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))
        ]
        for i in range(0, int(aantal)):
            d = randomize(data)
            requests.post(
                f"{base_url}/api/v1/signaal/",
                json=d,
                headers=headers,
            )


def _to_base64(file):
    with open(file, "rb") as binary_file:
        binary_file_data = binary_file.read()
        base64_encoded_data = base64.b64encode(binary_file_data)
        base64_message = base64_encoded_data.decode("utf-8")
    return base64_message


def get_street_name():
    fake = Faker()
    return fake.street_name()


def get_past_datetime():
    fake = Faker()
    return fake.past_datetime()


def get_building_number():
    fake = Faker()
    return fake.building_number()


def get_url():
    fake = Faker()
    return fake.url()


def get_postal_code():
    fake = Faker()
    postal_codes = range(1000, 1109)
    return f"{str(random.choice(postal_codes))}{fake.bothify(text='??').upper()}"


def get_phone_number():
    fake = Faker()
    return fake.msisdn()


def get_sentence():
    fake = Faker()
    return fake.sentence(nb_words=2)


def get_paragraph():
    fake = Faker()
    return fake.paragraph(nb_sentences=2)


def get_name():
    fake = Faker()
    return fake.name()


def get_first_name():
    fake = Faker()
    return fake.first_name()


def get_last_name():
    fake = Faker()
    return fake.last_name()


def get_email():
    fake = Faker()
    return fake.ascii_email()
