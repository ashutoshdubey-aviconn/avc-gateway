"""
Module energy.meter

Flow:
Top-level functions:
- handle_meter_connection
- handle_meter_energy
"""

import logging
from datetime import datetime

import paho.mqtt.client as mqtt

from constants.topics import consumption_state_topic
from utils.helpers import publish_status
from utils.payload import build_consumption_payload
from wareApp.models import (
    AisleGroup,
    DailySiteReading,
    HourlySiteReading,
    MeterReadings,
    Site,
    SmartEnergyDevices,
)

logger = logging.getLogger(__name__)


def handle_meter_connection(
    client: mqtt.Client,
    msg: mqtt.MQTTMessage,
    message: str,
    message_for: str,
    msg_type: list[str],
) -> bool:
    if message not in {"Disconnected", "Connected"}:
        return False
    topictosend = msg.topic.replace("localstate", "state").replace("asem", "Acclivate")
    client.publish(topictosend, message, qos=0, retain=False)
    return True


def handle_meter_energy(
    client: mqtt.Client,
    msg: mqtt.MQTTMessage,
    message: str,
    message_for: str,
    msg_type: list[str],
    site: Site,
    current_time: datetime,
) -> bool:
    if len(msg_type) <= 6 or msg_type[6] != "0":
        return False
    try:
        incoming_meter_reading = float(message)
    except (TypeError, ValueError):
        return True

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

    meter_reading_entry = MeterReadings.objects.filter(reading_of=message_for)
    device = SmartEnergyDevices.objects.filter(topic=message_for).first()
    if not device:
        return True

    leg_id = device.leg_id
    aisle_grp = AisleGroup.objects.filter(aisle_grp_id=leg_id)
    if not aisle_grp.exists():
        return True
    aisle_group = aisle_grp.first()

    if not meter_reading_entry.exists():
        MeterReadings.objects.create(
            local_meterId=int(msg_type[4]) if len(msg_type) > 4 else 0,
            reading_for=0,
            reading_of=message_for,
            previous_reading_value=str(message),
            updated_on=current_time,
        )
        return True

    previous_reading = meter_reading_entry.first()
    previous_value = float(previous_reading.previous_reading_value)
    previous_updated_on = previous_reading.updated_on

    from utils.helpers import get_home_gateway_hgw_id

    gw_hgw_id = get_home_gateway_hgw_id()
    if gw_hgw_id is None:
        logger.warning("Missing home gateway id for consumption topic")
        return True
    topictosend = consumption_state_topic(site.id, gw_hgw_id)

    if incoming_meter_reading < previous_value:
        payload = (
            "ERROR!!!  New meter reading for energy of aisle group id "
            + str(leg_id)
            + " is smaller than previous meter reading."
        )
        publish_status(client, topictosend, payload)
        return True

    new_unit_consumption = (incoming_meter_reading - previous_value) / 1000

    hourly_entry = HourlySiteReading.objects.filter(
        associated_Site=site,
        leg_id=leg_id,
        reading_from__gte=dateHourLowerLimitCheck,
        reading_from__lte=dateHourUpperLimitCheck,
    )
    daily_entry = DailySiteReading.objects.filter(
        associated_Site=site,
        leg_id=leg_id,
        reading_for=current_time.date(),
    )

    if hourly_entry.exists():
        hourly_object = hourly_entry.first()
        hourly_entry.update(unit_consumption=hourly_object.unit_consumption + new_unit_consumption)
    else:
        HourlySiteReading.objects.create(
            associated_Site=site,
            aisle_group=aisle_group,
            leg_id=leg_id,
            unit_consumption=new_unit_consumption,
            reading_from=dateHourLowerLimitCheck,
            reading_to=dateHourUpperLimitCheck,
        )

    aisle_group.cumulative_consumption += new_unit_consumption
    aisle_group.save(update_fields=["cumulative_consumption"])
    meter_reading_entry.update(
        previous_reading_value=incoming_meter_reading,
        updated_on=current_time,
    )

    if daily_entry.exists():
        daily_object = daily_entry.first()
        daily_entry.update(unit_consumption=daily_object.unit_consumption + new_unit_consumption)
    else:
        DailySiteReading.objects.create(
            associated_Site=site,
            aisle_group=aisle_group,
            leg_id=leg_id,
            unit_consumption=new_unit_consumption,
            reading_for=current_time.date(),
        )

    time_difference_in_readings = 0.0
    if previous_updated_on is not None:
        time_difference_in_readings = (current_time - previous_updated_on).total_seconds()

    payload = build_consumption_payload(time_difference_in_readings, new_unit_consumption)
    publish_status(client, topictosend, payload)
    return True
