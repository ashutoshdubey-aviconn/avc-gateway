# flake8: noqa
import json
import os

from prettytable import PrettyTable

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wareh.settings")
import django  # noqa: E402

django.setup()  # noqa: E402

import requests  # noqa: E402

# import project.app.models
from wareh.wareApp.views import *  # noqa: F403,F405,E402

BASE_URL = "https://asem1.aviconn.in:8005/api/"
# LOCAL_BASE_URL = "http://localhost:8005/api/"
SECRET_KEY = {"Content-Type": "application/json", "Authorization": "e$&$xp0gc5wep%95=_s#@+m-s+9pp^*rx%7r+d+$iatu#0opav"}


def main():
    start = 1
    while start:
        print("Please choose from the below choices \n")
        print("1. Add Customer")
        print("2. Add Site")
        print("3. Add Aisle Group ")
        print("4. Add HomeGateway Id")
        print("5. Smart Energy Meters Configuration")
        # print("6. For openhab configuration")
        # print("7. For wave item configuration")
        # print("8. Mosquitto Configuration")
        print("6. Reverse ssh Configuration")
        print("7. Network Manager Configuration")
        print("8. Delete SmartEnergy volt,current,power topics")
        print("For quit enter 0")

        options = int(input("Enter your choice : "))
        # print("options: ", options)
        if options == 0:
            start = 0

        elif options == 1:  # for creating new customer
            print("1. For new customer on server.")
            print("2. Use existing customer.")
            print("3. view Customers on cloud server.")
            cust_options = int(input("Please enter your choice : "))
            if cust_options == 1:
                customer_name = input("Enter customer name : ")
                customer_email = input("Enter customer Email : ")
                customer_contact_number = input("Enter customer contact number : ")
                customer_data = {
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_contact": customer_contact_number,
                }
                customer = create_customer_on_global_cloud(json.dumps(customer_data))
                print("customer data : ", customer)
                if customer["status"] == 200:
                    print("customer created on cloud server. create customer here for gateway")
                    customer_data["id"] = customer["user_id"]
                    create_customer(customer_data)
            elif cust_options == 2:
                all_customer = fetch_customer_from_global_cloud()
                for i in all_customer["data"]:
                    print(
                        "customer_id = "
                        + str(i["id"])
                        + " "
                        + "customer name = "
                        + str(i["username"])
                        + " "
                        + "customer email = "
                        + str(i["email"])
                    )
                allCustomerIds = [i["id"] for i in all_customer["data"]]
                print(allCustomerIds)
                customer_id = int(input("Choose customer id for the site you wanna create"))
                if customer_id not in allCustomerIds:
                    print("you have entered wrong customer Id. Please choose from the right options")
                    break
                customer_data = fetch_particular_customer_from_global_cloud(json.dumps({"id": customer_id}))
                print("customer_data : ", customer_data, "type", type(customer_data))
                customer_name = customer_data["username"]
                customer_email = customer_data["email"]
                customer_contact_number = customer_data["contact"]
                customer_data = {
                    "id": customer_id,
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_contact": customer_contact_number,
                }
                customer = create_customer(customer_data)
                print("customer :", customer)
            elif cust_options == 3:
                all_customer = fetch_customer_from_global_cloud()
                x = PrettyTable()
                x.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]

                for i in all_customer["data"]:
                    x.add_row([i["id"], i["username"], i["email"]])
                print(x)

        elif options == 2:  # For creating new site
            all_customer = fetch_customer_from_global_cloud()
            x = PrettyTable()
            x.field_names = ["Customer_Id", "Customer_Name", "Customer_Email"]

            for i in all_customer["data"]:
                x.add_row([i["id"], i["username"], i["email"]])
                # print("customer_id = "+str(i.id) + " " + "customer name = " + str(i.username) + " " + "customer email = "+ str(i.email))
                # print("customer_id = "+str(i["id"]) + " " + "customer name = " + str(i["username"]) + " " + "customer email = "+ str(i["email"]))
            print(x)
            allCustomerIds = [i["id"] for i in all_customer["data"]]
            print(allCustomerIds)
            customer_id = int(input("Choose customer id for the site you wanna create : "))
            if customer_id not in allCustomerIds:
                print("You entered wrong customer id....")
                break
            site_name = input("Enter your site name : ")
            print("1. Wh Metering")
            print("2. Wh Energy Saving")
            print("3. Wh Asset tracking")
            site_type = input("Please enter site type : ")
            location = input("Enter site location : ")
            site_data = {
                "site_name": site_name,
                "site_type": site_type,
                "site_location": location,
                "customer_id": customer_id,
            }
            site = create_site_on_global_cloud(json.dumps(site_data))
            print("site", site)
            if site["status"] == 200:
                print("site created successfully on global cloud , create entry for gateway here")
                site_data["site_id"] = site["site_id"]
                create_site(site_data)

        elif options == 3:  # for creating aisle groups
            # all_sites = fetch_all_sites()
            # print("all_sites",all_sites)
            # x = PrettyTable()
            # x.field_names = ["Site_Id", "Site_Name", "Site_Location"]

            # for i in all_sites["data"]:
            #   x.add_row([i["id"], i["site_name"], i["location"]])
            # print(x)
            # print("site id = " + str(i["id"]) + " " + "site name = " + str(i["site_name"]) + " " + "location = " + str(i["location"]))
            # allSiteslist = [i["id"] for i in all_sites["data"]]
            # print(allSiteslist)
            # print("\n")
            site_id = fetch_site_id()
            aisleStart = 1
            while aisleStart:
                aisle_name = input("Please enter aisle name : ")
                aisle_data = {
                    "aisle_name": aisle_name,
                    "site_id": site_id,
                }
                # print("1. Wh Metering")
                # print("2. Wh Energy Saving")
                # print("3. Wh Asset tracking")
                site_type = fetch_site_type_from_gateway()
                aisle_data["site_type"] = site_type
                if site_type == 1:
                    print("please choose power sources from below options")
                    print("0. Mains Supply")
                    print("1. DG ")
                    print("2. DG 1")
                    print("3. DG 2")
                    print("4. DG 3")
                    print("5. DG 4")
                    power_source = int(input("Enter power source : "))
                    aisle_data["power_source"] = power_source
                aisle = create_aisle_group_for_particular_site(json.dumps(aisle_data))
                if aisle["status"] == 200:
                    aisle_data["aisle_id"] = aisle["aisle_id"]
                    print("aisle create successfully on cloud server. create on gateway")
                    create_aisle_group(aisle_data)
                    print("1. For continue creating aisle group for above site")
                    print("2. For exit")
                    choice = int(input("Enter from above choice : "))
                    if choice == 2:
                        aisleStart = 0

        elif options == 4:  # for creating home gateway id
            print("For creating entry for home gateway")
            # all_sites = fetch_site_id()

            # changes done here on august 3 2021
            last_hw_r_port = fetch_last_rssh_port()
            last_hw_r_port = last_hw_r_port["rssh_port"]
            # changes end here ....
            # x = PrettyTable()
            # x.field_names = ["Site_Id", "Site_Name", "Site_Location"]

            # for i in all_sites["data"]:
            # x.add_row([i["id"], i["site_name"], i["location"]])
            # print(x)

            # print("site id = " + str(i["id"]) + " " + "site name = " + str(i["site_name"]) + " " + "location = " + str(i["location"]))
            # allSiteslist = [i["id"] for i in all_sites["data"]]
            # print(allSiteslist)
            # print("\n")
            site_id = fetch_site_id()
            print("LocationId : ", site_id)
            home_gateway_name = input("Enter home gateway Id ex:(avc_sitename_locationname_0000locationid_gatewayid): ")
            # changes done here on august 3 2021
            if int(last_hw_r_port) < 40000:
                rssh_port = 40000
                monitoring_port = 40001
            else:
                rssh_port = int(last_hw_r_port) + 3
                print("rssh_Port : ", rssh_port)
                monitoring_port = int(last_hw_r_port) + 2
                print("monitoring_port : ", monitoring_port)
            # rssh_port = (input("Enter unique Rssh port : "))
            # monitoring_port = (input("enter unique monitoring port "))
            # changes end here .....
            data = {
                "site_id": site_id,
                "home_gateway_name": home_gateway_name,
                "rssh_port": rssh_port,
                "monitoring_port": monitoring_port,
            }
            homeGateway = create_home_gateway_id_server(json.dumps(data))
            print("homegateway", homeGateway)
            if homeGateway["status"] == 200:
                print("home gateway created successfully")
                create_home_gateway_id(data)

        elif options == 5:  # for creating smart energy devices entry in local gateway only
            print("saving database entry for smart energy devices ")
            location_id = fetch_site_id()
            all_aisle_groups = fetch_all_aisle_groups()
            print("all_aisle_groups :", all_aisle_groups)
            aisle_counter = 1
            while aisle_counter:
                for aisle in all_aisle_groups:
                    print("aisle name : " + aisle.aisleGroupName + " " + "aisle group id = " + str(aisle.aisle_grp_id))
                aisle_id = [i.id for i in all_aisle_groups]
                print(aisle_id)
                print("\n")
                aisleId = int(input("Please choose the aisle id :"))
                if aisleId not in aisle_id:
                    print("You entered wrong aisle id. Please choose correct option")
                    break
                # print("1. Warehouse Metering ")
                # print("2. Warehouse Energy Saving")
                siteType = fetch_site_type_from_gateway()
                # location_id = int(input("Enter location id : "))
                # instance_count = 1
                instance_count = int(input("Enter total number of instance to create : "))
                meter_id = input("Enter meter id : ")
                # while total_instance:
                floor = input("Enter floor type (GF, FF, SF,TF,FF) : ")
                leg_name = input("Enter leg name : ")

                # if siteType == 1:
                #     energy_type = input(
                #         "Enter Energy type (0, Energy), (1, Power), (2, Voltage), (3, Current), (4, Power Factor) : ")
                # else:
                #     energy_type = input("Enter Energy type (0, Energy), (1, Power), (2, Voltage), (3, Current),"
                #                         " (4, Power Factor) : ")

                if siteType == 1:  # for wh metering
                    for i in range(5):
                        topic = f"METER_{location_id}_{floor}_{leg_name}_{meter_id}_{instance_count}_{i}"
                        print("topic :", topic)
                        data = {"topic": topic, "leg_id": aisleId}
                        smart_device = create_smart_energy_devices(data)
                        print("Smart device entry successfully created")
                else:
                    for i in range(4):
                        topic = f"METER_{location_id}_{floor}_{leg_name}_{meter_id}_{instance_count}_{i}"
                        data = {"topic": topic, "leg_id": aisleId}
                        smart_device = create_smart_energy_devices(data)
                        print("Smart device entry successfully created")
                # instance_count += 1
                # total_instance -= 1

                # print(" Enter 1 to continue for same aisle group, 2 to exit")
                # choice = int(input("Enter your choice"))
                # if choice == 2:
                #     smart_count = 0
                aisle_choice = input("Enter 1 to create more smart energy devices for different aisle, 2 to exit")
                if int(aisle_choice) == 2:
                    aisle_counter = 0

            print("################ meter's configuration of openhab started ##################")
            all_meter_id = set()
            all_smart_devices = fetch_smart_energy_devices()
            print("all_smart_devices", all_smart_devices)
            for devices in all_smart_devices:
                topic = devices.topic
                split_topic = topic.split("_")
                meter_id = split_topic[4]
                all_meter_id.add(meter_id)
            for meterId in all_meter_id:
                print("meterId :", meterId)
                openhab = write_data_to_openhab(meterId, siteType)

            print("%%%%%%%%%%%%%%%%%%%%%%%%% Openhab configuration completed %%%%%%%%%%%%%%%%%%%%%")

            print("######################### meter conf for wave items started ######################3")
            all_smart_devices = fetch_smart_energy_devices()
            print(all_smart_devices)
            for devices in all_smart_devices:
                topic = devices.topic
                print("Topic :", topic)
                write_csv = write_data_to_wave_items(topic, siteType)
                # print("write_csv :",write_csv)

            print("%%%%%%%%%%%%%%%%%%%%%% Wave item configuration completed %%%%%%%%%%%%%%%%%%%%%")

            print("###################### mosquitto configuration started #######################33")
            site_id = fetch_site_id()
            print("site_id : ", site_id)
            home_gateway = fetch_home_gateway()
            hgwId = home_gateway.hgw_id
            print("home_gateway", hgwId)
            mosquitto_conf(str(site_id), hgwId)
            print("%%%%%%%%%%%%%%%%%%%%%%%%%%% mosquitto conf done %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

            print("###################### pymodbus configuration started #######################33")
            site_id = fetch_site_id()
            print("site_id : ", site_id)
            home_gateway = fetch_home_gateway()
            hgwId = home_gateway.hgw_id
            print("home_gateway", hgwId)
            pymodbus_conf(str(site_id), hgwId)
            print("%%%%%%%%%%%%%%%%%%%%%%%%%%% pymodbus configuration conf done %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

        elif options == 6:  # for reverse ssh configurations
            print("reverse ssh configurations")
            home_gateway = fetch_home_gateway()
            rssh_port = home_gateway.rssh_port  # home_gateway["rssh_port"]
            monitoring_port = home_gateway.monitoring_port
            reverse_ssh_conf(rssh_port, monitoring_port)
            print("reverse ssh conf done")

        elif options == 7:  # for network-manager configuration
            print("Network manager configurations")
            wpa_ssid = input("Enter the ssid : ")
            wpa_psk = input("Enter the password : ")
            network_conf(wpa_ssid, wpa_psk)
            print("Network conf sucessfully done")

        elif options == 8:
            print("Delete topics from smart energy meter table")
            all_topics = SmartEnergyDevices.objects.all()
            for topic in all_topics:
                x = topic.topic.split("_")
                if len(x) > 1:
                    last = int(x[-1])
                    if last != 0:
                        print("deleting topic : ", topic)
                        try:
                            SmartEnergyDevices.objects.filter(topic=topic.topic).delete()
                            print("topic deleted successfully")
                        except Exception as err:
                            print("Unable to delete topic : {}".format(topic.topic), err)

        else:
            print("invalid option selected. please choose from above options only")


# this function are used for creating and fetching data from the global server (asem1.aviconn.net)
def create_customer_on_global_cloud(data):
    customer = requests.post(BASE_URL + "createCustomer/", data=data, headers=SECRET_KEY)
    return customer.json()


def fetch_customer_from_global_cloud():
    all_customers = requests.get(BASE_URL + "fetchAllCustomers/", headers=SECRET_KEY)
    return all_customers.json()


def create_site_on_global_cloud(data):
    site = requests.post(BASE_URL + "createSite/", data=data, headers=SECRET_KEY)
    return site.json()


def fetch_particular_customer_from_global_cloud(data):
    customer = requests.post(BASE_URL + "fetchParticularCustomer/", data=data, headers=SECRET_KEY)
    return customer.json()


def fetch_all_sites():
    site = requests.get(BASE_URL + "allSitesList/", headers=SECRET_KEY)
    return site.json()


def create_aisle_group_for_particular_site(data):
    aisle_group = requests.post(BASE_URL + "createAisleGroups/", data=data, headers=SECRET_KEY)
    return aisle_group.json()


def fetch_aisle_groups_for_particular_site(data):
    aisle_group = requests.get(BASE_URL + "fetchAisleGroups/", data=data, headers=SECRET_KEY)
    return aisle_group.json()


# changes done here on 3 august 2021
def fetch_last_rssh_port():
    hwd = requests.get(BASE_URL + "fetchLastRsshPort/", headers=SECRET_KEY)
    return hwd.json()


def create_home_gateway_id_server(data):
    home_gateway_id = requests.post(BASE_URL + "createHomeGatewayId/", data=data, headers=SECRET_KEY)
    return home_gateway_id.json()


def fetch_home_gateway_id(data):
    home_gateway_id = requests.post(BASE_URL + "fetchHomeGatewayId/", data=data, headers=SECRET_KEY)
    return home_gateway_id.json()


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
    elif len(split_topic) == 3:  # for supply source status in wh metering only. It tells which source is running
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
        if energyType == "1" or energyType == "2" or energyType == "3":  # voltage, current , power
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
    with open("/home/odroid/pymodbus/newwaveitemsWHTM.csv", "r") as f:
        str_arr_csv = f.readlines()
        str_arr_csv = [i.strip() for i in str_arr_csv]
        print(str_arr_csv)
        if string not in str_arr_csv:
            print("not present")
            check_str = False
        else:
            print("already present")
    if not check_str:
        with open("/home/odroid/pymodbus/newwaveitemsWHTM.csv", "a") as f:
            f.write(string + " \n")


def mosquitto_conf(siteId, hgwId):
    filePath = "/etc/mosquitto/mosquitto.conf"
    command = "echo odroid | sudo -S sed -i 's/siteId/{}/g' {}".format(siteId, filePath)
    command1 = "echo odroid | sudo -S sed -i 's/hgwId/{}/g' {}".format(hgwId, filePath)
    import os

    os.system(command)
    os.system(command1)
    return


def reverse_ssh_conf(rssh_port, monitoring_port):
    fin = open("/home/odroid/gateway-latest-code/autossh.sh", "rt")
    data = fin.read()
    data = data.replace("$rPort", rssh_port).replace("$mPort", monitoring_port)
    fin.close()
    fin = open("/home/odroid/gateway-latest-code/autossh.sh", "wt")
    fin.write(data)
    fin.close()


def pymodbus_conf(siteId, hgwId):
    fin = open("/home/odroid/pymodbus/openhab_script.py", "rt")
    data = fin.read()
    data = data.replace("$siteId", siteId).replace("$hgwId", hgwId)
    fin.close()
    fin = open("/home/odroid/pymodbus/openhab_script.py", "wt")
    fin.write(data)
    fin.close()


def network_conf(wpa_ssid, wpa_psk):
    filePath = "/etc/network/interfaces"
    wpa_ssid = "wpa-ssid " + wpa_ssid
    wpa_psk = "wpa-psk  " + wpa_psk
    command = "echo odroid | sudo -S sed -i 's/wpa-ssid Aviconn/{}/g' {}".format(wpa_ssid, filePath)
    command1 = "echo odroid | sudo -S sed -i 's/wpa-psk  Aviconn@32/{}/g' {}".format(wpa_psk, filePath)
    import os

    os.system(command)
    os.system(command1)
    return


if __name__ == "__main__":
    main()
