"""OpenHAB simulation script.

This script simulates MQTT messages produced by OpenHAB/energy meters for
local testing. It generates realistic-looking numeric payloads for a set of
predefined meter topics, publishes them using `mosquitto_pub`, and logs the
published values with timestamps.

Flow:
- `generate_value(topic)` produces a value based on topic suffixes (e.g.
    wattage, voltage, power factor) and keeps incremental state for `_0`
    aggregate topics.
- `publish(topic)` formats the MQTT topic using the local gateway pattern and
    invokes `mosquitto_pub` to publish the generated payload.
- `simulate()` groups topics by meter blocks, publishes them sequentially and
    logs timing information.

Run:
    Set `MQTT_HOST` and `MQTT_PORT` environment variables if needed and run the
    script. It loops and publishes periodically when executed as `__main__`.
"""

import os
import random
import time
from datetime import datetime, timezone

# Dictionary to store last known values for _0 topics
incremental_topics = {}


def log(msg):
    try:
        ts = datetime.now(timezone.utc)
    except Exception:
        ts = datetime.now()
    print(f"{ts} : {msg}")


def generate_value(topic):
    if topic.endswith("_0"):
        # Increment by 2 or 3 units if topic seen before, else start at random base
        last_val = incremental_topics.get(topic, random.uniform(5000, 7000))
        increment = random.uniform(2, 3)
        new_val = last_val + increment
        incremental_topics[topic] = new_val
        return round(new_val, 4)
    else:
        # Generate random float between ranges for general topics
        if "WATTAGE" in topic:
            return round(random.uniform(500, 600), 4)
        elif topic.endswith("_4"):
            return round(random.uniform(0.95, 1.0), 6)
        elif topic.endswith("_3"):
            return round(random.uniform(0.83, 0.85), 6)
        elif topic.endswith("_2"):
            return round(random.uniform(228, 231), 6)
        elif topic.endswith("_1"):
            return round(random.uniform(190, 197), 6)
        elif "SOURCE" in topic or "TIME" in topic or "ENERGY" in topic:
            return random.randint(0, 1)
        else:
            return round(random.uniform(0, 1), 4)


def publish(topic):
    value = generate_value(topic)
    mqtt_host = os.environ.get("MQTT_HOST", "localhost")
    mqtt_port = os.environ.get("MQTT_PORT", "1883")
    mqtt_topic = f"/asem/aviconn/164/avc_office_office_000164_1/out/{topic}/localstate"
    mqtt_cmd = f'mosquitto_pub -h {mqtt_host} -p {mqtt_port} -t "{mqtt_topic}" -m "{value}"'
    os.system(mqtt_cmd)
    # subprocess.call(mqtt_cmd, shell=True)
    log(f"Published to {topic} with value: {value}")


def simulate():
    log("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  Function START $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    start_time = datetime.now(timezone.utc)
    log(f"function start time is :  {start_time}")

    def meter_block(name, topics):
        time.sleep(2)
        log(f"{name} is CONNECTED on portId /dev/ttyUSB0")
        for topic in topics:
            publish(topic)
        log(f"{name} has been Connected")

    meter_block(
        "meter10",
        [
            "METER_164_GF_L11_1_1_1",
            "METER_164_GF_L11_1_1_2",
            "METER_164_GF_L11_1_1_3",
            "METER_164_GF_L12_1_2_1",
            "METER_164_GF_L12_1_2_2",
            "METER_164_GF_L12_1_2_3",
            "METER_164_GF_L13_1_3_1",
            "METER_164_GF_L13_1_3_2",
            "METER_164_GF_L13_1_3_3",
            "TOTAL_LOAD_WATTAGE_1",
        ],
    )

    meter_block("meter11", ["SUPPLY_SOURCE_1"])
    meter_block("meter12", ["SUPPLY_MAINS_LOAD_TIME_1_1"])
    meter_block("meter13", ["METER_164_GF_L11_1_1_0", "SUPPLY_MAINS_APPARENT_ENERGY_1"])
    meter_block(
        "meter14",
        ["METER_164_GF_L11_1_1_4", "METER_164_GF_L12_1_2_4", "METER_164_GF_L13_1_3_4"],
    )

    meter_block(
        "meter20",
        [
            "METER_164_GF_L14_2_1_1",
            "METER_164_GF_L14_2_1_2",
            "METER_164_GF_L14_2_1_3",
            "METER_164_GF_L15_2_2_1",
            "METER_164_GF_L15_2_2_2",
            "METER_164_GF_L15_2_2_3",
            "METER_164_GF_L16_2_3_1",
            "METER_164_GF_L16_2_3_2",
            "METER_164_GF_L16_2_3_3",
            "TOTAL_LOAD_WATTAGE_2",
        ],
    )

    meter_block("meter21", ["SUPPLY_SOURCE_2"])
    meter_block("meter22", ["DG_1_LOAD_TIME_2_2"])
    meter_block("meter23", ["METER_164_GF_L14_2_1_0", "DG_1_APPARENT_ENERGY_2"])
    meter_block(
        "meter24",
        ["METER_164_GF_L14_2_1_4", "METER_164_GF_L15_2_2_4", "METER_164_GF_L16_2_3_4"],
    )

    end_time = datetime.now(timezone.utc)
    log(f"function end time is :  {end_time}")
    log(f"total time taken in seconds is  :  {(end_time - start_time).total_seconds()}")
    log("#############################  Function END #######################################")


if __name__ == "__main__":
    while True:
        time.sleep(10)
        simulate()
