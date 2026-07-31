"""
Module mqtt.router

Flow:
Top-level functions:
- route_message: Central MQTT routing entrypoint.
"""

import logging

import paho.mqtt.client as mqtt
from django.utils import timezone

from constants.topics import BASE_TOPIC_PREFIX
from energy.apparent_enery import handle_apparent
from energy.meter import handle_meter_connection, handle_meter_energy
from gateway.autossh import handle_remote_access
from gateway.recovery import handle_sync_message
from load.current import handle_current_message
from load.power_factor import handle_power_factor_message
from load.runtime import handle_load_time
from load.source import handle_source_message
from load.voltage import handle_voltage_message
from load.wattage import handle_wattage, handle_wattage_load
from mqtt.topic_parser import normalize_payload, parse_mqtt_topic
from wareApp.models import Site

logger = logging.getLogger(__name__)


def route_message(client: mqtt.Client, msg: mqtt.MQTTMessage) -> None:
    """Central MQTT routing entrypoint.

    - Normalizes payload
    - Parses topic into parts
    - Short-circuits for remote access or sync messages
    - Delegates to handler modules
    """

    message = normalize_payload(msg.payload)
    logger.debug("MQTT message received: topic=%s payload=%s", msg.topic, message)

    # Ignore locally-generated state messages published to the server topic
    # (local storage publishes raw data to /asem/aviconn/ and handlers publish
    # processed state to /Acclivate/iOmniControl/.../state). Avoid re-processing
    # those state messages which would otherwise create processing loops.
    if isinstance(msg.topic, str) and msg.topic.startswith(BASE_TOPIC_PREFIX) and msg.topic.endswith("/state"):
        logger.debug("Ignoring local state topic to avoid reprocessing: %s", msg.topic)
        return

    parsed = parse_mqtt_topic(msg.topic)
    msg_type = parsed.get("msg_type", [])
    msg_subtype = parsed.get("msg_subtype")
    message_for = parsed.get("message_for")
    location_id = parsed.get("location_id")

    if not msg_type:
        return

    # Remote access can short-circuit routing
    if handle_remote_access(client, msg, message, msg_type):
        return

    # Cache site lookup to avoid repeated DB queries
    site_obj: Site | None = None
    if location_id is not None:
        site_obj = Site.objects.filter(id=location_id).first()

    # Only run sync/recovery handler for specific recovery subtypes
    if msg_subtype in ("consumption", "loadTime") and handle_sync_message(
        client, msg, message, msg_type, msg_subtype, site_obj, timezone.now()
    ):
        return

    if site_obj is None or message_for is None:
        return

    current_time = timezone.now()

    # Allow case-insensitive detection of 'meter' prefix in the first msg_type
    first_type_lower = str(msg_type[0]).lower() if msg_type else ""
    if "meter" in first_type_lower:  # noqa: SIM102
        if handle_meter_connection(client, msg, message, message_for, msg_type):
            return

    if "METER" in msg_type:
        handle_meter_energy(client, msg, message, message_for, msg_type, site_obj, current_time)

        if site_obj.site_type == 1:
            if len(msg_type) > 6:
                phase_code = msg_type[6]
                if phase_code == "2":
                    handle_voltage_message(client, msg, site_obj, msg_type)
                elif phase_code == "3":
                    handle_current_message(client, msg, site_obj, msg_type)
                elif phase_code == "4":
                    handle_power_factor_message(client, msg, site_obj, msg_type)

            handle_source_message(client, msg, site_obj, msg_type, message)
            handle_load_time(client, msg, site_obj, msg_type, message_for, message, current_time)
            handle_wattage(client, msg, msg_type, message)
            handle_wattage_load(client, msg, msg_type, message)
            handle_apparent(
                client,
                msg,
                message_for,
                msg_type,
                site_obj,
                current_time,
                message,
                location_id,
            )
