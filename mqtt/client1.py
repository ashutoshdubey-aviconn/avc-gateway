"""
Module mqtt.client1

Flow:
Top-level functions:
- start_client: Start the MQTT client and connect to the broker.
"""

import logging
from logging.handlers import RotatingFileHandler
from typing import Dict

import paho.mqtt.client as mqtt
from celery.utils.log import get_task_logger

from constants.mqtt import BROKER_HOST, BROKER_KEEPALIVE, BROKER_PORT, CLIENT1_ID
from mqtt.router import route_message

# Configure a rotating file logger for MQTT messages and routing
log_path = "logs/mqtt_messages.log"
handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)
root_logger = logging.getLogger()
if not any(
    isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == handler.baseFilename
    for h in root_logger.handlers
):
    root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

logger = get_task_logger(__name__)


def start_client() -> None:
    """
    Start the MQTT client and connect to the broker.
    Business logic is handled in the on_message callback.
    """

    def on_connect(client: mqtt.Client, userdata: object, flags: Dict[str, int], rc: int) -> None:
        """MQTT on_connect callback.

        Subscribes to the local telemetry prefix (`/asem/aviconn/#`) and the
        cloud/control prefix (`/Acclivate/iOmniControl/#`) when the broker
        connection is established.
        """
        logger.info("Connected with result code %s", rc)
        client.subscribe("/asem/aviconn/#")
        client.subscribe("/Acclivate/iOmniControl/#", 1)

    def on_message(client: mqtt.Client, userdata: object, msg: mqtt.MQTTMessage) -> None:
        """MQTT on_message callback.

        For each incoming message, delegate routing/processing to
        `mqtt.router.route_message` which performs topic parsing, filtering and
        dispatch to domain-specific handlers.
        """
        route_message(client, msg)

    client = mqtt.Client(client_id=CLIENT1_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, BROKER_KEEPALIVE)
    logger.info("MQTT Client is Running >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    client.loop_forever()
