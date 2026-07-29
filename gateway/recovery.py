import logging
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Union

import paho.mqtt.client as mqtt

from wareApp.models import (
    AisleGroup,
    DailySiteReading,
    HomeGatewayId,
    HourlySiteReading,
    Site,
    SupplyLoadTimeShare,
)

logger = logging.getLogger(__name__)


def handle_sync_message(
    client: mqtt.Client,
    msg: mqtt.MQTTMessage,
    message: str,
    msg_type: list[str],
    msg_subtype: Optional[str],
    site: Optional[object],
    current_time: Optional[datetime] = None,
) -> bool:
    if current_time is None:
        current_time = datetime.now()
    missed_time: Union[float, str] = 0.0

    # Recovery of daily/hourly consumption
    if msg_subtype == "consumption":
        try:
            # Flexible parsing: accept messages that include a missed seconds token,
            # the aisle/leg id, and either a single last-synced datetime or a start+end range.
            data = message.split(",")
            missed_time = data[0] if data else "missed:0"
            # compute missed seconds explicitly to satisfy static typing
            try:
                missed_seconds = float(missed_time.split(":")[1])
            except Exception:
                missed_seconds = 0.0

            # try to extract aisle group id (support different key labels)
            aisle_group_id = None
            for token in data:
                if "aisle" in token.lower() or "leg" in token.lower():
                    parts = token.split(":")
                    if len(parts) > 1:
                        aisle_group_id = parts[1].strip()
                        break
            if aisle_group_id is None and len(data) > 1:
                # fallback to second segment value
                aisle_group_id = data[1].split(":")[-1].strip()

            if aisle_group_id is None:
                logger.warning(
                    "No aisle_group_id provided in consumption sync message: %s",
                    message,
                )
                return True

            # find all datetime-like substrings in the message; support YYYY-MM-DD and optional hour
            datetime_patterns = re.findall(r"\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}(?::\d{2}(?::\d{2})?)?)?", message)
            start_dt = None
            end_dt = None
            if datetime_patterns:
                # parse first datetime as start
                try:
                    parts = datetime_patterns[0].split()
                    if len(parts) == 1:
                        start_dt = datetime.strptime(parts[0], "%Y-%m-%d")
                    else:
                        # try common full formats
                        try:
                            start_dt = datetime.strptime(datetime_patterns[0], "%Y-%m-%d %H:%M:%S.%f")
                        except Exception:
                            try:
                                start_dt = datetime.strptime(datetime_patterns[0], "%Y-%m-%d %H:%M:%S")
                            except Exception:
                                # fallback to hour-only
                                date_part, hour_part = parts[0], parts[1]
                                start_dt = datetime.strptime(date_part, "%Y-%m-%d").replace(
                                    hour=int(hour_part.split(":")[0])
                                )
                except Exception:
                    start_dt = None

                if len(datetime_patterns) > 1:
                    try:
                        parts = datetime_patterns[1].split()
                        if len(parts) == 1:
                            end_dt = datetime.strptime(parts[0], "%Y-%m-%d")
                        else:
                            try:
                                end_dt = datetime.strptime(datetime_patterns[1], "%Y-%m-%d %H:%M:%S.%f")
                            except Exception:
                                try:
                                    end_dt = datetime.strptime(datetime_patterns[1], "%Y-%m-%d %H:%M:%S")
                                except Exception:
                                    date_part, hour_part = parts[0], parts[1]
                                    end_dt = datetime.strptime(date_part, "%Y-%m-%d").replace(
                                        hour=int(hour_part.split(":")[0])
                                    )
                    except Exception:
                        end_dt = None

            # prepare query ranges
            if start_dt is None:
                # fallback to original single-last-entry behavior
                # old format: data[2] contains date and hour
                last_entry_datetime = (
                    data[2].split(":")[1].split(" ")
                    if len(data) > 2 and ":" in data[2]
                    else [current_time.strftime("%Y-%m-%d"), str(current_time.hour)]
                )
                last_entry_date = datetime.strptime(last_entry_datetime[0], "%Y-%m-%d")
                last_entry_date_hour = int(last_entry_datetime[1]) if len(last_entry_datetime) > 1 else 0
                start_dt = last_entry_date.replace(hour=last_entry_date_hour)

            if end_dt is None:
                end_dt = current_time

            logger.info(
                "Recovery requested: aisle_group=%s start=%s end=%s missed_seconds=%s",
                aisle_group_id,
                start_dt,
                end_dt,
                missed_seconds,
            )

            # Daily recovery: iterate by day from start_dt.date() to end_dt.date()
            logger.info("Firstly sending daily consumption data for quick recovery.")
            legs = DailySiteReading.objects.filter(reading_for__gte=start_dt.date())
            aisle_group_id_str = str(aisle_group_id)
            try:
                aisle_group_id_int = int(aisle_group_id_str)
            except Exception:
                logger.warning("Invalid aisle_group_id value: %s", aisle_group_id_str)
                return True
            gw_total_cumulative = AisleGroup.objects.filter(site=site, aisle_grp_id=aisle_group_id_int)[
                0
            ].cumulative_consumption
            topictosend1 = f"/Acclivate/iOmniControl/{Site.objects.all()[0].id}/{HomeGatewayId.objects.all()[0].hgw_id}/in/recovery/dailyConsumption/state"

            date_cursor = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date_cursor = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            while date_cursor.date() <= end_date_cursor.date():
                recovery_dates, daily_unit_consumptions = "", ""
                daily_consumption_entry = legs.filter(leg_id=aisle_group_id, reading_for=date_cursor.date())
                recovery_dates += date_cursor.strftime("%Y-%m-%d") + ","
                if daily_consumption_entry.exists():
                    daily_unit_consumptions += str(daily_consumption_entry[0].unit_consumption) + ","
                else:
                    daily_unit_consumptions += "ERROR404,"
                msg_payload = (
                    "Aisle_group_id : "
                    + aisle_group_id_str
                    + "; Recovery_Dates : "
                    + recovery_dates
                    + "; Unit_consumptions : "
                    + daily_unit_consumptions
                    + "; GW_Total_cumulative : "
                    + str(gw_total_cumulative)
                )
                client.publish(topictosend1, msg_payload, qos=0, retain=False)
                date_cursor += timedelta(days=1)

            # Hourly recovery: iterate hours from start_dt (rounded to hour) up to end_dt
            logger.info("Now starting delayed recovery for hourly consumption data.")
            topictosend1 = f"/Acclivate/iOmniControl/{Site.objects.all()[0].id}/{HomeGatewayId.objects.all()[0].hgw_id}/in/recovery/hourlyConsumption"
            hour_cursor = start_dt.replace(minute=0, second=0, microsecond=0)
            end_hour_cursor = end_dt.replace(minute=0, second=0, microsecond=0)

            while hour_cursor <= end_hour_cursor:
                recovery_hours, hourly_unit_consumptions = "", ""
                hourly_entry = HourlySiteReading.objects.filter(
                    leg_id=aisle_group_id,
                    reading_from__lte=hour_cursor,
                    reading_to__gte=hour_cursor,
                )
                recovery_hours += hour_cursor.strftime("%Y-%m-%d %H:%M:%S.%f") + ","
                if hourly_entry.exists():
                    hourly_unit_consumptions += str(hourly_entry[0].unit_consumption) + ","
                else:
                    hourly_unit_consumptions += "ERROR404,"
                msg_payload = (
                    "Aisle_group_id : "
                    + aisle_group_id_str
                    + "; Recovery_Hours : "
                    + recovery_hours
                    + "; Unit_consumptions : "
                    + hourly_unit_consumptions
                    + "; GW_total_cumulative : "
                    + str(gw_total_cumulative)
                )
                client.publish(topictosend1, msg_payload, qos=0, retain=False)
                logger.info(
                    "Hourly consumption data for aisle group id %s synced with cloud server.",
                    aisle_group_id,
                )
                time.sleep(2)
                hour_cursor += timedelta(hours=1)

        except Exception as e:
            logger.exception("Exception in consumption sync block: %s", e)
        return True

    # Recovery of load runtime for supply sources
    if msg_subtype == "loadTime":
        try:
            m = re.search(
                r"Power_source : (.*), Missed_consumption_time_in_secs : (.*), Last_synced_hour : (.*)",
                message,
            )
            if m is None:
                logger.warning("Could not parse sync info: %s", message)
                return True
            powerSource, missedTime, syncHour = m.groups()
            power_source = SupplyLoadTimeShare.objects.filter(power_source=int(powerSource))
            try:
                missed_time = float(missedTime)
            except ValueError:
                logger.warning("Invalid missedTime value: %s", missedTime)
                missed_time = 0.0
            last_synced_hour = datetime.strptime(syncHour, "%Y-%m-%d %H:%M:%S.%f")
            logger.info("Readings missed on server for %s seconds.", missed_time)
            logger.info(
                "Message received for recovery of runtime for %s",
                power_source[0].get_power_source_display(),
            )
            logger.info("Last synced datetime %s", last_synced_hour)
            recovery_data = power_source.filter(reading_to__gte=last_synced_hour)
            last_synced_hour = last_synced_hour.replace(minute=0, second=0, microsecond=0)
            recovery_hours, recovered_load_runtime = "", ""
            while current_time >= last_synced_hour:
                recovery_hours += last_synced_hour.strftime("%Y-%m-%d %H:%M:%S.%f") + ","
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
            logger.info("Load runtime recovery message sent to server.")
        except Exception as e:
            logger.exception("Exception in load runtime recovery block: %s", e)
        return True

    logger.warning("Received an unknown sync message: %s", message)
    return True
