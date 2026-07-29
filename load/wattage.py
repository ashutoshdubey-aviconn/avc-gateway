import logging
import time
from datetime import datetime
from typing import Optional

import paho.mqtt.client as mqtt

from constants.topics import load_data_state_topic
from utils.payload import build_wattage_load_message
from wareApp.models import HomeGatewayId, LoadData, Site, SiteLoadPower

logger = logging.getLogger(__name__)


def handle_wattage(client: mqtt.Client, msg: mqtt.MQTTMessage, msg_type: list[str], message: str) -> bool:
    if "WATTAGE" not in msg_type:
        return False
    try:
        site = Site.objects.all()[0]
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
        site = Site.objects.all()[0]
        load_power = float(message)
        time_now = datetime.now()
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
        topictosend = load_data_state_topic(
            Site.objects.all()[0].id,
            HomeGatewayId.objects.first().hgw_id,
        )
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
