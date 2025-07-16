import json
import os

import pika
from apps.meldingen.serializers import (
    ProducerMessageMeldingTaakopdrachtSerializer,
    ProducerMessageTaakopdrachtSerializer,
)


class BasisProducer:
    def __init__(self) -> None:
        connection = pika.BlockingConnection(
            pika.connection.URLParameters(os.getenv("RABBITMQ_URL"))
        )
        self.channel = connection.channel()

    def _publish(self, routing_key, data):
        self.channel.basic_publish(
            exchange=os.getenv("RABBITMQ_EXCHANGE"), routing_key=routing_key, body=data
        )


class TaakopdrachtAangemaaktProducer(BasisProducer):
    entity = "taakopdracht"
    action = "aangemaakt"

    def publish(self, melding, taakgebeurtenis):
        print("TaakopdrachtAangemaaktProducer: Sending to RabbitMQ: ")
        print(taakgebeurtenis)
        self.uuid = taakgebeurtenis.taakopdracht.uuid

        routing_key = f"{self.entity}.{self.uuid}.{self.action}"

        serializer = ProducerMessageTaakopdrachtSerializer(
            {
                "entity": self.entity,
                "action": self.action,
                "melding": melding,
                "uuid": self.uuid,
                "taakopdracht": taakgebeurtenis.taakopdracht,
                "data": {
                    "user": taakgebeurtenis.gebruiker,
                },
            }
        )

        self._publish(routing_key, json.dumps(serializer.data))


class TaakopdrachtVeranderdProducer(BasisProducer):
    entity = "melding"
    action = "taakopdrachten_veranderd"

    def publish(self, melding, taakgebeurtenis):
        print("TaakopdrachtVeranderdProducer: Sending to RabbitMQ: ")
        print(taakgebeurtenis)
        self.uuid = melding.uuid

        routing_key = f"{self.entity}.{self.uuid}.{self.action}"

        serializer = ProducerMessageMeldingTaakopdrachtSerializer(
            {
                "entity": self.entity,
                "action": self.action,
                "melding": melding,
                "uuid": melding.uuid,
                "taakopdracht": taakgebeurtenis.taakopdracht,
                "onderwerp": melding.onderwerpen.first(),
                "signalen": melding.signalen_voor_melding.all(),
                "data": {"user": taakgebeurtenis.gebruiker},
            }
        )
        self._publish(routing_key, json.dumps(serializer.data))
