"""
Module mqtt.client2

Flow:
Top-level functions:
- start_client
"""

from typing import dict

import paho.mqtt.client as mqtt
from celery.utils.log import get_task_logger

from constants.mqtt import BROKER_HOST, BROKER_KEEPALIVE, BROKER_PORT, CLIENT2_ID
from mqtt.router import route_message

logger = get_task_logger(__name__)


def start_client() -> None:
    def on_connect(client: mqtt.Client, userdata: object, flags: dict[str, int], rc: int) -> None:
        """MQTT on_connect callback for client2.

        Subscribes to control topics published under the `Acclivate` prefix.
        """
        logger.info("Connected with result code %s", rc)
        client.subscribe("/Acclivate/iOmniControl/#")

    def on_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        """MQTT on_message callback: delegate to the central router."""
        route_message(client, msg)

    client = mqtt.Client(client_id=CLIENT2_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, BROKER_KEEPALIVE)
    logger.info("MQTT Client is Running >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    client.loop_forever()
