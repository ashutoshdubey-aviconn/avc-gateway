"""Load measurement handlers package.

Modules under `load` process meter-derived load telemetry such as wattage,
voltage, current, power-factor, supply source selection and runtime
aggregation. Handlers are intended to be called from the central MQTT
router and return a boolean indicating whether they consumed the message.
"""
