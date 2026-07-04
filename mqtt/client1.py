import os
import re
import time

import paho.mqtt.client as mqtt

from datetime import datetime, timedelta
from celery.utils.log import get_task_logger

from wareApp.models import *

logger = get_task_logger(__name__)


def start_client():
    """
    Start the MQTT client and connect to the broker.
    Business logic will be handled in the on_message callback function.
    """

    def on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe("/asem/aviconn/#")
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        # client.subscribe("/sem/iOmniControl/#", 1)
        client.subscribe("/Acclivate/iOmniControl/#", 1)
        # client.subscribe("/sem/iOmniControl/+/+/+/+/state", 1)

    def on_message(client, userdata, msg):
        print("######################")
        print("Topic: ", msg.topic + "  Message: " + str(msg.payload))
        print("######################")
        message = str(msg.payload).split("'")[1]
        head = msg.topic
        gw_id = (head.split("/"))[4]
        print(gw_id)
        message_for = head.split("/")[6]
        print("This reading is for : {}".format(message_for))
        msg_type = message_for.split("_")
        print("This is the message type: {}".format(msg_type))
        location_id = head.split("/")[3]
        site = Site.objects.get(id=int(location_id))
        print("Location Id is : {}".format(int(location_id)))
        current_time = datetime.now()
        if "meter" in msg_type[0]:
            if message == "Disconnected":
                print("This is the disconnected meter {}.".format(message_for))
                topictosend = msg.topic.replace("localstate", "state").replace(
                    "asem", "Acclivate"
                )
                client.publish(topictosend, msg, qos=0, retain=False)
                return
            elif message == "Connected":
                print("This is {} in connection.".format(message_for))
                topictosend = msg.topic.replace("localstate", "state").replace(
                    "asem", "Acclivate"
                )
                client.publish(topictosend, msg, qos=0, retain=False)

        if "METER" in msg_type:
            if msg_type[6] == "0":  # This is to calculate the energy consumption.
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
                    meter_reading_entry = MeterReadings.objects.filter(
                        reading_of=message_for
                    )
                    leg_id = SmartEnergyDevices.objects.filter(topic=message_for)[
                        0
                    ].leg_id
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
                                float(
                                    incoming_meter_reading
                                    - previous_meter_reading_value
                                )
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
                            dateHourLowerLimitCheck1 = (
                                dateHourLowerLimitCheck - timedelta(hours=1)
                            )
                            dateHourUpperLimitCheck1 = (
                                dateHourUpperLimitCheck - timedelta(hours=1)
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
                                aisle_grp[0].cumulative_consumption
                                + new_unit_consumption
                            )
                            print(
                                "new cumulative consumption  is : ",
                                new_cumulative_consumption,
                            )

                            if hourly_entry.exists() and previous_hour_entry.exists():
                                print(
                                    "inside hourly and previous hourly entry exist case"
                                )
                                new_consumption = (
                                    hourly_entry[0].unit_consumption
                                    + new_unit_consumption
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
                                    "Meter reading also updated for {}".format(
                                        message_for
                                    )
                                )
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
                                        hourly_entry[0].unit_consumption
                                        + new_unit_consumption
                                    )
                                    hourly_entry.update(
                                        unit_consumption=new_consumption
                                    )
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
                                        "Meter reading also updated for {}".format(
                                            message_for
                                        )
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
                                    print(
                                        "Creating new hourly entry for {}.".format(leg)
                                    )
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
                                    daily_entry[0].unit_consumption
                                    + new_unit_consumption
                                )
                                daily_entry.update(unit_consumption=new_consumption)
                                print(
                                    "The reading for leg id {} is updated".format(
                                        leg_id
                                    )
                                )

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
                                    "New daily entry for leg id {} is created.".format(
                                        leg_id
                                    )
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

            if (
                site.site_type == 1
            ):  # These calculations are required only for WH_Metering.
                if msg_type[6] == "2":  # This is to publish the phase wise voltage.
                    try:
                        print(
                            "This is for Instantaneous Voltage for site {}.".format(
                                site
                            )
                        )
                        voltage_entry = SiteLoadPower.objects.filter(
                            Associated_Site=site, Meter_Number=int(msg_type[4])
                        )
                        if voltage_entry.exists():
                            if msg_type[5] == "1":
                                r_volt = float(msg.payload)
                                print("This is the R-phase voltage value: ", r_volt)
                                print("Updating the R-phase voltage.")
                                voltage_entry.update(r_volt=r_volt)
                                print("R-phase voltage updated as {}.".format(r_volt))

                            elif msg_type[5] == "2":
                                y_volt = float(msg.payload)
                                print("This is the Y-phase voltage value: ", y_volt)
                                print("Updating the Y-phase voltage.")
                                voltage_entry.update(y_volt=y_volt)
                                print("Y-phase voltage updated as {}.".format(y_volt))

                            elif msg_type[5] == "3":
                                b_volt = float(msg.payload)
                                print("This is the B-phase voltage value: ", b_volt)
                                print("Updating the B-phase voltage.")
                                voltage_entry.update(b_volt=b_volt)
                                print("B-phase voltage updated as {}.".format(b_volt))

                            else:
                                print("This is unknown value")
                        else:
                            print(
                                "Site load entry for this meter has not been created yet!"
                            )

                    except Exception as e:
                        print("This is the exception : {}".format(e))

                elif msg_type[6] == "3":  # This is to publish the phase wise current.
                    try:
                        print(
                            "This is for Instantaneous Current for site {}.".format(
                                site
                            )
                        )
                        current_entry = SiteLoadPower.objects.filter(
                            Associated_Site=site, Meter_Number=int(msg_type[4])
                        )
                        if current_entry.exists():
                            if msg_type[5] == "1":
                                r_current = float(msg.payload)
                                print("This is the R-phase current value: ", r_current)
                                print("Updating the R-phase current.")
                                current_entry.update(r_current=r_current)
                                print(
                                    "R-phase current updated as {}.".format(r_current)
                                )

                            elif msg_type[5] == "2":
                                y_current = float(msg.payload)
                                print("This is the Y-phase current value: ", y_current)
                                print("Updating the Y-phase current.")
                                current_entry.update(y_current=y_current)
                                print(
                                    "Y-phase current updated as {}.".format(y_current)
                                )

                            elif msg_type[5] == "3":
                                b_current = float(msg.payload)
                                print("This is the B-phase current value: ", b_current)
                                print("Updating the B-phase current.")
                                current_entry.update(b_current=b_current)
                                print(
                                    "B-phase current updated as {}.".format(b_current)
                                )

                        else:
                            print(
                                "Site load entry for this meter has not been created yet!"
                            )

                    except Exception as e:
                        print("This is the exception : {}".format(e))

                elif (
                    msg_type[6] == "4"
                ):  # This is to publish for phase wise power factor
                    try:
                        print("This is for Power Factor for site {}.".format(site))
                        power_factor_entry = SiteLoadPower.objects.filter(
                            Associated_Site=site, Meter_Number=int(msg_type[4])
                        )
                        if power_factor_entry.exists():
                            if msg_type[5] == "1":
                                r_power_factor = float(msg.payload)
                                print("This is the R phase Power Factor.")
                                print("Updating the R phase Power Factor")
                                power_factor_entry.update(r_power_factor=r_power_factor)
                                print(
                                    "R-phase power factor updated as {}.".format(
                                        r_power_factor
                                    )
                                )

                            elif msg_type[5] == "2":
                                y_power_factor = float(msg.payload)
                                print("This is the Y phase Power Factor.")
                                print("Updating the Y phase Power Factor")
                                power_factor_entry.update(y_power_factor=y_power_factor)
                                print(
                                    "Y-phase power factor updated as {}.".format(
                                        y_power_factor
                                    )
                                )

                            elif msg_type[5] == "3":
                                b_power_factor = float(msg.payload)
                                print("This is the B phase Power Factor.")
                                print("Updating the B phase Power Factor")
                                power_factor_entry.update(b_power_factor=b_power_factor)
                                print(
                                    "B-phase power factor updated as {}.".format(
                                        b_power_factor
                                    )
                                )

                        else:
                            print(
                                "Site load entry for this meter has not been created yet!"
                            )

                    except Exception as e:
                        print("This is the exception : {}".format(e))

        if site.site_type == 1:  # These messages are received only in WHTM Gateway.
            if (
                "SOURCE" in msg_type
            ):  # This is to send the supply source information and publish load power.
                try:
                    print("This is for power supply source information.")
                    meter_number = int(msg_type[2])
                    meter_info = MeterSource.objects.get(
                        Associated_Site=site, meter_number=meter_number
                    )[0]
                    meter_dual_source = meter_info.is_PS2_valid
                    power_source_1 = meter_info.get_power_source_1_display()
                    power_source_2 = meter_info.get_power_source_2_display()
                    power_sources = SiteLoadPower.objects.filter(
                        Associated_Site=site, Meter_Number=meter_number
                    )
                    source_1_entry = power_sources.filter(Supply_Source=power_source_1)
                    source_2_entry = power_sources.filter(Supply_Source=power_source_2)
                    topictosend = (
                        "/Acclivate/iOmniControl/"
                        + str(Site.objects.all()[0].id)
                        + "/"
                        + HomeGatewayId.objects.first().hgw_id
                        + "/in/"
                        + "load"
                        + "/state"
                    )
                    now = datetime.now()
                    created = now.strftime("%Y-%m-%d %H:%M:%S.%f")
                    if meter_dual_source:
                        if message == "0":
                            if source_1_entry.exists():
                                print("Updating status of {}.".format(power_source_1))
                                source_1_entry.update(
                                    Status="ON", Updated_on=datetime.now()
                                )
                                if source_2_entry.exists():
                                    source_2_entry.update(
                                        Site_Total_Load=0,
                                        r_volt=0,
                                        y_volt=0,
                                        b_volt=0,
                                        r_current=0,
                                        r_power_factor=0,
                                        y_power_factor=0,
                                        b_power_factor=0,
                                        y_current=0,
                                        b_current=0,
                                        Status="OFF",
                                        Updated_on=datetime.now(),
                                    )
                                print("Status updated.")
                            else:
                                print(
                                    "Creating the first entry for power source {}.".format(
                                        power_source_1
                                    )
                                )
                                SiteLoadPower.objects.create(
                                    Associated_Site=site,
                                    Meter_Number=meter_number,
                                    Supply_Source=power_source_1,
                                    Status="ON",
                                    Updated_on=datetime.now(),
                                )
                                print(
                                    "First entry for {} successfully created.".format(
                                        power_source_1
                                    )
                                )

                        elif message == "1":
                            if source_2_entry.exists():
                                print("Updating status of {}.".format(power_source_2))
                                source_2_entry.update(
                                    Status="ON", Updated_on=datetime.now()
                                )
                                if source_1_entry.exists():
                                    source_1_entry.update(
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
                                        Updated_on=datetime.now(),
                                    )
                                print("Status updated.")
                            else:
                                print(
                                    "Creating the first entry for power source {}.".format(
                                        power_source_2
                                    )
                                )
                                SiteLoadPower.objects.create(
                                    Associated_Site=site,
                                    Meter_Number=meter_number,
                                    Supply_Source=power_source_2,
                                    Status="ON",
                                    Updated_on=datetime.now(),
                                )
                                print(
                                    "First entry for {} successfully created.".format(
                                        power_source_2
                                    )
                                )

                        else:
                            print("ERROR!!")
                            print("This status for power source is invalid.")
                        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
                        if source_1_entry.exists():
                            s1 = source_1_entry[0]
                            print("source 1 entry : ", s1)
                            msg1 = (
                                "Total_load :"
                                + str(s1.Site_Total_Load)
                                + ", R-phase-voltage :"
                                + str(s1.r_volt)
                                + ", Y-phase-voltage :"
                                + str(s1.y_volt)
                                + ", B-phase-voltage :"
                                + str(s1.b_volt)
                                + ", R-phase-current :"
                                + str(source_1_entry[0].r_current)
                                + ", Y-phase-current :"
                                + str(s1.y_current)
                                + ", B-phase-current :"
                                + str(s1.b_current)
                                + ", Power_Source :"
                                + s1.Supply_Source
                                + ", Status :"
                                + s1.Status
                                + ", Meter_number :"
                                + str(s1.Meter_Number)
                                + ", Message_created_time :"
                                + created
                                + ", R-phase-power-factor :"
                                + str(s1.r_power_factor)
                                + ", Y-phase-power-factor :"
                                + str(s1.y_power_factor)
                                + ", B-phase-power-factor :"
                                + str(s1.b_power_factor)
                            )

                            client.publish(topictosend, msg1, qos=0, retain=False)

                        if source_2_entry.exists():
                            s2 = source_2_entry[0]
                            print("source 2 entry : ", s2)
                            msg2 = (
                                "Total_load :"
                                + str(s2.Site_Total_Load)
                                + ", R-phase-voltage :"
                                + str(s2.r_volt)
                                + ", Y-phase-voltage :"
                                + str(s2.y_volt)
                                + ", B-phase-voltage :"
                                + str(s2.b_volt)
                                + ", R-phase-current :"
                                + str(s2.r_current)
                                + ", Y-phase-current :"
                                + str(s2.y_current)
                                + ", B-phase-current :"
                                + str(s2.b_current)
                                + ", Power_Source :"
                                + s2.Supply_Source
                                + ", Status :"
                                + s2.Status
                                + ", Meter_number :"
                                + str(s2.Meter_Number)
                                + ", Message_created_time :"
                                + created
                                + ", R-phase-power-factor :"
                                + str(s2.r_power_factor)
                                + ", Y-phase-power-factor :"
                                + str(s2.y_power_factor)
                                + ", B-phase-power-factor :"
                                + str(s2.b_power_factor)
                            )

                            client.publish(topictosend, msg2, qos=0, retain=False)

                    else:
                        if source_1_entry.exists():
                            print("Updating status of {}.".format(power_source_1))
                            if message == "1":
                                source_1_entry.update(
                                    Status="ON", Updated_on=datetime.now()
                                )
                            elif message == "0":
                                source_1_entry.update(
                                    Status="OFF", Updated_on=datetime.now()
                                )
                            else:
                                print("ERROR!!")
                                print("This status for power source is invalid.")
                            print("Status updated.")
                        else:
                            print(
                                "Creating the first entry for power source {}.".format(
                                    power_source_1
                                )
                            )
                            SiteLoadPower.objects.create(
                                Associated_Site=site,
                                Meter_Number=meter_number,
                                Supply_Source=power_source_1,
                                Status="ON",
                                Updated_on=datetime.now(),
                            )
                            print(
                                "First entry for {} successfully created.".format(
                                    power_source_1
                                )
                            )

                        s1 = source_1_entry[0]
                        msg1 = (
                            "Total_load :"
                            + str(s1.Site_Total_Load)
                            + ", R-phase-voltage :"
                            + str(s1.r_volt)
                            + ", Y-phase-voltage :"
                            + str(s1.y_volt)
                            + ", B-phase-voltage :"
                            + str(s1.b_volt)
                            + ", R-phase-current :"
                            + str(s1.r_current)
                            + ", Y-phase-current :"
                            + str(s1.y_current)
                            + ", B-phase-current :"
                            + str(s1.b_current)
                            + ", Power_Source :"
                            + s1.Supply_Source
                            + ", Status :"
                            + s1.Status
                            + ", Meter_number :"
                            + str(s1.Meter_Number)
                            + ", Message_created_time :"
                            + created
                            + ", R-phase-power-factor :"
                            + str(s1.r_power_factor)
                            + ", Y-phase-power-factor :"
                            + str(s1.y_power_factor)
                            + ", B-phase-power-factor :"
                            + str(s1.b_power_factor)
                        )
                        client.publish(topictosend, msg1, qos=0, retain=False)

                except Exception as e:
                    print("This is the exception in supply source block : {}".format(e))

            elif (
                "TIME" in msg_type
            ):  # This is to read the DG run time from dual source meter.
                try:
                    power_source = str(msg_type[0]) + " " + str(msg_type[1])
                    print("Calculating load time for {}.".format(power_source))
                    if "LOAD" in msg_type:
                        current_load_time_cumulative = float(message)
                        last_load_time_cummulative = MeterReadings.objects.filter(
                            reading_for=1, reading_of=message_for
                        )
                        if last_load_time_cummulative.exists():
                            previous_load_time_cumulative = float(
                                last_load_time_cummulative[0].previous_reading_value
                            )
                            if (
                                current_load_time_cumulative
                                >= previous_load_time_cumulative
                            ):
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
                                if msg_type[5] == "1":
                                    for_power_source = MeterSource.objects.filter(
                                        meter_number=int(msg_type[4])
                                    )[0].power_source_1
                                elif msg_type[5] == "2":
                                    for_power_source = MeterSource.objects.filter(
                                        meter_number=int(msg_type[4])
                                    )[0].power_source_2
                                last_load_time_entry = (
                                    SupplyLoadTimeShare.objects.filter(
                                        power_source=for_power_source,
                                        reading_from__gte=dateHourLowerLimitCheck,
                                        reading_from__lte=dateHourUpperLimitCheck,
                                    )
                                )
                                print(
                                    "current_load_time_cumulative : {}".format(
                                        current_load_time_cumulative
                                    )
                                )
                                print(
                                    "previous_load_time_cumulative : {}".format(
                                        previous_load_time_cumulative
                                    )
                                )
                                load_time = (
                                    current_load_time_cumulative
                                    - previous_load_time_cumulative
                                )
                                if last_load_time_entry.exists():
                                    print(
                                        "Updating the runtime for {}.".format(
                                            power_source
                                        )
                                    )
                                    new_hourly_load_runtime = (
                                        last_load_time_entry[0].hourly_run_time
                                        + load_time
                                    )
                                    last_load_time_entry.update(
                                        hourly_run_time=new_hourly_load_runtime
                                    )
                                    last_load_time_cummulative.update(
                                        previous_reading_value=current_load_time_cumulative,
                                        updated_on=current_time,
                                    )
                                    print(
                                        "The {} load runtime has been updated.".format(
                                            power_source
                                        )
                                    )
                                else:
                                    print(
                                        "Creating the first entry for {}.".format(
                                            power_source
                                        )
                                    )
                                    SupplyLoadTimeShare.objects.create(
                                        site=site,
                                        power_source=for_power_source,
                                        hourly_run_time=load_time,
                                        reading_from=dateHourLowerLimitCheck,
                                        reading_to=dateHourUpperLimitCheck,
                                    )
                                    last_load_time_cummulative.update(
                                        previous_reading_value=current_load_time_cumulative,
                                        updated_on=current_time,
                                    )
                                    print(
                                        "First entry created for {}".format(
                                            power_source
                                        )
                                    )

                                time_now = datetime.now()
                                created = time_now.strftime("%Y-%m-%d %H:%M:%S.%f")
                                topictosend = (
                                    "/Acclivate/iOmniControl/"
                                    + str(Site.objects.all()[0].id)
                                    + "/"
                                    + HomeGatewayId.objects.first().hgw_id
                                    + "/in/"
                                    + "SupplyTime"
                                    + "/state"
                                )
                                msg = (
                                    "Supply_Source :"
                                    + str(for_power_source)
                                    + ",Runtime :"
                                    + str(load_time)
                                    + ",Last_runtime_cumulative :"
                                    + str(current_load_time_cumulative)
                                    + ",Message_time :"
                                    + created
                                )
                                client.publish(topictosend, msg, qos=0, retain=False)
                            else:
                                print(
                                    "New meter reading for runtime of {} is smaller than the previous meter reading.".format(
                                        power_source
                                    )
                                )
                        else:
                            print(
                                "Setting the reference reading for this power source."
                            )
                            MeterReadings.objects.create(
                                local_meterId=msg_type[4],
                                reading_for=1,
                                reading_of=message_for,
                                previous_reading_value=message,
                                updated_on=datetime.now(),
                            )
                except Exception as e:
                    print("This is the exception in load time block : {}".format(e))

            elif "WATTAGE" in msg_type:
                print("&&&&&&&&&&&&&&&&")
                try:
                    s = Site.objects.all()[0]
                    print("This is for Load Power.")
                    load_power = float(message)
                    print("This is the load value: ", load_power)
                    print("Now checking condition.")
                    load_entry = SiteLoadPower.objects.filter(
                        Associated_Site=s, Meter_Number=int(msg_type[3]), Status="ON"
                    )
                    if load_entry.exists():
                        # print "Inside if."
                        print(
                            "Updating the load for meter number {}.".format(msg_type[3])
                        )
                        load_entry.update(Site_Total_Load=load_power)
                        print("Total power updated.")

                    else:
                        pass
                except Exception as e:
                    print("This is the exception in wattage block : {}".format(e))
            elif "WATTAGELOAD" in msg_type:
                print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
                try:
                    s = Site.objects.all()[0]
                    print("This is for Load Power.")
                    load_power = float(message)
                    print("This is the load value: ", load_power)
                    print("Now checking condition.")
                    time_now = datetime.now()
                    created = time_now.strftime("%Y-%m-%d %H:%M:%S.%f")
                    epochTime = round(time.time() * 1000)
                    print("epochTime : ", epochTime)
                    load_entry = LoadData.objects.filter(
                        Associated_Site=s,
                        Meter_Number=int(msg_type[3]),
                    )
                    leg_id = load_entry[0].leg_id
                    print("leg_id : ", leg_id)
                    if load_entry.exists():
                        # print "Inside if."
                        print(
                            "Updating the load for meter number {}.".format(msg_type[3])
                        )
                        load_entry.update(
                            site_total_load=load_power,
                            Updated_on=time_now,
                            epochTime=epochTime,
                        )
                        print("Total power updated.")
                    else:
                        print("#######load entry not exists########")
                    topictosend = (
                        "/Acclivate/iOmniControl/"
                        + str(Site.objects.all()[0].id)
                        + "/"
                        + Homeobjects.filterGatewayId.objects.first().hgw_id
                        + "/in/"
                        + "LoadData"
                        + "/state"
                    )
                    msg = (
                        "LoadValue :"
                        + str(load_power)
                        + ", leg_id :"
                        + str(leg_id)
                        + ", Meter_Number :"
                        + str(msg_type[3])
                        + ", Datetime :"
                        + created
                        + ", epochTime :"
                        + str(epochTime)
                    )
                    print("msg : ", msg)
                    if load_power > 0:
                        client.publish(topictosend, msg, qos=0, retain=False)
                        print("%%%%%%%%%%%%%%%%%%%%%%")
                except Exception as e:
                    print("This is the exception in wattage block : {}".format(e))

            elif "APPARENT" in msg_type:
                print(
                    "################### Apparent Energy ####################################"
                )
                try:
                    print("This is the for meter Apparent Energy.")
                    incoming_meter_reading = float(message)
                    dateHourLowerLimitCheck = current_time.replace(
                        hour=int(current_time.hour), minute=0, second=0, microsecond=0
                    )
                    dateHourUpperLimitCheck = current_time.replace(
                        hour=int(current_time.hour), minute=59, second=59, microsecond=0
                    )
                    print(dateHourLowerLimitCheck)
                    print(dateHourUpperLimitCheck)
                    meter_reading_entry = MeterReadings.objects.filter(
                        reading_of=message_for
                    )
                    leg_id = SmartEnergyDevices.objects.filter(topic=message_for)[
                        0
                    ].leg_id
                    aisle_grp = AisleGroup.objects.filter(aisle_grp_id=leg_id)
                    if meter_reading_entry.exists():
                        previous_meter_reading_value = float(
                            meter_reading_entry[0].previous_reading_value
                        )
                        if incoming_meter_reading >= previous_meter_reading_value:
                            new_unit_consumption = (
                                float(
                                    incoming_meter_reading
                                    - previous_meter_reading_value
                                )
                                / 1000
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
                            dateHourLowerLimitCheck1 = (
                                dateHourLowerLimitCheck - timedelta(hours=1)
                            )
                            dateHourUpperLimitCheck1 = (
                                dateHourUpperLimitCheck - timedelta(hours=1)
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
                                aisle_grp[0].cumulative_consumption
                                + new_unit_consumption
                            )
                            print(
                                "new cumulative consumption  is : ",
                                new_cumulative_consumption,
                            )
                            if hourly_entry.exists() and previous_hour_entry.exists():
                                print(
                                    "inside hourly and previous hourly entry exist case"
                                )
                                new_consumption = (
                                    hourly_entry[0].unit_consumption
                                    + new_unit_consumption
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
                                    "Meter reading also updated for {}".format(
                                        message_for
                                    )
                                )

                            else:
                                if hourly_entry.exists():
                                    print("updating first hourly entry")
                                    new_consumption = (
                                        hourly_entry[0].unit_consumption
                                        + new_unit_consumption
                                    )
                                    hourly_entry.update(
                                        unit_consumption=new_consumption
                                    )
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
                                        "Meter reading also updated for {}".format(
                                            message_for
                                        )
                                    )

                                else:
                                    print("Creating new hourly entry for ")
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

                            print(
                                "Now checking condition for entry or update in daily reading."
                            )
                            if (
                                daily_entry.exists()
                            ):  # This is the logic for daily site reading.
                                print("Updating daily consumption data.")
                                new_consumption = (
                                    daily_entry[0].unit_consumption
                                    + new_unit_consumption
                                )
                                daily_entry.update(unit_consumption=new_consumption)
                                print(
                                    "The reading for leg id {} is updated".format(
                                        leg_id
                                    )
                                )

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
                                    "New daily entry for leg id {} is created.".format(
                                        leg_id
                                    )
                                )

                    else:
                        print("Setting the first reference reading for this leg.")
                        MeterReadings.objects.create(
                            local_meterId=int(msg_type[4]),
                            reading_for=0,
                            reading_of=str(message_for),
                            previous_reading_value=str(message),
                            updated_on=datetime.now(),
                        )
                except Exception as e:
                    print("This is the exception : {}".format(e))
        else:
            print("##########################################################")
            print("*********Got an unknown message. Need to check!!**********")
            print("##########################################################")

    client = mqtt.Client(client_id="paho_client_1")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("127.0.0.1", 5003, 60)
    logger.info("MQTT Client connected to broker at 127.0.0.1:5003")
    client.loop_forever()
