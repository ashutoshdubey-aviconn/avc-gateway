import os
import json
import logging
import subprocess
from prettytable import PrettyTable
from datetime import datetime
import time
from typing import List

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "warehouse.settings")
import django

django.setup()

# prefer explicit import namespace to avoid wildcard pollution in larger scripts
from wareApp import views as ware_views
import os
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from prettytable import PrettyTable

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "warehouse.settings")
import django

django.setup()

# avoid wildcard imports; wareApp.views exposes many helpers used by this script
from wareApp import views as ware_views
import requests
from django.contrib.auth import get_user_model

# Configuration
BASE_URL = os.environ.get("PROVISION_BASE_URL", "https://asem.aviconncorp.com/api/")
# secret token may come from environment for safety
ENV_SECRET = os.environ.get("PROVISION_SECRET_TOKEN")
if ENV_SECRET:
    SECRET_KEY = {"Content-Type": "application/json", "Authorization": ENV_SECRET}
else:
    SECRET_KEY = {
        "Content-Type": "application/json",
        "Authorization": "e$&$xp0gc5wep%95=_s#@+m-s+9pp^*rx%7r+d+$iatu#0opav",
    }

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# requests session with default timeout
SESSION = requests.Session()
DEFAULT_TIMEOUT = 10
logger = logging.getLogger(__name__)


def safe_read_lines(path: str) -> List[str]:
    try:
        with open(path, "r") as f:
            return [ln.strip() for ln in f.readlines()]
    except FileNotFoundError:
        logger.debug("File not found, returning empty list: %s", path)
        return []
    except Exception as exc:
        logger.exception("Error reading file %s: %s", path, exc)
        return []


def _ask_int(prompt: str, default: int | None = None) -> int:
    while True:
        try:
            val = input(prompt).strip()
            if not val and default is not None:
                return default
            return int(val)
        except ValueError:
            print("Please enter a valid integer.")


