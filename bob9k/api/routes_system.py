from __future__ import annotations
from flask import Flask, current_app
from bob9k.services.network_status import NetworkStatusService
def register_system_routes(app: Flask) -> None:
    @app.get('/api/system')
    def api_system():
        runtime = current_app.config['BOB9K_RUNTIME']; net = NetworkStatusService()
        return {'ok': True, 'ip': net.get_ip(), 'mode': runtime.state.mode, 'led_state': runtime.state.led_state}
    @app.post('/api/system/reboot')
    def api_system_reboot():
        import os
        os.system('sudo reboot')
        return {'ok': True}
