from typing import Any

from wareApp.models import (
    AisleGroup,
    DailySiteReading,
    HourlySiteReading,
    MeterReadings,
    SmartEnergyDevices,
)


def handle_apparent(
    client: Any,
    msg: Any,
    message_for: Any,
    msg_type: Any,
    site: Any,
    current_time: Any,
    message: Any,
    location_id: Any,
) -> bool:
    if "APPARENT" not in msg_type:
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

    if meter_reading_entry.exists():
        previous_meter_reading_value = float(meter_reading_entry[0].previous_reading_value)
        if incoming_meter_reading >= previous_meter_reading_value:
            new_unit_consumption = (incoming_meter_reading - previous_meter_reading_value) / 1000
            hourly_entry = HourlySiteReading.objects.filter(
                associated_Site=int(location_id),
                leg_id=leg_id,
                reading_from__gte=dateHourLowerLimitCheck,
                reading_to__lte=dateHourUpperLimitCheck,
            )
            daily_entry = DailySiteReading.objects.filter(
                associated_Site=int(location_id),
                leg_id=leg_id,
                reading_for=current_time.date(),
            )
            if hourly_entry.exists():
                hourly_entry.update(unit_consumption=hourly_entry.first().unit_consumption + new_unit_consumption)
            else:
                HourlySiteReading.objects.create(
                    associated_Site=site,
                    aisle_group=aisle_grp[0],
                    leg_id=leg_id,
                    unit_consumption=new_unit_consumption,
                    reading_from=dateHourLowerLimitCheck,
                    reading_to=dateHourUpperLimitCheck,
                )
            meter_reading_entry.update(
                previous_reading_value=incoming_meter_reading,
                updated_on=current_time,
            )
            aisle_grp.update(cumulative_consumption=aisle_grp[0].cumulative_consumption + new_unit_consumption)
            if daily_entry.exists():
                daily_entry.update(unit_consumption=daily_entry.first().unit_consumption + new_unit_consumption)
            else:
                DailySiteReading.objects.create(
                    associated_Site=site,
                    aisle_group=aisle_grp[0],
                    leg_id=leg_id,
                    unit_consumption=new_unit_consumption,
                    reading_for=current_time.date(),
                )
    else:
        MeterReadings.objects.create(
            local_meterId=int(msg_type[4]) if len(msg_type) > 4 else 0,
            reading_for=0,
            reading_of=str(message_for),
            previous_reading_value=str(message),
            updated_on=current_time,
        )
    return True
