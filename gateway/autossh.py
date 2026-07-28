import os
import time

from wareApp.models import HomeGatewayId
from constants.topics import remote_access_state_topic


def handle_remote_access(client, msg, message, msg_type):
    if "remoteAccess" not in msg_type:
        return False

    gw_id = HomeGatewayId.objects.first()
    if not gw_id:
        print("No HomeGatewayId record for remote access.")
        return True

    message_parts = message.split("_")
    action = message_parts[0] if message_parts else ""
    autossh_retry_count = (
        int(message_parts[1])
        if len(message_parts) > 1 and message_parts[1].isdigit()
        else 0
    )
    topicsend = remote_access_state_topic(gw_id.connected_to.id, gw_id.hgw_id)

    if action == "start":
        print("Starting autossh.")
        os.system("pgrep autossh | xargs kill -9")
        command = (
            "autossh -M "
            + gw_id.monitoring_port
            + ' -fN -o "PubkeyAuthentication=yes" -o "PasswordAuthentication=no"  -R '
            + gw_id.rssh_port
            + ":localhost:22 aviconn@asem1.aviconn.in"
        )
        print(command)
        os.system(command)
        count = 0
        while count < autossh_retry_count:
            time.sleep(5)
            status = os.popen("pgrep autossh").read().split("\n")[0]
            if status != "":
                print("Autossh started successfully.")
                break
            print("Retrying autossh")
            os.system(command)
            count += 1
        if count >= autossh_retry_count:
            Rssh_port_check = (
                os.popen("netstat -plant | grep " + gw_id.rssh_port)
                .read()
                .split("\n")[0]
            )
            if len(Rssh_port_check) == 0:
                Rssh_port_check = "Not in listen mode."
            Rport_status = "Rport_status : " + Rssh_port_check
            Monitoring_port_check = (
                os.popen("netstat -plant | grep " + gw_id.monitoring_port)
                .read()
                .split("\n")[0]
            )
            if len(Monitoring_port_check) == 0:
                Monitoring_port_check = "Not in listen mode."
            Mport_status = "Mport_status : " + Monitoring_port_check
            client.publish(
                topicsend,
                "Autossh failed to start on gateway.\n"
                + Rport_status
                + "\n"
                + Mport_status,
                qos=1,
                retain=False,
            )
            os.system("echo odroid | sudo -S fuser -k " + gw_id.rssh_port + "/tcp")
            os.system(
                "echo odroid | sudo -S fuser -k " + gw_id.monitoring_port + "/tcp"
            )
            msg = "Rssh and monitoring port restarted for gateway id {}.".format(
                gw_id.hgw_id
            )
            print(msg)
            client.publish(topicsend, msg, qos=1, retain=False)
            return True
        client.publish(topicsend, "Autossh started successfully.", qos=1, retain=False)
        return True

    if action == "stop":
        print("Stopping autossh!")
        os.system("echo odroid | sudo -S pgrep autossh | xargs kill -9")
        os.system("echo odroid | sudo -S fuser -k " + gw_id.rssh_port + "/tcp")
        os.system("echo odroid | sudo -S fuser -k " + gw_id.monitoring_port + "/tcp")
        msg = "Autossh has been stopped. Rssh and Monitoring ports have been closed."
        print(msg)
        client.publish(topicsend, msg, qos=1, retain=False)
        return True

    if action == "restart":
        print("Got a command from server to restart the gateway.")
        os.system("echo odroid | sudo -S init 6")
        msg = "Gateway has been restarted."
        print(msg)
        client.publish(topicsend, msg, qos=1, retain=False)
        return True

    msg = "Got an unknown command for rssh."
    print(msg)
    client.publish(topicsend, msg, qos=1, retain=False)
    return True
