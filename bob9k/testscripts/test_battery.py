from _common import refuse_if_service_running; from bob9k.config import load_config; from bob9k.logging_setup import setup_logging; from bob9k.hardware.battery import BatteryMonitor
refuse_if_service_running(); config=load_config(); logger=setup_logging(config); b=BatteryMonitor(config, logger); print(f'Voltage: {b.read_voltage()}V | Status: {b.get_status()}')
