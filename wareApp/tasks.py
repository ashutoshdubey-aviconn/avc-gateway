import paho.mqtt.client as mqtt
import re
import os
import time
from celery import shared_task
from wareApp.models import *
from datetime import datetime, timedelta, timezone
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
# app = Celery('tasks', broker='amqp://guest@localhost//')


@shared_task
def mqtt_client1():
    print("inside client 1")
    # app = Celery('mqtt_client', broker='amqp://guest@localhost/')

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe("/asem/aviconn/#")
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        # client.subscribe("/sem/iOmniControl/#", 1)
        client.subscribe("/Acclivate/iOmniControl/#", 1)
        # client.subscribe("/sem/iOmniControl/+/+/+/+/state", 1)

    # The callback for when a PUBLISH message is received from the server.
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

    client = mqtt.Client("paho_client_1")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("127.0.0.1", 5003, 60)
    print("MQTT Client 1 is Running >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # client.username_pw_set("djgpjqqt","AfTkXiiaov8c")

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()


@shared_task
def mqtt_client2():
    # app = Celery('mqtt_client', broker='amqp://guest@localhost/')

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("/Acclivate/iOmniControl/#")
        # client.subscribe("/sem/iOmniControl/+/+/+/+/state", 1)

    # The callback for when a PUBLISH message is received from the server.
    def on_message(client, userdata, msg):
        print("######################")
        print("Topic: ", msg.topic + "  Message: " + str(msg.payload))
        print("######################")
        message = str(msg.payload)
        head = msg.topic
        gw_id = (head.split("/"))[4]
        print(gw_id)
        message_for = head.split("/")[6]
        print("This reading is for : {}".format(message_for))
        msg_type = message_for.split("_")
        print("This is the message type: ".format(msg_type))
        msg_subtype = head.split("/")[7]
        location_id = int((head.split("/"))[3])
        site = Site.objects.get(id=location_id)
        print("Location Id is : {}".format(int(location_id)))
        current_time = datetime.now()
        if "remoteAccess" in msg_type:
            print("This message is for remote access on gateway.")
            gw_id = HomeGatewayId.objects.first()
            rssh_port = gw_id.rssh_port
            monitoring_port = gw_id.monitoring_port
            print("Rssh_port : {}".format(rssh_port))
            print("Monitoring_port : {}".format(monitoring_port))
            print(msg.payload)
            # message = str(msg.payload).split("_")
            message = str(msg.payload.decode("utf-8")).split("_")
            action = message[0]
            autossh_retry_count = int(message[1])
            print("This is to {} autossh.".format(action))
            topicsend = (
                "/Acclivate/iOmniControl/"
                + str(gw_id.connected_to.id)
                + "/"
                + gw_id.hgw_id
                + "/in/"
                + "remoteAccess"
                + "/state"
            )
            if action == "start":
                print("Starting autossh.")
                action = os.system("pgrep autossh | xargs kill -9")
                command = (
                    "autossh -M "
                    + monitoring_port
                    + ' -fN -o "PubkeyAuthentication=yes" -o "PasswordAuthentication=no"  -R '
                    + rssh_port
                    + ":localhost:22 aviconn@asem1.aviconn.in"
                )
                print(command)
                autossh = os.system(command)
                count = 0
                while True:
                    if count >= autossh_retry_count:
                        Rssh_port_check = (
                            os.popen("netstat -plant | grep " + rssh_port)
                            .read()
                            .split("\n")[0]
                        )
                        if len(Rssh_port_check) == 0:
                            Rssh_port_check = "Not in listen mode."
                        Rport_status = "Rport_status : " + Rssh_port_check
                        Monitoring_port_check = (
                            os.popen("netstat -plant | grep " + monitoring_port)
                            .read()
                            .split("\n")[0]
                        )
                        if len(Monitoring_port_check) == 0:
                            Monitoring_port_check = "Not in listen mode."
                        Mport_status = "Mport_status : " + Monitoring_port_check
                        msg1 = (
                            "Autossh failed to start on gateway."
                            + "\n"
                            + Rport_status
                            + "\n"
                            + Mport_status
                        )
                        print(msg1)
                        client.publish(topicsend, msg1, qos=1, retain=False)
                        os.system(
                            "echo odroid | sudo -S fuser -k " + rssh_port + "/tcp"
                        )
                        os.system(
                            "echo odroid | sudo -S fuser -k " + monitoring_port + "/tcp"
                        )
                        msg = "Rssh and monitoring port restarted for gateway id {}.".format(
                            gw_id.hgw_id
                        )
                        print(msg)
                    else:
                        time.sleep(5)
                        status = os.popen("pgrep autossh").read().split("\n")[0]
                        if status == "":
                            print("Retrying autossh")
                            autossh = os.system(command)
                            count += 1
                        else:
                            msg = "Autossh started sucessfully."
                            print(msg)
                            break

            elif action == "stop":
                print("Stopping autossh!")
                os.system("echo odroid | sudo -S pgrep autossh | xargs kill -9")
                os.system("echo odroid | sudo -S fuser -k " + rssh_port + "/tcp")
                os.system("echo odroid | sudo -S fuser -k " + monitoring_port + "/tcp")
                msg = "Autossh has been stoped. Rssh and Monitoring ports have been closed."
                print(msg)

            elif action == "restart":
                print("Got a command from server to restart the gateway.")
                os.system("echo odroid | sudo -S init 6")
                msg = "Gateway has been restarted."
                print(msg)

            else:
                msg = "Got an unknown command for rssh."
                print(msg)

            client.publish(topicsend, msg, qos=1, retain=False)
            return

        if "sync" in msg_type:  # This block is for data recovery mechanism.
            if "consumption" in msg_subtype:  # This is to recover consumption data.
                try:
                    data = message.split(",")
                    missed_time = data[0]
                    missed_time_in_secs = float(missed_time.split(":")[1])
                    aisle_group = data[1]
                    aisle_group_id = str(aisle_group.split(":")[1])
                    last_entry_datetime = (data[2].split(":")[1]).split(" ")
                    last_entry_date = datetime.strptime(
                        last_entry_datetime[0], "%Y-%m-%d"
                    )
                    last_entry_date_hour = int(last_entry_datetime[1])
                    dateHourLastEntry = last_entry_date.replace(
                        hour=last_entry_date_hour
                    )
                    dateHourLastEntryHour = dateHourLastEntry
                    print(
                        "This message has been received to recover the lost data on the server for {} seconds"
                        " for aisle group id {}.".format(
                            missed_time_in_secs, aisle_group_id
                        )
                    )
                    print(
                        "This is the time sent by the server to start recovery : {}".format(
                            dateHourLastEntry
                        )
                    )
                    print("Firstly sending daily consumption data for quick recovery.")
                    legs = DailySiteReading.objects.filter(
                        reading_for__gte=last_entry_date.date()
                    )
                    # distinct_legs = legs.distinct('leg_id')
                    sync_date = current_time.date()
                    gw_total_cumulative = AisleGroup.objects.filter(
                        site=site, aisle_grp_id=int(aisle_group_id)
                    )[0].cumulative_consumption
                    topictosend1 = (
                        "/Acclivate/iOmniControl/"
                        + str(Site.objects.all()[0].id)
                        + "/"
                        + HomeGatewayId.objects.all()[0].hgw_id
                        + "/in/"
                        + "recovery/"
                        + "dailyConsumption/"
                        + "/state"
                    )
                    #  This is the recovery mechanism for syncing data for one aisle group for all the lost dates/hour.
                    #  This will enable each aisle to recover its data individually(if any meter is damaged and only one aisle group needs recovery.)

                    while dateHourLastEntry.date() <= sync_date:
                        recovery_dates, daily_unit_consumptions = "", ""
                        daily_consumption_entry = legs.filter(
                            leg_id=aisle_group_id, reading_for=dateHourLastEntry.date()
                        )
                        recovery_date = datetime.strftime(
                            dateHourLastEntry.date(), "%Y-%m-%d"
                        )
                        recovery_dates += recovery_date + ","
                        if daily_consumption_entry.exists():
                            daily_unit_consumptions += (
                                str(daily_consumption_entry[0].unit_consumption) + ","
                            )
                        else:
                            daily_unit_consumptions += "ERROR404,"
                        print("This the aisle group id : {}".format(aisle_group_id))
                        print(
                            "These are the recovery dates : {}".format(recovery_dates)
                        )
                        print(
                            "These are their corresponding unit consumptions : {}".format(
                                daily_unit_consumptions
                            )
                        )
                        msg = (
                            "Aisle_group_id : "
                            + aisle_group_id
                            + "; Recovery_Dates : "
                            + recovery_dates
                            + "; Unit_consumptions : "
                            + daily_unit_consumptions
                            + "; GW_Total_cumulative : "
                            + str(gw_total_cumulative)
                        )
                        client.publish(topictosend1, msg, qos=0, retain=False)
                    print("Now starting delayed recovery for hourly consumption data.")
                    topictosend1 = (
                        "/Acclivate/iOmniControl/"
                        + str(Site.objects.all()[0].id)
                        + "/"
                        + HomeGatewayId.objects.all()[0].hgw_id
                        + "/in/"
                        + "recovery/"
                        + "hourlyConsumption"
                    )
                    sync_hour = datetime.now()

                    while sync_hour >= dateHourLastEntryHour:
                        recovery_hours, hourly_unit_consumptions = "", ""
                        hourly_entry = HourlySiteReading.objects.filter(
                            leg_id=aisle_group_id,
                            reading_from__lte=dateHourLastEntryHour,
                            reading_to__gte=dateHourLastEntryHour,
                        )
                        recovery_hour = dateHourLastEntryHour.strftime(
                            "%Y-%m-%d %H:%M:%S.%f"
                        )
                        recovery_hours += recovery_hour + ","
                        if hourly_entry.exists():
                            hourly_unit_consumptions += (
                                str(hourly_entry[0].unit_consumption) + ","
                            )
                        else:
                            hourly_unit_consumptions += "ERROR404,"

                        print("This the aisle group id : {}".format(aisle_group_id))
                        print(
                            "These are the recovery hours : {}".format(recovery_hours)
                        )
                        print(
                            "These are their corresponding unit consumptions : {}".format(
                                hourly_unit_consumptions
                            )
                        )
                        msg = (
                            "Aisle_group_id : "
                            + aisle_group_id
                            + "; Recovery_Hours : "
                            + recovery_hours
                            + "; Unit_consumptions : "
                            + hourly_unit_consumptions
                            + "; GW_total_cumulative : "
                            + str(gw_total_cumulative)
                        )
                        client.publish(topictosend1, msg, qos=0, retain=False)
                        print(
                            "Hourly consumption data for aisle group id {} synced with cloud server.".format(
                                aisle_group_id
                            )
                        )
                        time.sleep(2)
                        dateHourLastEntryHour += timedelta(hours=1)

                    #  This is the recovery mechanism based on recovery for all aisle groups for
                    #  one date/hour input at a time.
                    """while dateHourLastEntry.date() <= sync_date:
                        daily_consumption_entry = legs.filter(reading_for=dateHourLastEntry.date())
                        recovery_date = datetime.strptime(dateHourLastEntry.date(), "%Y-%m-%d")
                        if daily_consumption_entry.exists():
                            aisle_groups, daily_unit_consumptions = "", ""
                            for leg in distinct_legs:
                                single_leg_daily_data = daily_consumption_entry.filter(leg_id=leg.leg_id)
                                if single_leg_daily_data.exists():
                                    aisle_groups += str(leg.leg_id) + ","
                                    daily_unit_consumptions += single_leg_daily_data.unit_consumption + ","
                                else:
                                    aisle_groups += str(leg.leg_id) + ","
                                    daily_unit_consumptions += "Hourly unit consumption not found,"

                            print("This is the recovery date : {}".format(recovery_date))
                            print("These are the aisle group ids : {}".format(aisle_groups))
                            print("These are their corresponding unit consumptions : {}".format(daily_unit_consumptions))
                            msg = "Recovery_Date :" + recovery_date + \
                                    ",Aisle_group_ids :" + aisle_groups + \
                                    ",Unit_consumptions :" + daily_unit_consumptions
                            client.publish(topictosend, msg, qos=0, retain=False)
                            last_entry_date += timedelta(days=1)
                        else:
                            msg = "Recovery_Date :" + recovery_date + \
                                    ",Aisle_group_ids :" + aisle_groups + \
                                    ",Unit_consumptions : ERROR404"
                            client.publish(topictosend, msg, qos=0, retain=False)
                            last_entry_date += timedelta(days=1)

                    print("Now starting delayed recovery for hourly consumption data.")
                    sync_hour = datetime.now()
                    while sync_hour >= dateHourLastEntry:
                        hourly_entry = HourlySiteReading.objects.filter(reading_from__gte=dateHourLastEntry, reading_to__lte=dateHourLastEntry)
                        if hourly_entry.exists():
                            aisle_groups, hourly_unit_consumptions = "", ""
                            for leg in distinct_legs:
                                single_leg_hourly_data = hourly_entry.filter(leg_id=leg.leg_id)
                                aisle_groups += str(leg.leg_id) + ","
                                daily_unit_consumptions = single_leg_hourly_data.unit_consumption + ","
                            recovery_hour = datetime.strptime(dateHourLastEntry, "%Y-%m-%d H%:M%:S%")
                            print("This is the recovery date : {}".format(recovery_hour))
                            print("These are the aisle group ids : {}".format(aisle_groups))
                            print("These are their corresponding unit consumptions : {}".format(daily_unit_consumptions))
                            msg = "Recovery_Hour :" + recovery_hour + \
                                    ",Aisle_group_ids :" + aisle_groups + \
                                    ",Unit_consumptions :" + daily_unit_consumptions
                            client.publish(topictosend, msg, qos=0, retain=False)
                            dateHourLastEntry += timedelta(hours=1)
                            time.sleep(5)
                        else:
                            msg = "Recovery_Hour :" + recovery_hour + \
                                    ",Aisle_group_ids :" + aisle_groups + \
                                    ",Unit_consumptions : ERROR404"
                            client.publish(topictosend, msg, qos=0, retain=False)
                            dateHourLastEntry += timedelta(hours=1)
                            time.sleep(5)
                    print("Hourly consumption data synced with cloud server.")"""
                except Exception as e:
                    print(
                        "This is the exception in consumption sync block : {}".format(e)
                    )

            elif "loadTime" in msg_subtype:
                try:
                    powerSource, missedTime, syncHour = re.search(
                        "Power_source : (.*), Missed_consumption_time_in_secs : (.*), Last_synced_hour : (.*)'",
                        message,
                    ).groups()
                    power_source = SupplyLoadTimeShare.objects.filter(
                        power_source=int(powerSource)
                    )
                    missed_time = float(missedTime)
                    last_synced_hour = datetime.strptime(
                        syncHour, "%Y-%m-%d %H:%M:%S.%f"
                    )
                    print(
                        "Readings missed on server for {} seconds.".format(missed_time)
                    )
                    print(
                        "Message received for recovery of runtime for {}".format(
                            power_source[0].get_power_source_display()
                        )
                    )
                    print("Last synced datetime {}".format(last_synced_hour))
                    print("Starting recovery process for load runtime.")
                    recovery_data = power_source.filter(
                        reading_to__gte=last_synced_hour
                    )
                    last_synced_hour = last_synced_hour.replace(
                        minute=0, second=0, microsecond=0
                    )
                    recovery_hours, recovered_load_runtime = "", ""
                    while current_time >= last_synced_hour:
                        print(
                            "This is the recovery for hour {}".format(last_synced_hour)
                        )
                        recovery_hours += (
                            datetime.strftime(last_synced_hour, "%Y-%m-%d %H:%M:%S.%f")
                            + ","
                        )
                        load_runtime = recovery_data.filter(
                            reading_from=last_synced_hour
                        )
                        if load_runtime.exists():
                            recovered_load_runtime += (
                                str(load_runtime[0].hourly_run_time) + ","
                            )
                        else:
                            recovered_load_runtime += "ERROR404,"
                        last_synced_hour = last_synced_hour + timedelta(hours=1)
                    print("These are the recovery hours : {}".format(recovery_hours))
                    print(
                        "These are the corresponding load runtime : {}".format(
                            recovered_load_runtime
                        )
                    )
                    topictosend = (
                        "/Acclivate/iOmniControl/"
                        + str(Site.objects.first().id)
                        + "/"
                        + HomeGatewayId.objects.first().hgw_id
                        + "/in/"
                        + "recovery/"
                        + "loadRuntime"
                    )
                    msg = (
                        "Power_source : "
                        + powerSource
                        + "; Recovery_hours : "
                        + recovery_hours
                        + "; Recovery_load_runtime : "
                        + recovered_load_runtime
                    )
                    print(msg)
                    client.publish(topictosend, msg, qos=0, retain=False)
                    print("Load runtime recovery message sent to server.")
                except Exception as e:
                    print(
                        "This is the exception in load runtime recovery block : {}".format(
                            e
                        )
                    )

            else:
                print("#####################################################")
                print("****** Received an unknown sync message. ********")
                print("#####################################################")

        else:
            print("##########################################################")
            print("*********Got an unknown message. Need to check!!**********")
            print("##########################################################")

    client = mqtt.Client("paho_client_2")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("127.0.0.1", 5003, 60)
    print("MQTT Client is Running >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # client.username_pw_set("djgpjqqt","AfTkXiiaov8c")

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()
