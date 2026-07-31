"""MQTT package initialization.

This package provides MQTT clients and a central router used by the gateway
process. The primary entrypoints are `mqtt.client1.start_client` and
`mqtt.client2.start_client` which establish broker connections and forward
messages to `mqtt.router.route_message` for processing.
"""
