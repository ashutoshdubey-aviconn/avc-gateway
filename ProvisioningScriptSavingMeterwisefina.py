"""
Module ProvisioningScriptSavingMeterwisefina

Flow:
Top-level functions:
- detect_csv_kind
- fetch_aisle_groups_list
- extract_aisle_names_from_saving_csv
- extract_aisle_names_from_whtm_csv
- _normalize_name
- fetch_aisle_name_to_id_map
- map_topics_to_aisle_by_name
- fetch_db_aisle_names
- choose_customer
- add_site
Top-level classes:
- SmartEnergyDevice
- SmartEnergyConfigurator
- WHTMConfigurator
"""

import csv
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "warehouse.settings")

django.setup()

import json

import requests
from prettytable import PrettyTable

from wareApp.models import *
from wareApp.views import *

BASE_URL = "https://asem.aviconncorp.com/api/"
# LOCAL_URL = 'http://127.0.0.1:8001/api/'
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": r"e$&$xp0gc5wep%95=_s#@+m-s+9pp^*rx%7r+d+$iatu#0opav",
}


def detect_csv_kind(csv_path: str) -> str:
    try:
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            if not reader.fieldnames:
                return "unknown"
            fields = [fn.strip().lower() for fn in reader.fieldnames]
            fields_set = set(fields)
            print(f"DEBUG - Detected CSV columns: {fields_set}")

            # More flexible detection with variations
            # Check for Saving CSV
            has_dongle = any(col.startswith("dongle") for col in fields_set)
            has_meter = any(col.startswith("meter") for col in fields_set)
            has_leg = any(col.startswith("leg") for col in fields_set)
            has_aisle = any("aisle" in col for col in fields_set)

            if has_dongle and has_meter and has_leg:
                print(f"DEBUG - Detected as SAVING CSV")
                return "saving"

            # Check for WHTM CSV
            whtm_markers = {
                "supply source",
                "meter source number",
                "r-phase",
                "y-phase",
                "b-phase",
            }
            if whtm_markers.intersection(fields_set) and has_meter:
                print(f"DEBUG - Detected as WHTM CSV")
                return "whtm"

            print(f"DEBUG - CSV format not recognized.")
            print(f"  For Saving CSV, need: dongle + meter + leg columns")
            print(f"  For WHTM CSV, need: meter + supply source + phases")
            return "unknown"
    except FileNotFoundError:
        print(f"ERROR - File not found: {csv_path}")
        return "unknown"
    except Exception as e:
        print(f"ERROR - Exception while detecting CSV: {e}")
        return "unknown"


def fetch_aisle_groups_list() -> list:
    try:
        site_id = fetch_site_id()
        resp = requests.get(f"{BASE_URL}fetchAisleGroups/", headers=HEADERS, params={"site_id": site_id})
        data = resp.json()
        return data.get("aisle_groups", []) if isinstance(data, dict) else []
    except Exception:
        return []


def extract_aisle_names_from_saving_csv(csv_path: str) -> set:
    names = set()
    try:
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            if reader.fieldnames:
                reader.fieldnames = [fn.strip().lower() for fn in reader.fieldnames]
                print(f"DEBUG - CSV fieldnames: {reader.fieldnames}")
            for row in reader:
                # Try multiple variations of aisle group column name
                val = (row.get("aisle group") or row.get("aisle_group") or row.get("aisle") or "").strip()
                if val:
                    val_lower = val.lower()
                    names.add(val_lower)
                    print(f"DEBUG - Extracted aisle from CSV: '{val}' -> '{val_lower}'")
    except Exception as e:
        print(f"DEBUG - Error extracting aisle names: {e}")
    return names


def extract_aisle_names_from_whtm_csv(csv_path: str) -> set:
    names = set()
    try:
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f, skipinitialspace=True)
            if reader.fieldnames:
                reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
            for row in reader:
                val = (row.get("Aisle Group Name") or row.get("Aisle Group") or row.get("Aisle") or "").strip()
                if val:
                    names.add(val.lower())
    except Exception:
        pass
    return names


def _normalize_name(name: str) -> str:
    try:
        return (name or "").strip().lower()
    except Exception:
        return ""


def fetch_aisle_name_to_id_map() -> dict:
    mapping = {}
    try:
        site_pk = fetch_site_id()
        aisle_groups = AisleGroup.objects.filter(site_id=site_pk)
        for aisle_group in aisle_groups:
            mapping[_normalize_name(aisle_group.aisleGroupName)] = aisle_group.id
    except Exception as e:
        print(f"DEBUG - Error building local aisle map: {e}")
    return mapping


def map_topics_to_aisle_by_name(topic_aisle_pairs: list):
    name_to_id = fetch_aisle_name_to_id_map()
    saved = 0
    skipped = 0
    for topic, aisle_name in topic_aisle_pairs:
        aisle_id = name_to_id.get(_normalize_name(aisle_name))
        if not aisle_id:
            skipped += 1
            print(f"Skipping topic '{topic}': aisle group '{aisle_name}' not found in local gateway DB.")
            continue
        try:
            existing = SmartEnergyDevices.objects.filter(topic=topic).first()
            if existing:
                aisle_group = AisleGroup.objects.get(id=aisle_id)
                existing.associated_site = Site.objects.all()[0]
                existing.associated_aisle_group = aisle_group
                existing.device_type = 1
                existing.leg_id = aisle_id
                existing.save()
            else:
                create_smart_energy_devices({"topic": topic, "leg_id": aisle_id})
            saved += 1
        except Exception as e:
            skipped += 1
            print(f"Error saving topic '{topic}' for aisle group '{aisle_name}': {e}")
    if saved:
        print(f"Stored and mapped {saved} topics to local aisle groups from CSV.")
    if skipped:
        print(f"Skipped {skipped} topics because their aisle group could not be mapped or saved.")


