from __future__ import annotations
from flask import Flask, current_app, request

def register_tracking_routes(app: Flask) -> None:
    @app.get('/api/tracking/state')
    def tracking_state():
        runtime = current_app.config['BOB9K_RUNTIME']
        return {
            'ok': True,
            'enabled': runtime.state.tracking_enabled
        }

    @app.post('/api/tracking/toggle')
    def tracking_toggle():
        runtime = current_app.config['BOB9K_RUNTIME']
        if runtime.tracking:
            runtime.tracking.toggle()
        return {
            'ok': True,
            'enabled': runtime.state.tracking_enabled
        }

    @app.post('/api/tracking/enable')
    def tracking_enable():
        runtime = current_app.config['BOB9K_RUNTIME']
        if runtime.tracking:
            runtime.tracking.enable()
        return {
            'ok': True,
            'enabled': runtime.state.tracking_enabled
        }

    @app.post('/api/tracking/disable')
    def tracking_disable():
        runtime = current_app.config['BOB9K_RUNTIME']
        if runtime.tracking:
            runtime.tracking.disable()
        return {
            'ok': True,
            'enabled': runtime.state.tracking_enabled
        }
