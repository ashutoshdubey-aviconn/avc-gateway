import logging

import paho.mqtt.client as mqtt

from utils.helpers import update_phase_entry
from wareApp.models import Site, SiteLoadPower

logger = logging.getLogger(__name__)


def _handle_phase(
    client: mqtt.Client,
    msg: mqtt.MQTTMessage,
    site: Site,
    msg_type: list[str],
    suffix: str,
    required_code: str,
) -> bool:
    if len(msg_type) <= 6 or msg_type[6] != required_code:
        return False
    entry = SiteLoadPower.objects.filter(
        Associated_Site=site,
        Meter_Number=int(msg_type[4]) if len(msg_type) > 4 else 0,
    )
    if not entry.exists():
        return True
    payload_str = msg.payload.decode("utf-8") if isinstance(msg.payload, (bytes, bytearray)) else str(msg.payload)
    updated = update_phase_entry(entry, msg_type[5], suffix, payload_str)
    if updated is not None:
        logger.info("Phase %s %s updated as %s.", msg_type[5], suffix, updated)
    return True


def handle_power_factor_message(client: mqtt.Client, msg: mqtt.MQTTMessage, site: Site, msg_type: list[str]) -> bool:
    return _handle_phase(client, msg, site, msg_type, "power_factor", "4")