def fetch_db_aisle_names() -> set:
    try:
        site_pk = fetch_site_id()
        from wareApp.models import AisleGroup as _AG

        qs = _AG.objects.filter(site_id=site_pk).values_list("aisleGroupName", flat=True)
        result = {(n or "").strip().lower() for n in qs if n}
        for n in qs:
            if n:
                print(f"DEBUG - DB aisle: '{n}' -> '{(n or '').strip().lower()}'")
        return result
    except Exception as e:
        print(f"DEBUG - Error fetching DB aisle names: {e}")
        return set()


def choose_customer():
    print("1. Create a new Customer")
    print("2. Choose from Existing Records")
    user_input = int(input("Choose how you wish to proceed : "))
    if user_input == 1:
        try:
            name = input("enter the name of the user : ")
            email = input("enter the user's email : ")
            contact = input("enter the user's contact : ")

            user_data = {
                "customer_name": name,
                "customer_email": email,
                "customer_contact": "contact",
            }

            response = requests.post(
                f"{BASE_URL}createCustomer/",
                headers=HEADERS,
                data=json.dumps(user_data),
            )
            response = response.json()

            if response.get("status") == 200:
                print("New Customer is created on the cloud")
                user_data["id"] = response.get("user_id")
                create_customer(user_data)
            else:
                print("There was some error while creating the Customer")
                exit()
        except Exception as e:
            return Response({"msg": str(e)})

    elif user_input == 2:
        try:
            response = requests.get(f"{BASE_URL}fetchAllCustomers/", headers=HEADERS)
            response = response.json()

            table = PrettyTable()
            table.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]

            for i in response["data"]:
                table.add_row([i["id"], i["username"], i["email"]])

            print(table)

            customer_ids = [i["id"] for i in response["data"]]
            print(customer_ids)

            customer_id = int(input("Enter the Customer you want to proceed with from the table : "))

            if customer_id not in customer_ids:
                print("Wrong ID")

            # user_data = {
            # "id": site_id
            # }

            response = requests.post(
                f"{BASE_URL}fetchParticularCustomer/",
                headers=HEADERS,
                data=json.dumps({"id": customer_id}),
            )

            if response.json().get("status") == 200:
                resp = response.json()
                user_data = {
                    "id": customer_id,
                    "customer_name": resp["username"],
                    "customer_email": resp["email"],
                    "customer_contact": resp["contact"],
                }
                create_customer(user_data)
        except Exception as e:
            return Response({"msg": str(e)})

    else:
        print("you chose an incorrect option, kindly retry")
        choose_customer()


def add_site():
    print("1. Create a new site for a customer")
    print("2. Choose existing customer and fetch sites")

    try:
        user_input = int(input("Choose from the above options (1/2): ").strip())
    except ValueError:
        print("Invalid input. Please enter 1 or 2.")
        return

    if user_input == 1:
        try:
            response = requests.get(f"{BASE_URL}fetchAllCustomers/", headers=HEADERS)
            data = response.json()

            if "data" not in data or not data["data"]:
                print("No customers found.")
                return

            table = PrettyTable()
            table.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]

            for customer in data["data"]:
                table.add_row([customer["id"], customer["username"], customer["email"]])

            print(table)

            customer_ids = [c["id"] for c in data["data"]]

            try:
                customer_id = int(input("Enter the Customer ID from the table: ").strip())
            except ValueError:
                print("Invalid customer ID.")
                return

            if customer_id not in customer_ids:
                print("Invalid customer ID chosen.")
                return

            site_name = input("Enter the name of the site: ").strip()
            print("Choose Site Type: \n 1. WH-Metering \n 2. WH Energy Saving \n 3. WH Asset tracking")
            try:
                site_type = int(input("Enter Site Type (1-3): ").strip())
            except ValueError:
                print("Invalid site type.")
                return
            site_location = input("Enter site location: ").strip()

            site_info = {
                "site_name": site_name,
                "site_type": site_type,
                "site_location": site_location,
                "customer_id": customer_id,
            }

            resp = requests.post(f"{BASE_URL}createSite/", headers=HEADERS, data=json.dumps(site_info))
            resp_data = resp.json()

            if resp_data.get("status") == 200:
                print(" New site created successfully on server.")
                site_info["site_id"] = resp_data.get("site_id")
                create_site(site_info)
            else:
                print(" Error creating site on server:", resp_data)

        except Exception as e:
            print("Error:", str(e))

    elif user_input == 2:
        try:
            response = requests.get(f"{BASE_URL}fetchAllCustomers/", headers=HEADERS)
            data = response.json()
            if "data" not in data or not data["data"]:
                print("No customers found.")
                return
            table = PrettyTable()
            table.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]
            for customer in data["data"]:
                table.add_row([customer["id"], customer["username"], customer["email"]])
            print(table)
            customer_ids = [c["id"] for c in data["data"]]
            try:
                customer_id = int(input("Enter the Customer ID to view sites: ").strip())
            except ValueError:
                print("Invalid customer ID.")
                return
            if customer_id not in customer_ids:
                print("Invalid customer ID chosen.")
                return

            resp = requests.get(f"{BASE_URL}allSitesList/", headers=HEADERS)
            try:
                resp_data = resp.json()
            except Exception:
                print("Error: Couldn't decode site list response as JSON.")
                print("Response text:", resp.text)
                return

            if "data" not in resp_data or not resp_data["data"]:
                print("No sites found.")
                return

            customer_sites = [site for site in resp_data["data"] if site.get("customer_id") == customer_id]

            if not customer_sites:
                print("No sites found for this customer.")
                return

            print("Sites for selected customer:")
            table = PrettyTable()
            table.field_names = ["Site_Id", "Site_Name", "Site_Type"]
            for site in customer_sites:
                table.add_row(
                    [
                        site["id"],
                        site["site_name"],
                        site["site_type"],
                    ]
                )
            print(table)

            site_ids = [site["id"] for site in customer_sites]
            try:
                selected_site_id = int(input("Enter the Site ID to save: ").strip())
            except ValueError:
                print("Invalid Site ID.")
                return
            site_to_save = next(
                (site for site in customer_sites if site["id"] == selected_site_id),
                None,
            )
            if not site_to_save:
                print("Invalid Site ID chosen.")
                return

            site_data = {
                "site_id": site_to_save["id"],
                "site_name": site_to_save["site_name"],
                "site_type": site_to_save["site_type"],
                "customer_id": site_to_save["customer_id"],
                "site_location": site_to_save["location"],
            }

            create_site(site_data)
            print("Selected site stored successfully .")

        except Exception as e:
            print("Error:", str(e))

    else:
        print("Invalid option. Please enter 1 or 2.")


