from __future__ import annotations

from bob9k.hardware.battery import BatteryMonitor
from bob9k.hardware.camera import CameraWrapper
from bob9k.hardware.camera_servo import CameraServoController
from bob9k.hardware.hat import HatContext
from bob9k.hardware.lights import RgbEyes
from bob9k.hardware.motors import MotorController
from bob9k.hardware.registry import HardwareRegistry, RuntimeContext
from bob9k.hardware.steering import SteeringController
from bob9k.hardware.switches import SwitchController
from bob9k.hardware.ultrasonic import UltrasonicSensor
from bob9k.services.status_leds import StatusLedService
from bob9k.services.telemetry import TelemetryService
from bob9k.services.gamepad import GamepadService
from bob9k.state import RuntimeState


class StartupManager:
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger

    def initialize(self) -> RuntimeContext:
        registry = HardwareRegistry()
        state = RuntimeState()
        runtime = RuntimeContext(
            config=self.config,
            logger=self.logger,
            registry=registry,
            state=state,
            telemetry=None,
            status_leds=None,
            gamepad=None,
        )
        try:
            registry.hat = HatContext(self.config, self.logger)
            registry.hat.initialize()

            registry.lights = RgbEyes(self.config, self.logger)
            registry.lights.initialize()
            registry.lights.off()

            runtime.status_leds = StatusLedService(registry.lights, state, self.config, self.logger)
            runtime.status_leds.set_state('BOOTING')

            registry.motors = MotorController(self.config, self.logger)
            registry.motors.stop()

            registry.steering = SteeringController(self.config, self.logger, registry.hat)
            registry.steering.center()
            state.steering_angle = registry.steering.angle

            registry.camera_servo = CameraServoController(self.config, self.logger, registry.hat)
            registry.camera_servo.home()
            state.pan_angle = registry.camera_servo.pan_angle
            state.tilt_angle = registry.camera_servo.tilt_angle

            registry.switches = SwitchController(self.config, self.logger)
            registry.switches.all_off()

            registry.ultrasonic = UltrasonicSensor(self.config, self.logger)
            registry.battery = BatteryMonitor(self.config, self.logger)

            registry.camera = CameraWrapper(self.config, self.logger)
            registry.camera.start()

            if self.config.get('gamepad_enabled', True):
                runtime.gamepad = GamepadService(runtime, self.logger)
                runtime.gamepad.start()
                try:
                    import subprocess, sys
                    if sys.platform.startswith('linux'):
                        subprocess.run(['rfkill', 'unblock', 'bluetooth'], check=False)
                except Exception:
                    pass
            else:
                runtime.gamepad = None
                try:
                    import subprocess, sys
                    if sys.platform.startswith('linux'):
                        subprocess.run(['rfkill', 'block', 'bluetooth'], check=False)
                except Exception:
                    pass

            from bob9k.services.tracking import TrackingService
            runtime.tracking = TrackingService(runtime, self.logger)
            runtime.tracking.start()

            from bob9k.services.patrol import PatrolService
            runtime.patrol = PatrolService(runtime, self.logger)
            runtime.patrol.start()

            runtime.telemetry = TelemetryService(runtime, self.logger)
            runtime.telemetry.poll_once()
            runtime.telemetry.start()
            return runtime
        except Exception:
            if getattr(runtime, 'status_leds', None):
                runtime.status_leds.set_state('ERROR')
            raise
