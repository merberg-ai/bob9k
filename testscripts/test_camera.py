from _common import refuse_if_service_running; from bob9k.config import load_config; from bob9k.logging_setup import setup_logging; from bob9k.hardware.camera import CameraWrapper
refuse_if_service_running(); config=load_config(); logger=setup_logging(config); c=CameraWrapper(config, logger); c.start(); print(f'Camera running: {c.running}'); c.stop()