def aisle_groups():
    print("1. Want to create a new aisle groups")
    print("2. Choose from an old site")

    try:
        user_input = int(input("Choose from the above 2 options : ").strip())
    except ValueError:
        print("Invalid input. Please enter 1 or 2.")
        return

    if user_input == 1:
        try:
            site_id = fetch_site_id()
            print(site_id)
            while True:
                aisle_name = input("Please enter aisle name : ").strip()
                aisle_data = {
                    "aisle_name": aisle_name,
                    "site_id": site_id,
                }

                site_type = fetch_site_type_from_gateway()
                aisle_data["site_type"] = site_type

                if site_type == 1:
                    print("Please choose power source from below options")
                    print("0. Mains Supply")
                    print("1. DG")
                    print("2. DG 1")
                    print("3. DG 2")
                    print("4. DG 3")
                    print("5. DG 4")

                    try:
                        power_source = int(input("Enter power source : ").strip())
                        if power_source not in range(6):
                            print("Invalid power source choice.")
                            continue
                    except ValueError:
                        print("Invalid input for power source.")
                        continue

                    aisle_data["power_source"] = power_source

                response = requests.post(
                    f"{BASE_URL}createAisleGroups/",
                    headers=HEADERS,
                    data=json.dumps(aisle_data),
                )
                resp_data = response.json()

                if resp_data.get("status") == 200:
                    aisle_data["aisle_id"] = resp_data.get("aisle_id")
                    print("Aisle created successfully")
                    create_aisle_group(aisle_data)
                else:
                    print("Error creating aisle group on server:", resp_data)

                print("\n1. Continue creating aisle group for this site")
                print("2. Exit")
                try:
                    cont_choice = int(input("Enter your choice: ").strip())
                    if cont_choice == 2:
                        break
                    elif cont_choice != 1:
                        print("Invalid choice, exiting.")
                        break
                except ValueError:
                    print("Invalid input, exiting.")
                    break

        except Exception as e:
            print("Error:", str(e))

    elif user_input == 2:
        try:
            site_id = fetch_site_id()
            print(site_id)
            response = requests.post(
                f"{BASE_URL}fetchAisleGroups/",
                headers=HEADERS,
                data=json.dumps({"site_id": site_id}),
            )
            resp_data = response.json()
            if "data" in resp_data and resp_data["data"]:
                print(f"\nAisle Groups for Site ID {site_id}:")
                for idx, aisle in enumerate(resp_data["data"], start=1):
                    print(f"{idx}. {aisle['aisleGroupName']}")

                for aisle in resp_data["data"]:
                    aisle_data = {
                        "site_id": site_id,
                        "aisle_name": aisle["aisleGroupName"],
                        "aisle_id": aisle.get("ched_leg_id", aisle.get("id", "")),
                    }
                    print(aisle_data)
                    create_aisle_group(aisle_data)
                print("All aisle groups stored successfully")
            else:
                print("No aisle groups found for this site or error occurred.")

            print("\nDo you want to create new aisle groups for this site?")
            print("1. Yes")
            print("2. No (Exit)")
            try:
                choice = int(input("Enter your choice: ").strip())
                if choice == 1:
                    while True:
                        aisle_name = input("Please enter aisle name : ").strip()
                        aisle_data = {
                            "aisle_name": aisle_name,
                            "site_id": site_id,
                        }
                        site_type = fetch_site_type_from_gateway()
                        aisle_data["site_type"] = site_type

                        if site_type == 1:
                            print("Please choose power source from below options")
                            print("0. Mains Supply")
                            print("1. DG")
                            print("2. DG 1")
                            print("3. DG 2")
                            print("4. DG 3")
                            print("5. DG 4")
                            try:
                                power_source = int(input("Enter power source : ").strip())
                                if power_source not in range(6):
                                    print("Invalid power source choice.")
                                    continue
                            except ValueError:
                                print("Invalid input for power source.")
                                continue
                            aisle_data["power_source"] = power_source
                            print(aisle_data)
                        response = requests.post(
                            f"{BASE_URL}createAisleGroups/",
                            headers=HEADERS,
                            data=json.dumps(aisle_data),
                        )
                        resp_data = response.json()
                        print(resp_data)
                        if resp_data.get("status") == 200:
                            aisle_data["aisle_id"] = resp_data.get("aisle_id")
                            print("Aisle created successfully")
                            create_aisle_group(aisle_data)
                        else:
                            print("Error creating aisle group on server:", resp_data)

                        print("\n1. Continue creating aisle group for this site")
                        print("2. Exit")
                        try:
                            cont_choice = int(input("Enter your choice: ").strip())
                            if cont_choice == 2:
                                break
                            elif cont_choice != 1:
                                print("Invalid choice, exiting.")
                                break
                        except ValueError:
                            print("Invalid input, exiting.")
                            break
                else:
                    print("Exiting aisle group management.")
            except ValueError:
                print("Invalid input. Exiting.")

        except Exception as e:
            print("Error:", str(e))

    else:
        print("Invalid option. Please enter 1 or 2.")


