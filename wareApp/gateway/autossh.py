"""
Migrated gateway.autossh into wareApp.gateway.autossh
"""

import logging
import time
from typing import Iterable

import paho.mqtt.client as mqtt

from wareApp.constants.topics import remote_access_state_topic
from wareApp.models import HomeGatewayId

logger = logging.getLogger(__name__)


def handle_remote_access(client: mqtt.Client, msg: mqtt.MQTTMessage, message: str, msg_type: Iterable[str]) -> bool:
    if "remoteAccess" not in msg_type:
        return False

    gw_id = HomeGatewayId.objects.first()
    if not gw_id:
        logger.warning("No HomeGatewayId record for remote access.")
        return True

    message_parts = message.split("_")
    action = message_parts[0] if message_parts else ""
    autossh_retry_count = int(message_parts[1]) if len(message_parts) > 1 and message_parts[1].isdigit() else 0
    topicsend = remote_access_state_topic(gw_id.connected_to.id, gw_id.hgw_id)

    if action == "start":
        logger.info("Starting autossh.")
        try:
            import subprocess

            subprocess.run(["pkill", "-f", "autossh"], check=False)
        except Exception:
            logger.exception("Failed to pkill autossh")

        autossh_cmd = [
            "autossh",
            "-M",
            str(gw_id.monitoring_port),
            "-fN",
            "-o",
            "PubkeyAuthentication=yes",
            "-o",
            "PasswordAuthentication=no",
            "-R",
            f"{gw_id.rssh_port}:localhost:22",
            "aviconn@asem1.aviconn.in",
        ]
        logger.debug("autossh command: %s", " ".join(autossh_cmd))
        try:
            subprocess.run(autossh_cmd, check=True)
        except Exception:
            logger.exception("Failed to start autossh")

        count = 0
        while count < autossh_retry_count:
            time.sleep(5)
            try:
                status = subprocess.check_output(["pgrep", "autossh"]).decode().split("\n")[0]
            except Exception:
                status = ""
            if status != "":
                logger.info("Autossh started successfully.")
                break
            logger.info("Retrying autossh")
            try:
                subprocess.run(autossh_cmd, check=True)
            except Exception:
                logger.exception("Retry autossh failed")
            count += 1
        if count >= autossh_retry_count:
            try:
                Rssh_port_check = (
                    subprocess.check_output(
                        [
                            "sh",
                            "-c",
                            f"netstat -plant | grep {gw_id.rssh_port}",
                        ]
                    )
                    .decode()
                    .split("\n")[0]
                )
            except Exception:
                Rssh_port_check = "Not in listen mode."
            Rport_status = "Rport_status : " + Rssh_port_check
            try:
                Monitoring_port_check = (
                    subprocess.check_output(
                        [
                            "sh",
                            "-c",
                            f"netstat -plant | grep {gw_id.monitoring_port}",
                        ]
                    )
                    .decode()
                    .split("\n")[0]
                )
            except Exception:
                Monitoring_port_check = "Not in listen mode."
            Mport_status = "Mport_status : " + Monitoring_port_check
            client.publish(
                topicsend,
                "Autossh failed to start on gateway.\n" + Rport_status + "\n" + Mport_status,
                qos=1,
                retain=False,
            )
            payload_msg = f"Autossh failed to start; operator intervention required for gateway id {gw_id.hgw_id}."
            logger.warning(payload_msg)
            client.publish(topicsend, payload_msg, qos=1, retain=False)
            return True
        client.publish(topicsend, "Autossh started successfully.", qos=1, retain=False)
        return True

    if action == "stop":
        logger.info("Stopping autossh!")
        try:
            import subprocess

            subprocess.run(["pkill", "-f", "autossh"], check=False)
        except Exception:
            logger.exception("Failed to pkill autossh")
        payload_msg = "Autossh has been stopped. Operator should verify Rssh and Monitoring ports."
        logger.info(payload_msg)
        client.publish(topicsend, payload_msg, qos=1, retain=False)
        return True

    if action == "restart":
        logger.info("Got a command from server to restart the gateway.")
        payload_msg = "Restart requested: operator intervention required. Run 'sudo reboot' manually."
        logger.warning("Restart requested for gateway %s; manual reboot required.", gw_id.hgw_id)
        client.publish(topicsend, payload_msg, qos=1, retain=False)
        return True

    payload_msg = "Got an unknown command for rssh."
    logger.warning(payload_msg)
    client.publish(topicsend, payload_msg, qos=1, retain=False)
    return True
