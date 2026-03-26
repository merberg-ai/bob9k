from __future__ import annotations
from flask import Flask, current_app, request
from bob9k.services.network_status import NetworkStatusService
from bob9k.services.version import get_version_info
from bob9k.config import load_runtime_config, save_runtime_config


def register_system_routes(app: Flask) -> None:
    @app.get('/api/system')
    def api_system():
        runtime = current_app.config['BOB9K_RUNTIME']
        net = NetworkStatusService()
        version = get_version_info()
        return {
            'ok': True,
            'ip': net.get_ip(),
            'mode': runtime.state.mode,
            'led_state': runtime.state.led_state,
            'version': version,
            'battery_override': runtime.config.get('battery', {}).get('disable_low_battery_lockout', False),
        }

    @app.post('/api/system/battery_override')
    def api_system_battery_override():
        runtime = current_app.config['BOB9K_RUNTIME']
        payload = request.get_json(force=True, silent=True) or {}
        override_val = bool(payload.get('override', False))

        runtime.config.setdefault('battery', {})['disable_low_battery_lockout'] = override_val
        
        runtime_cfg = load_runtime_config()
        runtime_cfg.setdefault('battery', {})['disable_low_battery_lockout'] = override_val
        save_runtime_config(runtime_cfg)

        return {'ok': True, 'battery_override': override_val}

    @app.post('/api/system/reboot')
    def api_system_reboot():
        import os
        os.system('sudo reboot')
        return {'ok': True}

    @app.post('/api/system/shutdown')
    def api_system_shutdown():
        import os
        os.system('sudo shutdown -h now')
        return {'ok': True}