def home_gateway():
    try:
        site_id = fetch_site_id()
        if not site_id:
            print("No valid site ID found.")
            return

        print(f"Fetching Home Gateway IDs for Site ID {site_id}...")
        resp = requests.get(
            f"{BASE_URL}fetchHomeGatewayId/",
            headers=HEADERS,
            params={"site_id": site_id},
        )

        try:
            resp_json = resp.json()
        except Exception:
            print("Error: Could not decode response as JSON.")
            print("Response body:", resp.text)
            return

        gateways = resp_json.get("home_gateways", [])

        if not gateways:
            print("No home gateways found for this site.")
            return

        print("\nAvailable Home Gateways:")
        table = PrettyTable()
        table.field_names = ["Index", "Home_Gateway_ID", "RSSH_Port", "Monitoring_Port"]
        for idx, gw in enumerate(gateways, start=1):
            table.add_row([idx, gw.get("hgw_id"), gw.get("rssh_port"), gw.get("monitoring_port")])
        print(table)

        try:
            choice = int(input("Enter the index of the Home Gateway ID you want to select: ").strip())
        except ValueError:
            print("Invalid input.")
            return

        if choice < 1 or choice > len(gateways):
            print("Invalid choice.")
            return

        selected = gateways[choice - 1]
        selected_hgw = selected.get("hgw_id")
        rssh_port = selected.get("rssh_port")
        monitoring_port = selected.get("monitoring_port")

        print(f"You selected: {selected_hgw}")

        # Store in gateway database
        data = {
            "site_id": site_id,
            "home_gateway_name": selected_hgw,
            "rssh_port": rssh_port,
            "monitoring_port": monitoring_port,
        }

        create_home_gateway_id(data)
        print("Home gateway stored successfully in gateway database.")

    except Exception as e:
        print("Error:", str(e))


def reverse_ssh_conf(rssh_port, monitoring_port):
    """Configure reverse SSH by updating autossh.sh with the provided ports"""
    try:
        file_path = "/home/odroid/gateway-latest-code/autossh.sh"
        # Read the file
        with open(file_path, "rt") as fin:
            data = fin.read()

        # Replace port placeholders with actual values
        data = data.replace("$rPort", str(rssh_port)).replace("$mPort", str(monitoring_port))

        # Write the updated data back
        with open(file_path, "wt") as fin:
            fin.write(data)

        print("Reverse SSH configuration updated successfully.")
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"Error updating reverse SSH configuration: {e}")


def mosquitto_conf(siteId, hgwId):
    """Configure Mosquitto with site ID and home gateway ID"""
    try:
        file_path = "/etc/mosquitto/mosquitto.conf"
        import shutil

        backup = file_path + ".bak"
        try:
            shutil.copyfile(file_path, backup)
        except Exception:
            pass
        with open(file_path, "r", encoding="utf-8") as f:
            data = f.read()
        data = data.replace("siteId", str(siteId)).replace("hgwId", str(hgwId))
        tmp = file_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        subprocess.run(["mv", tmp, file_path], check=True)
        print("Mosquitto configuration updated successfully.")
        return
    except Exception as e:
        print(f"Error updating mosquitto configuration: {e}")


def pymodbus_conf(siteId, hgwId):
    """Configure pymodbus openhab_script with site ID and home gateway ID"""
    try:
        file_path = "/home/odroid/pymodbus/openhab_script.py"
        with open(file_path, "rt") as fin:
            data = fin.read()

        # Replace placeholders with actual values
        data = data.replace("$siteId", str(siteId)).replace("$hgwId", str(hgwId))

        with open(file_path, "wt") as fin:
            fin.write(data)

        print("Pymodbus configuration updated successfully.")
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"Error updating pymodbus configuration: {e}")


def network_conf(wpa_ssid, wpa_psk):
    """Configure network manager with WiFi credentials"""
    try:
        file_path = "/etc/network/interfaces"
        wpa_ssid_line = "wpa-ssid " + wpa_ssid
        wpa_psk_line = "wpa-psk  " + wpa_psk
        import shutil

        backup = file_path + ".bak"
        try:
            shutil.copyfile(file_path, backup)
        except Exception:
            pass
        with open(file_path, "r", encoding="utf-8") as f:
            data = f.read()
        data = data.replace("wpa-ssid Aviconn", wpa_ssid_line).replace("wpa-psk  Aviconn@32", wpa_psk_line)
        tmp = file_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        subprocess.run(["mv", tmp, file_path], check=True)
        print("Network manager configuration updated successfully.")
    except Exception as e:
        print(f"Error updating network configuration: {e}")


