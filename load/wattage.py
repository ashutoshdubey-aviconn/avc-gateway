import logging
import time

import paho.mqtt.client as mqtt
from django.utils import timezone

from constants.topics import load_data_state_topic
from utils.payload import build_wattage_load_message
from wareApp.models import LoadData, Site, SiteLoadPower

logger = logging.getLogger(__name__)


def handle_wattage(client: mqtt.Client, msg: mqtt.MQTTMessage, msg_type: list[str], message: str) -> bool:
    if "WATTAGE" not in msg_type:
        return False
    try:
        site = Site.objects.first()
        load_power = float(message)
        load_entry = SiteLoadPower.objects.filter(
            Associated_Site=site,
            Meter_Number=int(msg_type[3]) if len(msg_type) > 3 else 0,
            Status="ON",
        )
        if load_entry.exists():
            load_entry.update(Site_Total_Load=load_power)
    except Exception as e:
        logger.exception("Exception in wattage block: %s", e)
    return True


def handle_wattage_load(client: mqtt.Client, msg: mqtt.MQTTMessage, msg_type: list[str], message: str) -> bool:
    if "WATTAGELOAD" not in msg_type:
        return False
    try:
        site = Site.objects.first()
        load_power = float(message)
        time_now = timezone.now()
        epochTime = round(time.time() * 1000)
        load_entry = LoadData.objects.filter(
            Associated_Site=site,
            Meter_Number=int(msg_type[3]) if len(msg_type) > 3 else 0,
        )
        if not load_entry.exists():
            return True
        leg_id = load_entry[0].leg_id
        load_entry.update(
            site_total_load=load_power,
            Updated_on=time_now,
            epochTime=epochTime,
        )
        from utils.helpers import get_default_site_id, get_home_gateway_hgw_id

        site_id_cached = get_default_site_id()
        gw_hgw_id = get_home_gateway_hgw_id()
        if site_id_cached is None or gw_hgw_id is None:
            return True
        topictosend = load_data_state_topic(site_id_cached, gw_hgw_id)
        msg_payload = build_wattage_load_message(
            load_power,
            leg_id,
            msg_type[3] if len(msg_type) > 3 else "",
            time_now.strftime("%Y-%m-%d %H:%M:%S.%f"),
            epochTime,
        )
        if load_power > 0:
            client.publish(topictosend, msg_payload, qos=0, retain=False)
    except Exception as e:
        logger.exception("Exception in wattage load block: %s", e)
    return True
