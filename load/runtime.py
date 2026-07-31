"""
Module load.runtime

Flow:
Top-level functions:
- handle_load_time
"""

import logging
from datetime import datetime

import paho.mqtt.client as mqtt
from django.utils import timezone

from constants.topics import supply_time_state_topic
from utils.payload import build_supply_time_payload
from wareApp.models import MeterReadings, MeterSource, Site, SupplyLoadTimeShare

logger = logging.getLogger(__name__)


def handle_load_time(
    client: mqtt.Client,
    msg: mqtt.MQTTMessage,
    site: Site,
    msg_type: list[str],
    message_for: str,
    message: str,
    current_time: datetime,
) -> bool:
    if "TIME" not in msg_type or "LOAD" not in msg_type:
        return False
    try:
        current_load_time_cumulative = float(message)
        last_load_time_cumulative = MeterReadings.objects.filter(
            reading_for=1,
            reading_of=message_for,
        )
        if last_load_time_cumulative.exists():
            previous_load_time_cumulative = float(last_load_time_cumulative[0].previous_reading_value)
            if current_load_time_cumulative >= previous_load_time_cumulative:
                dateHourLowerLimitCheck = current_time.replace(
                    hour=current_time.hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                dateHourUpperLimitCheck = current_time.replace(
                    hour=current_time.hour,
                    minute=59,
                    second=59,
                    microsecond=0,
                )
                if len(msg_type) > 5 and msg_type[5] == "1":
                    meter_source = MeterSource.objects.filter(meter_number=int(msg_type[4])).first()
                    for_power_source = meter_source.power_source_1 if meter_source else None
                elif len(msg_type) > 5 and msg_type[5] == "2":
                    meter_source = MeterSource.objects.filter(meter_number=int(msg_type[4])).first()
                    for_power_source = meter_source.power_source_2 if meter_source else None
                else:
                    return True

                if not for_power_source:
                    return True

                last_load_time_entry = SupplyLoadTimeShare.objects.filter(
                    power_source=for_power_source,
                    reading_from__gte=dateHourLowerLimitCheck,
                    reading_to__lte=dateHourUpperLimitCheck,
                )
                load_time = current_load_time_cumulative - previous_load_time_cumulative
                if last_load_time_entry.exists():
                    current = last_load_time_entry[0]
                    last_load_time_entry.update(hourly_run_time=current.hourly_run_time + load_time)
                    last_load_time_cumulative.update(
                        previous_reading_value=current_load_time_cumulative,
                        updated_on=current_time,
                    )
                else:
                    SupplyLoadTimeShare.objects.create(
                        site=site,
                        power_source=for_power_source,
                        hourly_run_time=load_time,
                        reading_from=dateHourLowerLimitCheck,
                        reading_to=dateHourUpperLimitCheck,
                    )
                    last_load_time_cumulative.update(
                        previous_reading_value=current_load_time_cumulative,
                        updated_on=current_time,
                    )
                created = timezone.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                from utils.helpers import get_default_site_id, get_home_gateway_hgw_id

                site_id_cached = get_default_site_id()
                gw_hgw_id = get_home_gateway_hgw_id()
                if site_id_cached is None or gw_hgw_id is None:
                    logger.warning("Missing site or gateway id for supply_time_state_topic")
                    return True
                topictosend = supply_time_state_topic(site_id_cached, gw_hgw_id)
                msg_payload = build_supply_time_payload(
                    for_power_source,
                    load_time,
                    current_load_time_cumulative,
                    created,
                )
                client.publish(topictosend, msg_payload, qos=0, retain=False)
        else:
            MeterReadings.objects.create(
                local_meterId=int(msg_type[4]) if len(msg_type) > 4 else 0,
                reading_for=1,
                reading_of=message_for,
                previous_reading_value=message,
                updated_on=timezone.now(),
            )
    except Exception as e:
        logger.exception("Exception in load time block: %s", e)
    return True