class SmartEnergyDevice:
    def __init__(
        self,
        dongle,
        meter_id,
        legs,
        aisle_group,
        location_id,
        instance_count=1,
        floor="",
        site_type=1,
        phase="",
    ):
        self.dongle = dongle
        self.floor = floor
        self.legs = [l for l in legs if l]
        self.meter_id = meter_id
        self.instance_count = instance_count
        self.site_type = site_type
        self.aisle_group = aisle_group
        self.phase = phase
        self.location_id = location_id
        self.usb_port = None

    def map_registers(self, topic: str):
        """
        Apply register mapping rules based on topic + site_type.
        Returns a row string for waveitems.
        """
        split_topic = topic.split("_")
        meter_name = ""
        register_to_read = 0

        # Initialize variables to avoid UnboundLocalError
        meter_id = ""
        instance = ""
        energyType = ""

        if len(split_topic) == 7:  # wh saving, metering, voltage, power, current
            meter_id = split_topic[4]
            instance = split_topic[5]
            energyType = split_topic[6]
        elif len(split_topic) == 6:  # wh metering, mains, dg load time
            meter_id = split_topic[4]
            meter_name = "meter" + str(meter_id) + "2"
            register_to_read = 0
        elif len(split_topic) == 5:  # apparent energy and energy in wh metering
            meter_id = split_topic[4]
            meter_name = "meter" + str(meter_id) + "3"
            register_to_read = 2
        elif len(split_topic) == 4:  # total wattage
            meter_id = split_topic[3]
            meter_name = "meter" + str(meter_id) + "0"
            register_to_read = 14
        elif len(split_topic) == 3:  # supply source status
            meter_id = split_topic[2]
            meter_name = "meter" + str(meter_id) + "1"
            register_to_read = 0
        else:
            return None  # invalid topic

        # ---- site_type-specific mapping ----
        if self.site_type == 2:  # wh energy saving
            if energyType == "0":
                meter_name = "meter" + str(meter_id) + "0"
            else:
                meter_name = "meter" + str(meter_id) + "1"

            if instance == "1":  # R-phase
                if energyType == "0":
                    register_to_read = 0
                elif energyType == "1":
                    register_to_read = 11
                elif energyType == "2":
                    register_to_read = 1
                elif energyType == "3":
                    register_to_read = 7
            elif instance == "2":  # Y-phase
                if energyType == "0":
                    register_to_read = 1
                elif energyType == "1":
                    register_to_read = 12
                elif energyType == "2":
                    register_to_read = 2
                elif energyType == "3":
                    register_to_read = 8
            elif instance == "3":  # B-phase
                if energyType == "0":
                    register_to_read = 2
                elif energyType == "1":
                    register_to_read = 13
                elif energyType == "2":
                    register_to_read = 3
                elif energyType == "3":
                    register_to_read = 9

        elif self.site_type == 1:  # wh metering
            if energyType in ("1", "2", "3"):  # voltage, current, power
                meter_name = "meter" + str(meter_id) + "0"
                if instance == "1":  # R-phase
                    if energyType == "1":
                        register_to_read = 6
                    elif energyType == "2":
                        register_to_read = 0
                    elif energyType == "3":
                        register_to_read = 3
                elif instance == "2":  # Y-phase
                    if energyType == "1":
                        register_to_read = 7
                    elif energyType == "2":
                        register_to_read = 1
                    elif energyType == "3":
                        register_to_read = 4
                elif instance == "3":  # B-phase
                    if energyType == "1":
                        register_to_read = 8
                    elif energyType == "2":
                        register_to_read = 2
                    elif energyType == "3":
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

        return f"{meter_name}|{topic}|{register_to_read}|Big|Big"

    def generate_waveitems(self):
        """
        Generate topics first, then map registers.
        """
        rows = []
        if self.site_type == 2:
            # WH-Energy-Saving: leg1→phase1, leg2→phase2, leg3→phase3
            legs_to_use = self.legs if self.legs else [""]
            for idx, leg_name in enumerate(legs_to_use, start=1):
                instance = str(min(idx, 3))
                for energyType in ["0", "1", "2", "3"]:
                    topic = f"METER_{self.location_id}_{self.floor}_{leg_name}_{self.meter_id}_{instance}_{energyType}"
                    row = self.map_registers(topic)
                    if row:
                        rows.append(row)
        else:
            # WH-Metering: per-phase types (1,2,3) and PF (4) map by leg→phase
            legs_to_use = self.legs if self.legs else [""]
            for idx, leg_name in enumerate(legs_to_use, start=1):
                instance = str(min(idx, 3))
                for energyType in ["1", "2", "3", "4"]:
                    topic = f"METER_{self.location_id}_{self.floor}_{leg_name}_{self.meter_id}_{instance}_{energyType}"
                    row = self.map_registers(topic)
                    if row:
                        rows.append(row)
            # Do not add aggregate total wattage topic for Saving output
        return rows

    def generate_openhab(self):
        """
        Generate openhab entries - 2 entries per meter for WH Metering
        Entry 0: meter{id}0 with address 2130|12
        Entry 1: meter{id}1 with address 1000|32
        """
        rows = []
        usb_port = f"/dev/ttyUSB{max(int(self.dongle) - 1, 0)}"
        # First entry with address 2130|12
        meter_name_0 = f"meter{self.meter_id}0"
        row_0 = f"{meter_name_0}|{usb_port}|9600|8|N|1|rtu|10|holding|float32|2130|12|{self.meter_id}|PROCOM12|1"
        rows.append(row_0)

        # Second entry with address 1000|32
        meter_name_1 = f"meter{self.meter_id}1"
        row_1 = f"{meter_name_1}|{usb_port}|9600|8|N|1|rtu|10|holding|float32|1000|32|{self.meter_id}|PROCOM12|1"
        rows.append(row_1)

        return rows


class SmartEnergyConfigurator:
    def __init__(self, devices_csv="devices.csv"):
        self.devices_csv = devices_csv
        self.devices = []

    def load_devices(self, location_id: str):
        """
        Read devices from CSV and attach user-provided location_id
        """
        try:
            with open(self.devices_csv, "r", newline="") as f:
                reader = csv.DictReader(f, skipinitialspace=True)

                # Normalize header names: strip spaces and lowercase
                if reader.fieldnames:
                    reader.fieldnames = [fn.strip().lower() for fn in reader.fieldnames]

                for raw_row in reader:
                    # Normalize row keys and strip string values
                    row = {
                        (k.strip().lower() if isinstance(k, str) else k): (v.strip() if isinstance(v, str) else v)
                        for k, v in raw_row.items()
                    }

                    # Robust accessors with fallbacks/defaults
                    def to_int(value, default=0):
                        try:
                            return int(value)
                        except Exception:
                            return default

                    try:
                        dongle_val = (
                            row.get("dongle") or row.get("dongle_id") or row.get("dongle no") or row.get("dongle_no")
                        )
                        floor_val = row.get("floor") or row.get("level") or ""
                        leg1_val = row.get("leg1") or row.get("leg 1") or row.get("leg") or row.get("leg_name") or ""
                        leg2_val = row.get("leg2") or row.get("leg 2") or ""
                        leg3_val = row.get("leg3") or row.get("leg 3") or ""
                        legs = [leg1_val, leg2_val, leg3_val]
                        meter_val = (
                            row.get("meter_id") or row.get("meter") or row.get("meter no") or row.get("meter_no") or ""
                        )
                        instance_val = row.get("instance_count") or 1
                        site_type_val = row.get("site_type") or 1
                        aisle_group_val = row.get("aisle group") or row.get("aisle_group") or row.get("aisle_id") or ""
                        phase_val = row.get("phase") or ""

                        device = SmartEnergyDevice(
                            dongle=to_int(dongle_val, 0),
                            meter_id=str(meter_val) if meter_val is not None else "",
                            legs=legs,
                            aisle_group=(str(aisle_group_val) if aisle_group_val is not None else ""),
                            location_id=location_id,
                            instance_count=to_int(instance_val, 1),
                            floor=floor_val,
                            site_type=to_int(site_type_val, 1),
                            phase=phase_val,
                        )
                        self.devices.append(device)
                    except Exception as row_err:
                        print(" Error parsing row:", row)
                        print(" Reason:", row_err)
        except Exception as e:
            print(f" Error reading CSV: {e}")

    def export_waveitems_csv(self, filepath="waveitems.csv"):
        rows = []
        for device in self.devices:
            rows.extend(device.generate_waveitems())
        # Enforce dual-source register mapping for Saving topics (site_type==2)
        remapped = []
        for r in rows:
            try:
                parts = r.split("|")
                if len(parts) < 3:
                    remapped.append(r)
                    continue
                topic = parts[1]
                reg = parts[2]
                tp = topic.split("_")
                # Saving topic format: METER_location_floor_leg_meter_instance_energyType
                if len(tp) == 7 and tp[0] == "METER":
                    instance = tp[5]
                    energy_type = tp[6]
                    if energy_type in ("1", "2", "3"):
                        if instance == "1":
                            new_reg = "11" if energy_type == "1" else ("1" if energy_type == "2" else "7")
                        elif instance == "2":
                            new_reg = "12" if energy_type == "1" else ("2" if energy_type == "2" else "8")
                        elif instance == "3":
                            new_reg = "13" if energy_type == "1" else ("3" if energy_type == "2" else "9")
                        else:
                            new_reg = reg
                        parts[2] = new_reg
                        r = "|".join(parts)
                remapped.append(r)
            except Exception:
                remapped.append(r)
        rows = remapped
        with open(filepath, "w") as f:
            f.write("\n".join(rows))
        print(f"Waveitems exported to {filepath}")

    def export_openhab_csv(self, filepath="openhab.csv"):
        rows = []
        for device in self.devices:
            device_rows = device.generate_openhab()
            # generate_openhab() now returns a list of rows
            if isinstance(device_rows, list):
                rows.extend(device_rows)
            else:
                rows.append(device_rows)
        with open(filepath, "w") as f:
            f.write("\n".join(rows))
        print(f"OpenHAB exported to {filepath}")


