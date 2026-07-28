from datetime import datetime
from typing import Any


def build_source_status_message(entry: Any) -> Any:
    return (
        "Total_load :"
        + str(entry.Site_Total_Load)
        + ", R-phase-voltage :"
        + str(entry.r_volt)
        + ", Y-phase-voltage :"
        + str(entry.y_volt)
        + ", B-phase-voltage :"
        + str(entry.b_volt)
        + ", R-phase-current :"
        + str(entry.r_current)
        + ", Y-phase-current :"
        + str(entry.y_current)
        + ", B-phase-current :"
        + str(entry.b_current)
        + ", Power_Source :"
        + entry.Supply_Source
        + ", Status :"
        + entry.Status
        + ", Meter_number :"
        + str(entry.Meter_Number)
        + ", Message_created_time :"
        + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        + ", R-phase-power-factor :"
        + str(entry.r_power_factor)
        + ", Y-phase-power-factor :"
        + str(entry.y_power_factor)
        + ", B-phase-power-factor :"
        + str(entry.b_power_factor)
    )


def build_wattage_load_message(load_power: Any, leg_id: Any, meter_number: Any, created: Any, epoch_time: Any) -> Any:
    return (
        "LoadValue :"
        + str(load_power)
        + ", leg_id :"
        + str(leg_id)
        + ", Meter_Number :"
        + str(meter_number)
        + ", Datetime :"
        + created
        + ", epochTime :"
        + str(epoch_time)
    )


def build_supply_time_payload(
    power_source: Any, load_time: Any, current_load_time_cumulative: Any, created: Any
) -> Any:
    return (
        "Supply_Source :"
        + str(power_source)
        + ",Runtime :"
        + str(load_time)
        + ",Last_runtime_cumulative :"
        + str(current_load_time_cumulative)
        + ",Message_time :"
        + created
    )


def build_consumption_payload(time_difference_in_readings: Any, new_unit_consumption: Any) -> Any:
    return (
        "Consumption_time_in_sec :"
        + str(time_difference_in_readings)
        + ",Unit_consumption :"
        + str(new_unit_consumption)
        + ",Rc :1"
    )
