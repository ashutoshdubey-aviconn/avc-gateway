import re
import time
from datetime import datetime, timedelta

from wareApp.models import (
    AisleGroup,
    DailySiteReading,
    HomeGatewayId,
    HourlySiteReading,
    Site,
    SupplyLoadTimeShare,
)


def handle_sync_message(
    client, msg, message, msg_type, msg_subtype, site, current_time
):
    if "sync" not in msg_type:
        return False

    if msg_subtype == "consumption":
        try:
            data = message.split(",")
            missed_time = data[0]
            aisle_group_id = str(data[1].split(":")[1])
            last_entry_datetime = data[2].split(":")[1].split(" ")
            last_entry_date = datetime.strptime(last_entry_datetime[0], "%Y-%m-%d")
            last_entry_date_hour = int(last_entry_datetime[1])
            dateHourLastEntry = last_entry_date.replace(hour=last_entry_date_hour)
            dateHourLastEntryHour = dateHourLastEntry
            print(
                "This message has been received to recover the lost data on the server for {} seconds for aisle group id {}.".format(  # noqa: E501
                    float(missed_time.split(":")[1]), aisle_group_id
                )  # noqa: E501
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
            sync_date = current_time.date()
            gw_total_cumulative = AisleGroup.objects.filter(
                site=site, aisle_grp_id=int(aisle_group_id)
            )[0].cumulative_consumption
            topictosend1 = (
                "/Acclivate/iOmniControl/"
                + str(Site.objects.all()[0].id)
                + "/"
                + HomeGatewayId.objects.all()[0].hgw_id
                + "/in/recovery/dailyConsumption/state"  # noqa: E501
            )

            while dateHourLastEntry.date() <= sync_date:
                recovery_dates, daily_unit_consumptions = "", ""
                daily_consumption_entry = legs.filter(
                    leg_id=aisle_group_id, reading_for=dateHourLastEntry.date()
                )
                recovery_dates += dateHourLastEntry.strftime("%Y-%m-%d") + ","
                if daily_consumption_entry.exists():
                    daily_unit_consumptions += (
                        str(daily_consumption_entry[0].unit_consumption) + ","
                    )
                else:
                    daily_unit_consumptions += "ERROR404,"
                msg_payload = (
                    "Aisle_group_id : "
                    + aisle_group_id
                    + "; Recovery_Dates : "
                    + recovery_dates
                    + "; Unit_consumptions : "
                    + daily_unit_consumptions
                    + "; GW_Total_cumulative : "
                    + str(gw_total_cumulative)
                )
                client.publish(topictosend1, msg_payload, qos=0, retain=False)
                dateHourLastEntry += timedelta(days=1)

            print("Now starting delayed recovery for hourly consumption data.")
            topictosend1 = (
                "/Acclivate/iOmniControl/"
                + str(Site.objects.all()[0].id)
                + "/"
                + HomeGatewayId.objects.all()[0].hgw_id
                + "/in/recovery/hourlyConsumption"  # noqa: E501
            )
            sync_hour = datetime.now()

            while sync_hour >= dateHourLastEntryHour:
                recovery_hours, hourly_unit_consumptions = "", ""
                hourly_entry = HourlySiteReading.objects.filter(
                    leg_id=aisle_group_id,
                    reading_from__lte=dateHourLastEntryHour,
                    reading_to__gte=dateHourLastEntryHour,
                )
                recovery_hours += (
                    dateHourLastEntryHour.strftime("%Y-%m-%d %H:%M:%S.%f") + ","
                )
                if hourly_entry.exists():
                    hourly_unit_consumptions += (
                        str(hourly_entry[0].unit_consumption) + ","
                    )
                else:
                    hourly_unit_consumptions += "ERROR404,"
                msg_payload = (
                    "Aisle_group_id : "
                    + aisle_group_id
                    + "; Recovery_Hours : "
                    + recovery_hours
                    + "; Unit_consumptions : "
                    + hourly_unit_consumptions
                    + "; GW_total_cumulative : "
                    + str(gw_total_cumulative)
                )
                client.publish(topictosend1, msg_payload, qos=0, retain=False)
                print(
                    "Hourly consumption data for aisle group id {} synced with cloud server.".format(
                        aisle_group_id
                    )
                )
                time.sleep(2)
                dateHourLastEntryHour += timedelta(hours=1)
        except Exception as e:
            print("This is the exception in consumption sync block : {}".format(e))
        return True

    if msg_subtype == "loadTime":
        try:
            powerSource, missedTime, syncHour = re.search(
                "Power_source : (.*), Missed_consumption_time_in_secs : (.*), Last_synced_hour : (.*)'",
                message,
            ).groups()
            power_source = SupplyLoadTimeShare.objects.filter(
                power_source=int(powerSource)
            )
            missed_time = float(missedTime)
            last_synced_hour = datetime.strptime(syncHour, "%Y-%m-%d %H:%M:%S.%f")
            print("Readings missed on server for {} seconds.".format(missed_time))
            print(
                "Message received for recovery of runtime for {}".format(
                    power_source[0].get_power_source_display()
                )
            )
            print("Last synced datetime {}".format(last_synced_hour))
            recovery_data = power_source.filter(reading_to__gte=last_synced_hour)
            last_synced_hour = last_synced_hour.replace(
                minute=0, second=0, microsecond=0
            )
            recovery_hours, recovered_load_runtime = "", ""
            while current_time >= last_synced_hour:
                recovery_hours += (
                    last_synced_hour.strftime("%Y-%m-%d %H:%M:%S.%f") + ","
                )
                load_runtime = recovery_data.filter(reading_from=last_synced_hour)
                if load_runtime.exists():
                    recovered_load_runtime += str(load_runtime[0].hourly_run_time) + ","
                else:
                    recovered_load_runtime += "ERROR404,"
                last_synced_hour += timedelta(hours=1)
            msg_payload = (
                "Power_source : "
                + powerSource
                + "; Recovery_hours : "
                + recovery_hours
                + "; Recovery_load_runtime : "
                + recovered_load_runtime
            )
            topictosend = (
                "/Acclivate/iOmniControl/"
                + str(Site.objects.first().id)
                + "/"
                + HomeGatewayId.objects.first().hgw_id
                + "/in/recovery/loadRuntime"
            )
            client.publish(topictosend, msg_payload, qos=0, retain=False)
            print("Load runtime recovery message sent to server.")
        except Exception as e:
            print("This is the exception in load runtime recovery block : {}".format(e))
        return True

    print("#####################################################")
    print("****** Received an unknown sync message. ********")
    print("#####################################################")
    return True
