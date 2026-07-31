"""
Module load.source

Flow:
Top-level functions:
- handle_source_message
"""

import paho.mqtt.client as mqtt
from django.utils import timezone

from constants.topics import load_state_topic
from utils.helpers import publish_status
from utils.payload import build_source_status_message
from wareApp.models import MeterSource, Site, SiteLoadPower


def handle_source_message(
    client: mqtt.Client,
    msg: mqtt.MQTTMessage,
    site: Site,
    msg_type: list[str],
    message: str,
) -> bool:
    if "SOURCE" not in msg_type:
        return False

    if len(msg_type) < 3:
        return True

    meter_number = int(msg_type[2])
    meter_info = MeterSource.objects.filter(
        Associated_Site=site,
        meter_number=meter_number,
    ).first()
    if not meter_info:
        return True

    power_source_1 = meter_info.get_power_source_1_display()
    power_source_2 = meter_info.get_power_source_2_display()
    power_sources = SiteLoadPower.objects.filter(
        Associated_Site=site,
        Meter_Number=meter_number,
    )
    source_1_entry = power_sources.filter(Supply_Source=power_source_1)
    source_2_entry = power_sources.filter(Supply_Source=power_source_2)

    if meter_info.is_PS2_valid:
        if message == "0":
            target = source_1_entry
            fallback = source_2_entry
            active = power_source_1
        elif message == "1":
            target = source_2_entry
            fallback = source_1_entry
            active = power_source_2
        else:
            return True

        if target.exists():
            target.update(Status="ON", Updated_on=timezone.now())
            if fallback.exists():
                fallback.update(
                    Site_Total_Load=0,
                    r_volt=0,
                    y_volt=0,
                    b_volt=0,
                    r_current=0,
                    y_current=0,
                    b_current=0,
                    r_power_factor=0,
                    y_power_factor=0,
                    b_power_factor=0,
                    Status="OFF",
                    Updated_on=timezone.now(),
                )
        else:
            SiteLoadPower.objects.create(
                Associated_Site=site,
                Meter_Number=meter_number,
                Supply_Source=active,
                Status="ON",
                Updated_on=timezone.now(),
            )
    else:
        if message not in {"0", "1"}:
            return True
        if source_1_entry.exists():
            source_1_entry.update(
                Status="ON" if message == "1" else "OFF",
                Updated_on=timezone.now(),
            )
        else:
            SiteLoadPower.objects.create(
                Associated_Site=site,
                Meter_Number=meter_number,
                Supply_Source=power_source_1,
                Status="ON",
                Updated_on=timezone.now(),
            )

    from utils.helpers import get_default_site_id, get_home_gateway_hgw_id

    site_id_cached = get_default_site_id()
    gw_hgw_id = get_home_gateway_hgw_id()
    if site_id_cached is None or gw_hgw_id is None:
        return True
    topictosend = load_state_topic(site_id_cached, gw_hgw_id)

    if source_1_entry.exists():
        publish_status(client, topictosend, build_source_status_message(source_1_entry.first()))
    if source_2_entry.exists():
        publish_status(client, topictosend, build_source_status_message(source_2_entry.first()))

    return True
