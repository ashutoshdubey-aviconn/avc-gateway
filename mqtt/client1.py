import time

import paho.mqtt.client as mqtt
from celery.utils.log import get_task_logger
from constants.mqtt import BROKER_HOST, BROKER_PORT, BROKER_KEEPALIVE, CLIENT1_ID
from mqtt.router import route_message

logger = get_task_logger(__name__)


def start_client():
    """
    Start the MQTT client and connect to the broker.
    Business logic is handled in the on_message callback.
    """

    def on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe("/asem/aviconn/#")
        client.subscribe("/Acclivate/iOmniControl/#", 1)

    def on_message(client, userdata, msg):
        route_message(client, msg)

    client = mqtt.Client(client_id=CLIENT1_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, BROKER_KEEPALIVE)
    logger.info("MQTT Client is Running >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    client.loop_forever()
