from datetime import datetime

from wareApp.models import SiteLoadPower


def build_source_status_message(entry: SiteLoadPower) -> str:
    return (
        f"Total_load :{entry.Site_Total_Load}, R-phase-voltage :{entry.r_volt}, Y-phase-voltage :{entry.y_volt}, B-phase-voltage :{entry.b_volt}, "
        f"R-phase-current :{entry.r_current}, Y-phase-current :{entry.y_current}, B-phase-current :{entry.b_current}, Power_Source :{entry.Supply_Source}, Status :{entry.Status}, "
        f"Meter_number :{entry.Meter_Number}, Message_created_time :{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}, "
        f"R-phase-power-factor :{entry.r_power_factor}, Y-phase-power-factor :{entry.y_power_factor}, B-phase-power-factor :{entry.b_power_factor}"
    )


def build_wattage_load_message(
    load_power: float,
    leg_id: int | str,
    meter_number: str,
    created: str,
    epoch_time: int,
) -> str:
    return f"LoadValue :{load_power}, leg_id :{leg_id}, Meter_Number :{meter_number}, Datetime :{created}, epochTime :{epoch_time}"


def build_supply_time_payload(
    power_source: int | str,
    load_time: float,
    current_load_time_cumulative: float,
    created: str,
) -> str:
    return f"Supply_Source :{power_source},Runtime :{load_time},Last_runtime_cumulative :{current_load_time_cumulative},Message_time :{created}"


def build_consumption_payload(time_difference_in_readings: float, new_unit_consumption: float) -> str:
    return f"Consumption_time_in_sec :{time_difference_in_readings},Unit_consumption :{new_unit_consumption},Rc :1"
