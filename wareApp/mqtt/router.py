"""Minimal MQTT router used by tests.

This file provides `route_message` and re-exports the meter handlers from
`wareApp.energy.meter` so unit tests can patch them on the `wareApp.mqtt.router`
module.
"""
import logging
from datetime import datetime

from wareApp.energy.meter import handle_meter_connection, handle_meter_energy
from wareApp.models import Site
from wareApp.mqtt.topic_parser import normalize_payload, parse_mqtt_topic

logger = logging.getLogger(__name__)


def route_message(client, msg):
    """Dispatch MQTT messages to the appropriate handlers.

    Tests only require that METER topics trigger the meter handlers and that
    non-meter topics return without error.
    """
    topic = getattr(msg, "topic", None)
    parsed = parse_mqtt_topic(topic)
    msg_type = parsed.get("msg_type", [])
    if not msg_type or len(msg_type) == 0:
        return None

    # Only handle METER messages here
    if msg_type[0] != "METER":
        return None

    message_for = parsed.get("message_for")
    message = normalize_payload(getattr(msg, "payload", None))

    # First try the connection handler (may return True meaning handled)
    try:
        if handle_meter_connection(client, msg, message, message_for, msg_type):
            return None
    except Exception:
        logger.exception("handle_meter_connection failed")

    # Resolve site if available
    site = None
    loc = parsed.get("location_id")
    if loc is not None:
        try:
            site = Site.objects.filter(id=loc).first()
        except Exception:
            site = None

    # Call energy handler with current time
    try:
        handle_meter_energy(client, msg, message, message_for, msg_type, site, datetime.now())
    except Exception:
        logger.exception("handle_meter_energy failed")

    return None


# Re-export names so tests can patch them on this module
__all__ = ["route_message", "handle_meter_connection", "handle_meter_energy"]