def interactive_menu():
    options_map = {
        1: "Add Customer",
        2: "Add Site",
        3: "Add Aisle Group",
        4: "Add HomeGateway Id",
        5: "Smart Energy Meters Configuration",
        6: "Reverse ssh Configuration",
        7: "Network Manager Configuration",
        8: "Delete SmartEnergy topics",
        0: "Quit",
    }

    while True:
        print("Please choose from the below choices:\n")
        for k in sorted(options_map.keys()):
            print(f"{k}. {options_map[k]}")

        choice = _ask_int("Enter your choice: ")
        if choice == 0:
            logger.info("Exiting interactive provisioning script")
            break

        if choice == 1:
            # Add customer
            print("1. For new customer on server.")
            print("2. Use existing customer.")
            print("3. View customers on cloud server.")
            sub = _ask_int("Please enter your choice: ")
            if sub == 1:
                name = input("Enter customer name: ").strip()
                email = input("Enter customer Email: ").strip()
                contact = input("Enter customer contact number: ").strip()
                data = {
                    "customer_name": name,
                    "customer_email": email,
                    "customer_contact": contact,
                }
                try:
                    resp = create_customer_on_global_cloud(json.dumps(data))
                    logger.info("customer response: %s", resp)
                    if resp.get("status") == 200:
                        data["id"] = resp.get("user_id")
                        ware_views.create_customer(data)
                except Exception:
                    logger.exception("Failed creating customer on cloud")
            elif sub == 2:
                # Use existing customer from global cloud
                try:
                    all_customer = fetch_customer_from_global_cloud()
                    data_list = (
                        all_customer.get("data")
                        if isinstance(all_customer, dict)
                        else None
                    )
                    if not data_list:
                        logger.error(
                            "No customers returned from cloud: %s", all_customer
                        )
                        continue
                    x = PrettyTable()
                    x.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]
                    for i in data_list:
                        x.add_row([i.get("id"), i.get("username"), i.get("email")])
                    print(x)
                    all_ids = [i.get("id") for i in data_list]
                    customer_id = _ask_int(
                        "Choose customer id for the site you wanna create: "
                    )
                    if customer_id not in all_ids:
                        logger.error("Invalid customer id chosen: %s", customer_id)
                        continue
                    # fetch particular customer details
                    cust_resp = fetch_particular_customer_from_global_cloud(
                        {"id": customer_id}
                    )
                    # API may return wrapper {"status":.., "data": {...}} or direct object
                    if isinstance(cust_resp, dict) and "data" in cust_resp:
                        cust = cust_resp.get("data") or {}
                    elif isinstance(cust_resp, dict):
                        cust = cust_resp
                    else:
                        logger.error(
                            "Unexpected customer detail response type: %s",
                            type(cust_resp),
                        )
                        continue

                    customer_name = cust.get("username") or cust.get("customer_name")
                    customer_email = cust.get("email") or cust.get("customer_email")
                    customer_contact = cust.get("contact") or cust.get(
                        "customer_contact"
                    )
                    customer_data = {
                        "id": customer_id,
                        "customer_name": customer_name,
                        "customer_email": customer_email,
                        "customer_contact": customer_contact,
                    }
                    UserModel = get_user_model()
                    if UserModel.objects.filter(id=customer_id).exists():
                        logger.info(
                            "Local user %s already exists, skipping creation",
                            customer_id,
                        )
                    else:
                        ware_views.create_customer(customer_data)
                        logger.info(
                            "Created local customer entry for id %s", customer_id
                        )
                except Exception:
                    logger.exception("Failed using existing customer")
            elif sub == 3:
                # View customers on cloud server
                try:
                    all_customer = fetch_customer_from_global_cloud()
                    x = PrettyTable()
                    x.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]
                    for i in all_customer.get("data", []):
                        x.add_row([i.get("id"), i.get("username"), i.get("email")])
                    print(x)
                except Exception:
                    logger.exception("Failed fetching customers for view")

        elif choice == 2:
            try:
                all_customer = fetch_customer_from_global_cloud()
                x = PrettyTable()
                x.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]
                for i in all_customer.get("data", []):
                    x.add_row([i.get("id"), i.get("username"), i.get("email")])
                print(x)
            except Exception:
                logger.exception("Failed fetching customers")

        elif choice == 3:
            # create aisle groups
            site_id = ware_views.fetch_site_id()
            aisle_start = True
            while aisle_start:
                aisle_name = input("Please enter aisle name: ").strip()
                aisle_data = {"aisle_name": aisle_name, "site_id": site_id}
                site_type = ware_views.fetch_site_type_from_gateway()
                aisle_data["site_type"] = site_type
                if site_type == 1:
                    ps = _ask_int("Enter power source (0..5): ")
                    aisle_data["power_source"] = ps
                try:
                    aisle = create_aisle_group_for_particular_site(
                        json.dumps(aisle_data)
                    )
                    if aisle.get("status") == 200:
                        aisle_data["aisle_id"] = aisle.get("aisle_id")
                        ware_views.create_aisle_group(aisle_data)
                except Exception:
                    logger.exception("Failed creating aisle group")
                cont = _ask_int("Enter 1 to continue, 2 to exit: ", default=2)
                if cont == 2:
                    aisle_start = False

        elif choice == 4:
            try:
                # prefer ware_views implementation if available
                last_hw = getattr(ware_views, "fetch_last_rssh_port", None)
                if callable(last_hw):
                    last_hw = last_hw()
                else:
                    last_hw = fetch_last_rssh_port()
                last_hw_r_port = last_hw.get("rssh_port")
                site_id = ware_views.fetch_site_id()
                home_gateway_name = input("Enter home gateway Id: ").strip()
                if int(last_hw_r_port) < 40000:
                    rssh_port = 40000
                    monitoring_port = 40001
                else:
                    rssh_port = int(last_hw_r_port) + 3
                    monitoring_port = int(last_hw_r_port) + 2
                data = {
                    "site_id": site_id,
                    "home_gateway_name": home_gateway_name,
                    "rssh_port": rssh_port,
                    "monitoring_port": monitoring_port,
                }
                resp = create_home_gateway_id_server(json.dumps(data))
                logger.info("home gateway response: %s", resp)
                if resp.get("status") == 200:
                    ware_views.create_home_gateway_id(data)
            except Exception:
                logger.exception("Failed creating home gateway")

        elif choice == 5:
            # simplified smart energy devices creation flow
            try:
                location_id = ware_views.fetch_site_id()
                all_aisle_groups = ware_views.fetch_all_aisle_groups()
                for aisle in all_aisle_groups:
                    print(
                        f"aisle name: {getattr(aisle,'aisleGroupName',None)} id: {getattr(aisle,'aisle_grp_id',None)}"
                    )
                aisle_ids = [getattr(i, "id", None) for i in all_aisle_groups]
                aisleId = _ask_int("Please choose the aisle id: ")
                if aisleId not in aisle_ids:
                    logger.error("Invalid aisle id chosen")
                    continue
                siteType = ware_views.fetch_site_type_from_gateway()
                instance_count = _ask_int("Enter total number of instance to create: ")
                meter_id = input("Enter meter id: ").strip()
                floor = input("Enter floor type (GF, FF,...): ").strip()
                leg_name = input("Enter leg name: ").strip()
                count_range = 5 if siteType == 1 else 4
                for i in range(count_range):
                    topic = f"METER_{location_id}_{floor}_{leg_name}_{meter_id}_{instance_count}_{i}"
                    data = {"topic": topic, "leg_id": aisleId}
                    ware_views.create_smart_energy_devices(data)
                logger.info("Created smart energy device topics for meter %s", meter_id)
            except Exception:
                logger.exception("Failed smart energy device creation")

        elif choice == 6:
            try:
                home_gateway = ware_views.fetch_home_gateway()
                reverse_ssh_conf(home_gateway.rssh_port, home_gateway.monitoring_port)
            except Exception:
                logger.exception("Failed reverse ssh config")

        elif choice == 7:
            try:
                wpa_ssid = input("Enter the ssid: ").strip()
                wpa_psk = input("Enter the password: ").strip()
                network_conf(wpa_ssid, wpa_psk)
            except Exception:
                logger.exception("Failed network config")

        elif choice == 8:
            try:
                from wareApp.models import SmartEnergyDevices

                all_topics = SmartEnergyDevices.objects.all()
                for topic in all_topics:
                    x = topic.topic.split("_")
                    if len(x) > 1:
                        last = int(x[-1])
                        if last != 0:
                            logger.info("deleting topic: %s", topic.topic)
                            SmartEnergyDevices.objects.filter(
                                topic=topic.topic
                            ).delete()
            except Exception:
                logger.exception("Failed deleting topics")

        else:
            logger.warning("Invalid option selected: %s", choice)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Provisioning helper script")
    parser.add_argument(
        "--non-interactive", action="store_true", help="Run non-interactive checks only"
    )
    parser.add_argument(
        "--test-api",
        action="store_true",
        help="Run a quick API fetch/create test and print responses (useful for debugging)",
    )
    args = parser.parse_args(argv)
    if args.test_api:
        _test_api_calls()
        return

    if args.non_interactive:
        logger.info("Running non-interactive checks")
        # placeholder for future non-interactive actions
        return

    interactive_menu()


