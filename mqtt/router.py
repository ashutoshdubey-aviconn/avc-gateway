from datetime import datetime

from wareApp.models import Site
from constants.power import PHASE_SUFFIX_MAP
from gateway.autossh import handle_remote_access
from gateway.recovery import handle_sync_message
from load.current import handle_current_message
from load.power_factor import handle_power_factor_message
from load.runtime import handle_load_time
from load.source import handle_source_message
from load.voltage import handle_voltage_message
from load.wattage import handle_wattage, handle_wattage_load
from energy.apparent_enery import handle_apparent
from energy.meter import handle_meter_connection, handle_meter_energy
from mqtt.topic_parser import normalize_payload, parse_mqtt_topic


def route_message(client, msg):
    print("######################")
    print("Topic: ", msg.topic, " Message: ", msg.payload)
    print("######################")

    message = normalize_payload(msg.payload)
    parsed = parse_mqtt_topic(msg.topic)
    msg_type = parsed.get("msg_type", [])
    msg_subtype = parsed.get("msg_subtype")
    message_for = parsed.get("message_for")
    location_id = parsed.get("location_id")

    if not msg_type:
        return

    if handle_remote_access(client, msg, message, msg_type):
        return

    if handle_sync_message(
        client,
        msg,
        message,
        msg_type,
        msg_subtype,
        None if location_id is None else Site.objects.filter(id=location_id).first(),
        datetime.now(),
    ):
        return

    if location_id is None or message_for is None:
        return

    site = Site.objects.filter(id=location_id).first()
    if not site:
        return

    current_time = datetime.now()

    if "meter" in msg_type[0]:
        if handle_meter_connection(client, msg, message, message_for, msg_type):
            return

    if "METER" in msg_type:
        handle_meter_energy(
            client, msg, message, message_for, msg_type, site, current_time
        )

        if site.site_type == 1:
            if len(msg_type) > 6:
                phase_code = msg_type[6]
                if phase_code == "2":
                    handle_voltage_message(client, msg, site, msg_type)
                elif phase_code == "3":
                    handle_current_message(client, msg, site, msg_type)
                elif phase_code == "4":
                    handle_power_factor_message(client, msg, site, msg_type)

            handle_source_message(client, msg, site, msg_type, message)
            handle_load_time(
                client, msg, site, msg_type, message_for, message, current_time
            )
            handle_wattage(client, msg, msg_type, message)
            handle_wattage_load(client, msg, msg_type, message)
            handle_apparent(
                client,
                msg,
                message_for,
                msg_type,
                site,
                current_time,
                message,
                location_id,
            )