def SmartEnergyMenu():
    while True:
        file_name = input("Enter the CSV file name for Saving (default: devices.csv): ").strip() or "devices.csv"
        kind = detect_csv_kind(file_name)
        if kind == "saving":
            break
        elif kind == "whtm":
            print("You provided a WHTM CSV. Please upload a Saving CSV for this step.")
        else:
            print("Unrecognized CSV format. Please upload a valid Saving CSV.")

    # Validate CSV aisle groups against DB; if mismatch, don't proceed
    while True:
        csv_aisles = extract_aisle_names_from_saving_csv(file_name)
        db_aisles = fetch_db_aisle_names()
        print(f"DEBUG - CSV aisle groups: {csv_aisles}")
        print(f"DEBUG - DB aisle groups: {db_aisles}")
        missing = [a for a in csv_aisles if a and a not in db_aisles]
        if missing:
            print("CSV contains aisle groups not present in gateway. Missing:")
            for m in missing:
                print(f" - {m}")
            retry = input("Would you like to retry with a different CSV? (y/n, default n): ").strip().lower()
            if retry == "y":
                file_name = (
                    input("Please upload a correct Saving CSV with matching aisle groups: ").strip() or file_name
                )
                continue
            else:
                print("Proceeding anyway with available aisle groups...")
                break
        break

    location_id = fetch_site_id()
    print(f"Using Location ID from gateway: {location_id}")

    config = SmartEnergyConfigurator(file_name)
    config.load_devices(location_id)

    # Force Saving site_type for this flow to ensure Saving topics (energy types 0-3)
    for d in config.devices:
        d.site_type = 2

    # Automatically map topics to aisle groups by name from CSV (no prompt)
    topic_aisle_pairs = []
    for device in config.devices:
        rows = device.generate_waveitems()
        if device.aisle_group:
            for row in rows:
                parts = row.split("|")
                if len(parts) >= 2:
                    topic_aisle_pairs.append((parts[1], device.aisle_group))
    if topic_aisle_pairs:
        map_topics_to_aisle_by_name(topic_aisle_pairs)

    # Export CSVs
    config.export_waveitems_csv("waveitems.csv")
    config.export_openhab_csv("openhab.csv")

    try:
        site_id = fetch_site_id()
        home_gateway = fetch_home_gateway()
        pymodbus_conf(str(site_id), home_gateway.hgw_id)
    except Exception as e:
        print(f"Error configuring pymodbus after Saving export: {e}")


def fetch_aisle_group():
    try:
        site_pk = fetch_site_id()
        return list(AisleGroup.objects.filter(site_id=site_pk).values("id", "aisleGroupName"))
    except Exception:
        return []


def mainSaving():
    try:
        print("Welcome to Provisioning")
        while True:
            print("1. Choose Customer")
            print("2. Add Site")
            print("3. Create Aisle groups")
            print("4. Add HomeGateway Id")
            print("5. Smart Energy Meters Configuration")
            print("6. Reverse ssh Configuration")
            print("7. Network Manager Configuration")
            print("For quit enter 0")
            user_input = int(input("Enter the Action you want to Proceed with : "))
            if user_input == 0:
                break
            elif user_input == 1:
                choose_customer()
            elif user_input == 2:
                add_site()
            elif user_input == 3:
                aisle_groups()
            elif user_input == 4:
                home_gateway()
            elif user_input == 5:
                SmartEnergyMenu()
            elif user_input == 6:
                try:
                    home_gateway_obj = fetch_home_gateway()
                    if home_gateway_obj:
                        rssh_port = home_gateway_obj.rssh_port
                        monitoring_port = home_gateway_obj.monitoring_port
                        hgw_id = home_gateway_obj.hgw_id
                        site_id = fetch_site_id()

                        print(
                            f"Configuring Reverse SSH with rssh_port: {rssh_port}, monitoring_port: {monitoring_port}"
                        )
                        reverse_ssh_conf(rssh_port, monitoring_port)

                        print(f"Configuring Mosquitto with siteId: {site_id}, hgwId: {hgw_id}")
                        mosquitto_conf(site_id, hgw_id)
                    else:
                        print("No home gateway found. Please configure home gateway first (step 4).")
                except Exception as e:
                    print(f"Error in reverse SSH/Mosquitto configuration: {e}")
            elif user_input == 7:
                try:
                    wpa_ssid = input("Enter the WiFi SSID: ").strip()
                    wpa_psk = input("Enter the WiFi Password: ").strip()
                    if wpa_ssid and wpa_psk:
                        network_conf(wpa_ssid, wpa_psk)
                    else:
                        print("SSID and password cannot be empty.")
                except Exception as e:
                    print(f"Error in network configuration: {e}")
            else:
                break
    except KeyboardInterrupt as err:
        print("\nExiting")
        exit()
        ...
        ...


