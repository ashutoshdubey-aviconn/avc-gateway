import paho.mqtt.client as mqtt
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


def start_client():
    """
    Start the MQTT client and connect to the broker.
    Business logic will be handled in the on_message callback function.
    """
    client = mqtt.Client(client_id="paho_client_1")

    client.connect("127.0.0.1", 5003, 60)
    logger.info("MQTT Client connected to broker at 127.0.0.1:5003")
    client.loop_forever()