# this function are used for creating and fetching data from the global server (asem1.aviconn.net)
def create_customer_on_global_cloud(data):
    # Accept either a dict (preferred) or a JSON string
    if isinstance(data, str):
        resp = SESSION.post(
            BASE_URL + "createCustomer/",
            data=data,
            headers=SECRET_KEY,
            timeout=DEFAULT_TIMEOUT,
        )
    else:
        resp = SESSION.post(
            BASE_URL + "createCustomer/",
            json=data,
            headers=SECRET_KEY,
            timeout=DEFAULT_TIMEOUT,
        )
    try:
        return resp.json()
    except ValueError:
        logger.error(
            "Non-JSON response from create_customer_on_global_cloud: %s", resp.text
        )
        return {"status": resp.status_code, "text": resp.text}


def fetch_customer_from_global_cloud():
    try:
        resp = SESSION.get(
            BASE_URL + "fetchAllCustomers/", headers=SECRET_KEY, timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.exception("Error fetching customers: %s", exc)
        # return a structured error for callers
        return {
            "status": getattr(exc.response, "status_code", None),
            "error": str(exc),
            "text": getattr(exc.response, "text", None),
        }


def create_site_on_global_cloud(data):
    resp = SESSION.post(
        BASE_URL + "createSite/", data=data, headers=SECRET_KEY, timeout=DEFAULT_TIMEOUT
    )
    return resp.json()


def fetch_particular_customer_from_global_cloud(data):
    resp = SESSION.post(
        BASE_URL + "fetchParticularCustomer/",
        data=data,
        headers=SECRET_KEY,
        timeout=DEFAULT_TIMEOUT,
    )
    return resp.json()


def fetch_all_sites():
    resp = SESSION.get(
        BASE_URL + "allSitesList/", headers=SECRET_KEY, timeout=DEFAULT_TIMEOUT
    )
    return resp.json()


def create_aisle_group_for_particular_site(data):
    resp = SESSION.post(
        BASE_URL + "createAisleGroups/",
        data=data,
        headers=SECRET_KEY,
        timeout=DEFAULT_TIMEOUT,
    )
    return resp.json()


def fetch_aisle_groups_for_particular_site(data):
    resp = SESSION.get(
        BASE_URL + "fetchAisleGroups/",
        params=data,
        headers=SECRET_KEY,
        timeout=DEFAULT_TIMEOUT,
    )
    return resp.json()


# changes done here on 3 august 2021
def fetch_last_rssh_port():
    resp = SESSION.get(
        BASE_URL + "fetchLastRsshPort/", headers=SECRET_KEY, timeout=DEFAULT_TIMEOUT
    )
    return resp.json()


def create_home_gateway_id_server(data):
    resp = SESSION.post(
        BASE_URL + "createHomeGatewayId/",
        data=data,
        headers=SECRET_KEY,
        timeout=DEFAULT_TIMEOUT,
    )
    return resp.json()


def _test_api_calls():
    """Run quick API checks: fetch customers and attempt creating a dry-run customer.
    Prints full responses for debugging."""
    logger.info("Testing API: fetching customers from %s", BASE_URL)
    customers = fetch_customer_from_global_cloud()
    print("FETCH_CUSTOMERS_RESULT:\n", json.dumps(customers, indent=2, default=str))

    # try creating a test customer
    test_data = {
        "customer_name": "test_user_from_script",
        "customer_email": "test@example.local",
        "customer_contact": "000",
    }
    logger.info("Testing API: creating test customer (won't be used) at %s", BASE_URL)
    create_resp = create_customer_on_global_cloud(test_data)
    print("CREATE_CUSTOMER_RESULT:\n", json.dumps(create_resp, indent=2, default=str))


def fetch_home_gateway_id(data):
    resp = SESSION.post(
        BASE_URL + "fetchHomeGatewayId/",
        data=data,
        headers=SECRET_KEY,
        timeout=DEFAULT_TIMEOUT,
    )
    return resp.json()


def write_data_to_openhab(meterId, site_type):
    if site_type == 2:  # for wh energy saving only
        for i in range(2):
            meter_name = "meter" + str(meterId) + str(i)
            if i == 0:
                string = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|float32|2000|12|{meterId}|PROCOM12|1"
            else:
                string = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|float32|1000|32|{meterId}|PROCOM12|1"
            save_to_openhab_csv(string)
    elif site_type == 1:  # for wh metering only
        for i in range(5):
            meter_name = "meter" + str(meterId) + str(i)
            if i == 0:
                # for power, voltage, current, total wattage
                string = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|float32|1000|32|{meterId}|PROCOM12|1"
            elif i == 1:
                # for supply source status
                string = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|long|1000|2|{meterId}|PROCOM12|1"
            elif i == 2:
                # for mains and dg load time
                string = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|long|2202|4|{meterId}|PROCOM12|1"
            elif i == 3:
                # for energy and apparent energy
                string = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|float32|2202|6|{meterId}|PROCOM12|1"
            elif i == 4:
                # for power factor
                string = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|float32|1054|6|{meterId}|PROCOM12|1"
            save_to_openhab_whtm_csv(string)


def write_data_to_wave_items(topic, site_type):
    split_topic = topic.split("_")
    print("split topic : ", split_topic)
    if len(split_topic) == 7:  # for wh saving, and metering, voltage, power, current
        print("topic length 7")
        meter_id = split_topic[4]
        instance = split_topic[5]
        energyType = split_topic[6]
    elif len(split_topic) == 6:  # for wh metering, mains and dg load time
        meter_id = split_topic[4]
        meter_name = "meter" + str(meter_id) + "2"
        register_to_read = 0
    elif len(split_topic) == 5:  # for apparent energy and energy in wh metering only
        meter_id = split_topic[4]
        meter_name = "meter" + str(meter_id) + "3"
        register_to_read = 2
    elif len(split_topic) == 4:  # for total wattage in wh metering only
        meter_id = split_topic[3]
        meter_name = "meter" + str(meter_id) + "0"
        register_to_read = 14
    elif (
        len(split_topic) == 3
    ):  # for supply source status in wh metering only. It tells which source is running
        meter_id = split_topic[2]
        meter_name = "meter" + str(meter_id) + "1"
        register_to_read = 0
    if site_type == 2:  # for wh energy saving only
        print("inside site type 1 enery-saving")
        if energyType == "0":
            meter_name = "meter" + str(meter_id) + "0"
        else:
            meter_name = "meter" + str(meter_id) + "1"
        print("meter name : ", meter_name)
        if instance == "1":  # For R-Phase
            print("instance 1")
            print("energy type :", energyType)
            if energyType == "0":  # For Energy

                register_to_read = 0
            elif energyType == "1":  # For Power

                register_to_read = 6
            elif energyType == "2":  # For Voltage
                register_to_read = 0
            elif energyType == "3":  # For Current
                register_to_read = 3
            print("register to read ", register_to_read)
        elif instance == "2":  # For Y-Phase
            print("instance 2")
            if energyType == "0":  # For Energy
                register_to_read = 1
            elif energyType == "1":  # For Power
                register_to_read = 7
            elif energyType == "2":  # For Voltage
                register_to_read = 1
            elif energyType == "3":  # For Current
                register_to_read = 4
        elif instance == "3":  # For B-Phase
            print("instance 3")
            if energyType == "0":  # For Energy
                register_to_read = 2
            elif energyType == "1":  # For Power
                register_to_read = 8
            elif energyType == "2":  # For Voltage
                register_to_read = 2
            elif energyType == "3":  # For Current
                register_to_read = 5
        string = f"{meter_name}|{topic}|{register_to_read}|Big|Big"
        save_to_wave_item_csv(string)
    elif site_type == 1:  # for wh metering
        print("inside wh-metering")
        if (
            energyType == "1" or energyType == "2" or energyType == "3"
        ):  # voltage, current , power
            meter_name = "meter" + str(meter_id) + "0"
            if len(split_topic) == 7:
                if instance == "1":  # For R-Phase
                    if energyType == "1":  # For Power
                        register_to_read = 6
                    elif energyType == "2":  # For Voltage
                        register_to_read = 0
                    elif energyType == "3":  # For Current
                        register_to_read = 3
                elif instance == "2":  # For Y-Phase
                    if energyType == "1":  # For Power
                        register_to_read = 7
                    elif energyType == "2":  # For Voltage
                        register_to_read = 1
                    elif energyType == "3":  # For Current
                        register_to_read = 4
                elif instance == "3":  # For B-Phase
                    if energyType == "1":  # For Power
                        register_to_read = 8
                    elif energyType == "2":  # For Voltage
                        register_to_read = 2
                    elif energyType == "3":  # For Current
                        register_to_read = 5
        elif energyType == "0":
            meter_name = "meter" + str(meter_id) + "3"
            register_to_read = 1
        elif energyType == "4":
            meter_name = "meter" + str(meter_id) + "4"
            if instance == "1":
                register_to_read = 0
            elif instance == "2":
                register_to_read = 1
            elif instance == "3":
                register_to_read = 2
        string = f"{meter_name}|{topic}|{register_to_read}|Big|Big"
        save_to_wave_item_whtm_csv(string)


def save_to_openhab_csv(string):
    check_str = True
    with open("/home/odroid/pymodbus/newopenhab.csv", "r") as f:
        str_arr_csv = f.readlines()
        str_arr_csv = [i.strip() for i in str_arr_csv]
        print(str_arr_csv)
        if string not in str_arr_csv:
            print("not present")
            check_str = False
        else:
            print("already present")
    if not check_str:
        with open("/home/odroid/pymodbus/newopenhab.csv", "a") as f:
            f.write(string + " \n")


def save_to_openhab_whtm_csv(string):
    check_str = True
    with open("/home/odroid/pymodbus/newopenhabWHTM.csv", "r") as f:
        str_arr_csv = f.readlines()
        str_arr_csv = [i.strip() for i in str_arr_csv]
        print(str_arr_csv)
        if string not in str_arr_csv:
            print("not present")
            check_str = False
        else:
            print("already present")
    if not check_str:
        with open("/home/odroid/pymodbus/newopenhabWHTM.csv", "a") as f:
            f.write(string + " \n")


def save_to_wave_item_csv(string):
    check_str = True
    with open("/home/odroid/pymodbus/newwaveitems.csv", "r") as f:
        str_arr_csv = f.readlines()
        str_arr_csv = [i.strip() for i in str_arr_csv]
        print(str_arr_csv)
        if string not in str_arr_csv:
            print("not present")
            check_str = False
        else:
            print("already present")
    if not check_str:
        with open("/home/odroid/pymodbus/newwaveitems.csv", "a") as f:
            f.write(string + " \n")


def save_to_wave_item_whtm_csv(string):
    check_str = True
    with open(
        "/home/ashutosh-dubey/Documents/odroid/gateway-latest-code/wh-project/newwaveitemsWHTM.csv",
        "r",
    ) as f:
        str_arr_csv = f.readlines()
        str_arr_csv = [i.strip() for i in str_arr_csv]
        print(str_arr_csv)
        if string not in str_arr_csv:
            print("not present")
            check_str = False
        else:
            print("already present")
    if not check_str:
        with open(
            "/home/ashutosh-dubey/Documents/odroid/gateway-latest-code/wh-project/newwaveitemsWHTM.csv",
            "a",
        ) as f:
            f.write(string + " \n")


def mosquitto_conf(siteId, hgwId):
    filePath = "/etc/mosquitto/mosquitto.conf"
    import shutil

    try:
        backup = filePath + ".bak"
        shutil.copyfile(filePath, backup)
    except Exception:
        pass
    try:
        with open(filePath, "r", encoding="utf-8") as f:
            data = f.read()
        data = data.replace("siteId", str(siteId)).replace("hgwId", str(hgwId))
        tmp = filePath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        subprocess.run(["mv", tmp, filePath], check=True)
    except Exception:
        logger.exception("Failed to update %s", filePath)
    return


def reverse_ssh_conf(rssh_port, monitoring_port):
    path = "/home/odroid/gateway-latest-code/autossh.sh"
    try:
        with open(path, "r", encoding="utf-8") as fin:
            data = fin.read()
        data = data.replace("$rPort", str(rssh_port)).replace(
            "$mPort", str(monitoring_port)
        )
        with open(path, "w", encoding="utf-8") as fout:
            fout.write(data)
    except Exception:
        logger.exception("Failed to update autossh script at %s", path)


def pymodbus_conf(siteId, hgwId):
    path = "/home/odroid/pymodbus/openhab_script.py"
    try:
        with open(path, "r", encoding="utf-8") as fin:
            data = fin.read()
        data = data.replace("$siteId", str(siteId)).replace("$hgwId", str(hgwId))
        with open(path, "w", encoding="utf-8") as fout:
            fout.write(data)
    except Exception:
        logger.exception("Failed to update pymodbus openhab script at %s", path)


def network_conf(wpa_ssid, wpa_psk):
    filePath = "/etc/network/interfaces"
    wpa_ssid = "wpa-ssid " + wpa_ssid
    wpa_psk = "wpa-psk  " + wpa_psk
    import shutil

    try:
        backup = filePath + ".bak"
        shutil.copyfile(filePath, backup)
    except Exception:
        pass
    try:
        with open(filePath, "r", encoding="utf-8") as f:
            data = f.read()
        data = data.replace("wpa-ssid Aviconn", wpa_ssid).replace(
            "wpa-psk  Aviconn@32", wpa_psk
        )
        tmp = filePath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        subprocess.run(["mv", tmp, filePath], check=True)
    except Exception:
        logger.exception("Failed to update network config %s", filePath)
    return


if __name__ == "__main__":
    main()