def mainWHTM():
    try:
        print("Welcome to Provisioning")
        while True:
            print("1. Choose Customer")
            print("2. Add Site")
            print("3. Create Aisle groups")
            print("4. Add HomeGateway Id")
            print("5. Smart Energy Meters Configuration for WHTM")
            print("6. Reverse ssh Configuration")
            print("7. Network Manager Configuration")
            print("For quit enter 0")
            user_input = int(input("Enter the Action you want to Proceed with : "))
            if user_input == 0:
                break
            elif user_input == 1:
                choose_customer()
            elif user_input == 2:
                add_site()
            elif user_input == 3:
                aisle_groups()
            elif user_input == 4:
                home_gateway()
            elif user_input == 5:
                meterConfigurationWHTM()
            elif user_input == 6:
                ...
            elif user_input == 7:
                ...
            else:
                break
    except KeyboardInterrupt as err:
        print("\nExiting")
        exit()
        ...
        ...


class WHTMConfigurator:
    def __init__(
        self,
        csv_path: str,
        location_id: str,
        include_load_data_topics: bool = True,
        include_apparent_energy_topics: bool = True,
    ):
        self.csv_path = csv_path
        self.location_id = location_id
        self.rows = []
        self.include_load_data_topics = include_load_data_topics
        self.include_apparent_energy_topics = include_apparent_energy_topics
        self.topic_aisle_pairs = []  # list of (topic, aisle_group_name)

    def load_csv(self):
        with open(self.csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                reader.fieldnames = [fn.strip() for fn in reader.fieldnames]
            for raw in reader:
                if not raw:
                    continue
                rec = {
                    (k.strip() if isinstance(k, str) else k): (v.strip() if isinstance(v, str) else v)
                    for k, v in raw.items()
                }
                if (
                    not rec.get("Meter")
                    and not rec.get("R-Phase")
                    and not rec.get("Y-Phase")
                    and not rec.get("B-Phase")
                ):
                    continue
                self.rows.append(rec)

    def build_openhab_rows_for_meter(self, meter_id: str, is_dual: bool) -> list:
        meter_id_str = str(meter_id)
        out = []
        # Generate 2 entries per meter for WH Metering: one with address 2130|12 and one with 1000|32
        for i in range(2):
            meter_name = f"meter{meter_id_str}{i}"
            if i == 0:
                line = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|float32|2130|12|{meter_id_str}|PROCOM12|1"
            else:  # i == 1
                line = f"{meter_name}|/dev/ttyUSB0|9600|8|N|1|rtu|10|holding|float32|1000|32|{meter_id_str}|PROCOM12|1"
            out.append(line)
        return out

    def map_topic_to_waveitems(self, topic: str) -> str:
        parts = topic.split("_")
        meter_name = ""
        register = 0
        if len(parts) == 7 and parts[0] == "METER":
            meter_id = parts[4]
            instance = parts[5]
            energy_type = parts[6]
            if energy_type in ("1", "2", "3"):
                meter_name = f"meter{meter_id}0"
                if instance == "1":
                    register = 11 if energy_type == "1" else (1 if energy_type == "2" else 7)
                elif instance == "2":
                    register = 12 if energy_type == "1" else (2 if energy_type == "2" else 8)
                elif instance == "3":
                    register = 13 if energy_type == "1" else (3 if energy_type == "2" else 9)
            elif energy_type == "0":
                meter_name = f"meter{meter_id}3"
                register = 1
            elif energy_type == "4":
                meter_name = f"meter{meter_id}4"
                register = 0 if parts[5] == "1" else (1 if parts[5] == "2" else 2)
        elif len(parts) == 6 and parts[0] == "METER":
            # No floor in topic: METER_location_leg_meter_instance_energyType
            meter_id = parts[3]
            instance = parts[4]
            energy_type = parts[5]
            if energy_type in ("1", "2", "3"):
                meter_name = f"meter{meter_id}0"
                if instance == "1":
                    register = 11 if energy_type == "1" else (1 if energy_type == "2" else 7)
                elif instance == "2":
                    register = 12 if energy_type == "1" else (2 if energy_type == "2" else 8)
                elif instance == "3":
                    register = 13 if energy_type == "1" else (3 if energy_type == "2" else 9)
            elif energy_type == "0":
                meter_name = f"meter{meter_id}3"
                register = 1
            elif energy_type == "4":
                meter_name = f"meter{meter_id}4"
                register = 0 if instance == "1" else (1 if instance == "2" else 2)
        elif len(parts) == 6:
            meter_id = parts[4]
            meter_name = f"meter{meter_id}2"
            register = 0
        elif len(parts) == 5:
            meter_id = parts[4]
            meter_name = f"meter{meter_id}3"
            register = 2
        elif len(parts) == 4:
            meter_id = parts[3]
            meter_name = f"meter{meter_id}0"
            register = 14
        elif len(parts) == 3:
            meter_id = parts[2]
            meter_name = f"meter{meter_id}1"
            register = 0
        return f"{meter_name}|{topic}|{register}|Big|Big"

    def aggregate_topics_for_meter(self, meter: str, supply_source_value: str, dual: bool) -> list:
        topics = [f"TOTAL_LOAD_WATTAGE_{meter}", f"SUPPLY_SOURCE_{meter}"]
        if dual:
            if self.include_load_data_topics:
                topics.append(f"SUPPLY_MAINS_LOAD_TIME_{meter}_{meter}")
                topics.append(f"DG_1_LOAD_TIME_{meter}_{meter}")
            if self.include_apparent_energy_topics:
                topics.append(f"SUPPLY_MAINS_APPARENT_ENERGY_{meter}")
                topics.append(f"DG_1_APPARENT_ENERGY_{meter}")
        else:
            try:
                ps = int(supply_source_value)
            except Exception:
                ps = 0
            mapping = {
                0: ("SUPPLY_MAINS",),
                1: ("DG_1",),
                2: ("DG_2",),
                3: ("DG_3",),
                4: ("DG_4",),
            }
            for prefix in mapping.get(ps, ("SUPPLY_MAINS",)):
                if self.include_load_data_topics:
                    topics.append(f"{prefix}_LOAD_TIME_{meter}_{meter}")
                if self.include_apparent_energy_topics:
                    topics.append(f"{prefix}_APPARENT_ENERGY_{meter}")
        return topics

    def generate(self):
        openhab_lines = []
        waveitems_lines = []

        for rec in self.rows:
            supply_source_raw = rec.get("Supply Source", "")
            meter_id_raw = rec.get("Meter", "")
            meter_src_num_raw = rec.get("Meter Source Number", "")
            r_leg = rec.get("R-Phase", "").strip()
            y_leg = rec.get("Y-Phase", "").strip()
            b_leg = rec.get("B-Phase", "").strip()
            floor_label = (rec.get("Floor") or rec.get("Level") or "").strip()

            if not meter_id_raw:
                continue

            meter_id = str(meter_id_raw).strip()
            is_dual = str(meter_src_num_raw).strip() == "2"

            openhab_lines.extend(self.build_openhab_rows_for_meter(meter_id, is_dual))

            legs = [("1", r_leg), ("2", y_leg), ("3", b_leg)]
            aisle_name = (rec.get("Aisle Group Name") or rec.get("Aisle Group") or rec.get("Aisle") or "").strip()
            for instance, leg_name in legs:
                if not leg_name:
                    continue
                for energy_type in ["1", "2", "3", "4", "0"]:
                    if floor_label:
                        topic = f"METER_{self.location_id}_{floor_label}_{leg_name}_{meter_id}_{instance}_{energy_type}"
                    else:
                        topic = f"METER_{self.location_id}_{leg_name}_{meter_id}_{instance}_{energy_type}"
                    waveitems_lines.append(self.map_topic_to_waveitems(topic))
                    if aisle_name:
                        self.topic_aisle_pairs.append((topic, aisle_name))

            for t in self.aggregate_topics_for_meter(meter_id, supply_source_raw, is_dual):
                waveitems_lines.append(self.map_topic_to_waveitems(t))

        def dedupe(seq):
            seen = set()
            out = []
            for item in seq:
                if item not in seen:
                    seen.add(item)
                    out.append(item)
            return out

        return dedupe(openhab_lines), dedupe(waveitems_lines)

    def export(
        self,
        openhab_lines: list,
        waveitems_lines: list,
        openhab_path: str = "openhab.csv",
        waveitems_path: str = "waveitems.csv",
    ):
        with open(openhab_path, "w") as f:
            f.write("\n".join(openhab_lines))
        with open(waveitems_path, "w") as f:
            f.write("\n".join(waveitems_lines))


def meterConfigurationWHTM():
    try:
        # WHTM-specific feature: ask whether to include certain topic groups BEFORE file selection
        ld_choice = input("Create load data topics (LOAD_TIME)? (y/n, default y): ").strip().lower()
        include_load_data = False if ld_choice == "n" else True
        ae_choice = input("Create apparent energy topics? (y/n, default y): ").strip().lower()
        include_apparent_energy = False if ae_choice == "n" else True
        print(
            f"Selected: LOAD_TIME={'Yes' if include_load_data else 'No'}, APPARENT_ENERGY={'Yes' if include_apparent_energy else 'No'}"
        )

        while True:
            csv_path = input("Enter WHTM CSV file path (leave blank to cancel): ").strip()
            if not csv_path:
                print("No CSV provided. Skipping WHTM topic creation.")
                return
            if not os.path.exists(csv_path):
                print("File not found. Please enter a valid file path.")
                continue
            kind = detect_csv_kind(csv_path)
            if kind == "whtm":
                break
            elif kind == "saving":
                print("You provided a Saving CSV. Please upload a WHTM CSV for this step.")
            else:
                print("Unrecognized CSV format. Please upload a valid WHTM CSV.")
        location_id = fetch_site_id()

        configurator = WHTMConfigurator(
            csv_path=csv_path,
            location_id=str(location_id),
            include_load_data_topics=include_load_data,
            include_apparent_energy_topics=include_apparent_energy,
        )
        configurator.load_csv()
        openhab_lines, waveitems_lines = configurator.generate()

        # Automatically map topics to aisle groups by name from CSV (no prompt)
        topic_aisle_pairs = []
        for topic, aisle_name in configurator.topic_aisle_pairs:
            topic_aisle_pairs.append((topic, aisle_name))
        if topic_aisle_pairs:
            map_topics_to_aisle_by_name(topic_aisle_pairs)

        configurator.export(
            openhab_lines,
            waveitems_lines,
            openhab_path="openhabWHTM.csv",
            waveitems_path="waveitemsWHTM.csv",
        )
        print("openhabWHTM.csv and waveitemsWHTM.csv generated successfully.")

    except KeyboardInterrupt:
        print("Cancelled.")
    except Exception as e:
        print("Error:", str(e))


def main():
    print("1. Wh Saving")
    print("2. WHTM Provisioning")
    print("3. Exit")
    user_input = int(input("Enter the Action you want to Proceed with : "))
    if user_input == 1:
        mainSaving()
    elif user_input == 2:
        mainWHTM()
    else:
        exit()


main()
