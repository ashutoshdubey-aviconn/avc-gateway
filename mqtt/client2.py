import os
import re
import time

import paho.mqtt.client as mqtt

from datetime import datetime, timedelta
from celery.utils.log import get_task_logger

from wareApp.models import *

logger = get_task_logger(__name__)


def start_client():
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

    client = mqtt.Client(client_id="paho_client_2")

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("127.0.0.1", 5003, 60)
    logger.info("MQTT Client is Running >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # client.username_pw_set("djgpjqqt","AfTkXiiaov8c")

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()
