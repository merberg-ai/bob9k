from __future__ import annotations
from flask import Flask, current_app
from bob9k.services.network_status import NetworkStatusService
from bob9k.services.version import get_version_info


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
        }

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
