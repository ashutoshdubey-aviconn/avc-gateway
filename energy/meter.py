import os
import re
import time

import paho.mqtt.client as mqtt

from datetime import datetime, timedelta
from celery.utils.log import get_task_logger

from wareApp.models import *

logger = get_task_logger(__name__)


def handle_meter_message(
    client,
    site,
    message,
    message_for,
    msg_type,
    current_time,
    location_id,
):

    if msg_type[6] == "0":  # This is to calculate the energy consumption.

        return calculate_energy(
            client,
            site,
            message,
            message_for,
            msg_type,
            current_time,
            location_id,
        )
        print("Calculating energy for {}.".format(msg_type[3]))
        try:
            print("This is the for meter energy.")
            incoming_meter_reading = float(message)
            dateHourLowerLimitCheck = current_time.replace(
                hour=int(current_time.hour), minute=0, second=0, microsecond=0
            )
            dateHourUpperLimitCheck = current_time.replace(
                hour=int(current_time.hour), minute=59, second=59, microsecond=0
            )
            print(dateHourLowerLimitCheck)
            print(dateHourUpperLimitCheck)
            meter_reading_entry = MeterReadings.objects.filter(reading_of=message_for)
            leg_id = SmartEnergyDevices.objects.filter(topic=message_for)[0].leg_id
            aisle_grp = AisleGroup.objects.filter(aisle_grp_id=leg_id)
            topictosend = (
                "/Acclivate/iOmniControl/"
                + str(Site.objects.first().id)
                + "/"
                + HomeGatewayId.objects.first().hgw_id
                + "/in/"
                + "consumption"
                + "/state"
            )
            if meter_reading_entry.exists():
                previous_meter_reading_value = float(
                    meter_reading_entry[0].previous_reading_value
                )
                if incoming_meter_reading >= previous_meter_reading_value:
                    leg = meter_reading_entry[0].reading_of.split("_")[3]
                    print("Now calculating consumption for {}.".format(leg))
                    new_unit_consumption = (
                        float(incoming_meter_reading - previous_meter_reading_value)
                        / 1000
                    )
                    print(
                        "Unit consumption for this leg is {}.".format(
                            str(new_unit_consumption)
                        )
                    )
                    hourly_entry = HourlySiteReading.objects.filter(
                        associated_Site=int(location_id),
                        leg_id=leg_id,
                        reading_from__gte=dateHourLowerLimitCheck,
                        reading_from__lte=dateHourUpperLimitCheck,
                    )
                    daily_entry = DailySiteReading.objects.filter(
                        associated_Site=int(location_id),
                        leg_id=leg_id,
                        reading_for=current_time.date(),
                    )
                    print(
                        "Now checking condition for entry or update in hourly reading."
                    )
                    dateHourLowerLimitCheck1 = dateHourLowerLimitCheck - timedelta(
                        hours=1
                    )
                    dateHourUpperLimitCheck1 = dateHourUpperLimitCheck - timedelta(
                        hours=1
                    )
                    previous_hour_entry = HourlySiteReading.objects.filter(
                        associated_Site=int(location_id),
                        leg_id=leg_id,
                        reading_from__gte=dateHourLowerLimitCheck1,
                        reading_from__lte=dateHourUpperLimitCheck1,
                    )
                    time_difference_in_readings = (
                        current_time - meter_reading_entry[0].updated_on
                    ).total_seconds()
                    print("time difference : ", time_difference_in_readings)
                    print("leg id is : ", leg_id)
                    print("aisle_ grp object: ", aisle_grp)
                    new_cumulative_consumption = (
                        aisle_grp[0].cumulative_consumption + new_unit_consumption
                    )
                    print(
                        "new cumulative consumption  is : ",
                        new_cumulative_consumption,
                    )

                    if hourly_entry.exists() and previous_hour_entry.exists():
                        print("inside hourly and previous hourly entry exist case")
                        new_consumption = (
                            hourly_entry[0].unit_consumption + new_unit_consumption
                        )
                        hourly_entry.update(unit_consumption=new_consumption)
                        aisle_grp.update(
                            cumulative_consumption=new_cumulative_consumption
                        )
                        meter_reading_entry.update(
                            previous_reading_value=incoming_meter_reading,
                            updated_on=current_time,
                        )
                        print(
                            "The hourly reading for leg id {} is updated".format(leg_id)
                        )
                        print("Meter reading also updated for {}".format(message_for))
                        payload = (
                            "Consumption_time_in_sec :"
                            + str(time_difference_in_readings)
                            + ",Unit_consumption :"
                            + str(new_unit_consumption)
                            + ",saving :0.0"
                            + ",Message_time :"
                            + str(current_time)
                            + ",Leg_Meter_Reading :"
                            + str(msg_type[3])
                            + "_"
                            + str(message)
                            + ",Current_Hour_total_consumption :"
                            + str(hourly_entry[0].unit_consumption)
                            + ",AisleGrp_id :"
                            + str(leg_id)
                            + ",GW_Total_Cumulative :"
                            + str(aisle_grp[0].cumulative_consumption)
                            + ",Previous_hour_total_consumption :"
                            + str(previous_hour_entry[0].unit_consumption)
                            + ",Rc :1"
                        )

                    else:
                        if hourly_entry.exists():
                            print("updating first hourly entry")
                            new_consumption = (
                                hourly_entry[0].unit_consumption + new_unit_consumption
                            )
                            hourly_entry.update(unit_consumption=new_consumption)
                            aisle_grp.update(
                                cumulative_consumption=new_cumulative_consumption
                            )
                            meter_reading_entry.update(
                                previous_reading_value=incoming_meter_reading,
                                updated_on=current_time,
                            )
                            print(
                                "The hourly reading for leg id {} is updated".format(
                                    leg_id
                                )
                            )
                            print(
                                "Meter reading also updated for {}".format(message_for)
                            )
                            previous_hour_entry = 0.0
                            payload = (
                                "Consumption_time_in_sec :"
                                + str(time_difference_in_readings)
                                + ",Unit_consumption :"
                                + str(new_unit_consumption)
                                + ",saving :0.0"
                                + ",Message_time :"
                                + str(current_time)
                                + ",Leg_Meter_Reading :"
                                + str(msg_type[3])
                                + "_"
                                + str(message)
                                + ",Current_Hour_total_consumption :"
                                + str(hourly_entry[0].unit_consumption)
                                + ",AisleGrp_id :"
                                + str(leg_id)
                                + ",GW_Total_Cumulative :"
                                + str(aisle_grp[0].cumulative_consumption)
                                + ",Previous_hour_total_consumption :"
                                + str(previous_hour_entry)
                                + ",Rc :1"
                            )

                        else:
                            print("Creating new hourly entry for {}.".format(leg))
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
                            aisle_grp.update(
                                cumulative_consumption=new_cumulative_consumption
                            )
                            print(
                                "New hourly entry for leg id {} is created.".format(
                                    leg_id
                                )
                            )
                            if previous_hour_entry.exists():
                                previous_hour_units = str(
                                    previous_hour_entry[0].unit_consumption
                                )
                            else:
                                previous_hour_units = "0"
                            payload = (
                                "Consumption_time_in_sec :"
                                + str(time_difference_in_readings)
                                + ",Unit_consumption :"
                                + str(new_unit_consumption)
                                + ",saving :0.0"
                                + ",Message_time :"
                                + str(current_time)
                                + ",Leg_Meter_Reading :"
                                + str(msg_type[3])
                                + "_"
                                + str(message)
                                + ",Current_Hour_total_consumption :"
                                + previous_hour_units
                                + ",AisleGrp_id :"
                                + str(leg_id)
                                + ",GW_Total_Cumulative :"
                                + str(new_unit_consumption)
                                + ",Previous_hour_total_consumption :"
                                + previous_hour_units
                                + ",Rc :1"
                            )

                    print(
                        "Now checking condition for entry or update in daily reading."
                    )
                    if (
                        daily_entry.exists()
                    ):  # This is the logic for daily site reading.
                        print("Updating daily consumption data.")
                        new_consumption = (
                            daily_entry[0].unit_consumption + new_unit_consumption
                        )
                        daily_entry.update(unit_consumption=new_consumption)
                        print("The reading for leg id {} is updated".format(leg_id))

                    else:
                        print("Creating new daily consumption entry.")
                        DailySiteReading.objects.create(
                            associated_Site=site,
                            aisle_group=aisle_grp[0],
                            leg_id=leg_id,
                            unit_consumption=new_unit_consumption,
                            reading_for=current_time.date(),
                        )
                        print(
                            "New daily entry for leg id {} is created.".format(leg_id)
                        )
                else:
                    print("ERROR!!!")
                    print(
                        "New meter reading for energy of leg_id {} is smaller than previous meter reading.".format(
                            leg_id
                        )
                    )
                    payload = (
                        "ERROR!!!  "
                        + "New meter reading for energy of aisle group id "
                        + str(leg_id)
                        + " is smaller than previous meter reading."
                    )
                client.publish(topictosend, payload, qos=0, retain=False)
            else:
                print("Setting the first reference reading for this leg.")
                MeterReadings.objects.create(
                    local_meterId=int(msg_type[4]),
                    reading_for=0,
                    reading_of=str(message_for),
                    previous_reading_value=str(message),
                    updated_on=datetime.now(),
                )
                print("Reference reading set for leg {}.".format(msg_type[3]))

        except Exception as e:
            print("This is the exception in consumption block : {}".format(e))
