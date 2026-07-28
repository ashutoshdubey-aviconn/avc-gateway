from mqtt.client1 import start_client as start_client1
from mqtt.client2 import start_client as start_client2
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(name="mqtt_client1")
def mqtt_client1():
    start_client1()


@shared_task(name="mqtt_client2")
def mqtt_client2():
    start_client2()
