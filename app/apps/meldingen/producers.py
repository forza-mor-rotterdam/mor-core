import json
import logging
import os

import pika
from apps.meldingen.serializers import (
    ProducerMessageMeldingTaakopdrachtSerializer,
    ProducerMessageTaakopdrachtSerializer,
)

logger = logging.getLogger(__name__)


class BasisProducer:
    def __init__(self) -> None:
        self.channel = None
        self.MESSAGE_BUS_URL = os.getenv("MESSAGE_BUS_URL")
        self.MESSAGE_EXCHANGE = os.getenv("MESSAGE_EXCHANGE", "morcore")
        if not self.MESSAGE_BUS_URL or not self.MESSAGE_EXCHANGE:
            logger.error(
                f"MESSAGE_BUS_URL en/of MESSAGE_EXCHANGE zijn niet gezet: MESSAGE_BUS_URL={self.MESSAGE_EXCHANGE}, MESSAGE_BUS_URL={self.MESSAGE_EXCHANGE}"
            )
            return
        try:
            connection = pika.BlockingConnection(
                pika.connection.URLParameters(self.MESSAGE_BUS_URL)
            )
            self.channel = connection.channel()
        except Exception:
            logger.error(
                f"Er ging iets mis met het opzetten van de rabbitmq verbinding: MESSAGE_BUS_URL={self.MESSAGE_BUS_URL}"
            )
            return

    def _publish(self, routing_key, data):
        if not self.channel:
            return
        try:
            self.channel.basic_publish(
                exchange=self.MESSAGE_EXCHANGE, routing_key=routing_key, body=data
            )
        except Exception:
            logger.error(
                f"Er ging iets mis met het publiseren van de message: MESSAGE_EXCHANGE={self.MESSAGE_EXCHANGE}, routing_key={routing_key}, body={data}"
            )
            return


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
