from __future__ import annotations

from flask import Flask, current_app, request


def register_tracking_routes(app: Flask) -> None:
    @app.get('/api/tracking/state')
    def tracking_state():
        runtime = current_app.config['BOB9K_RUNTIME']
        return {
            'ok': True,
            'enabled': runtime.state.tracking_enabled,
            'mode': runtime.state.tracking_mode,
            'detector': runtime.state.tracking_detector,
            'target_acquired': runtime.state.tracking_target_acquired,
            'disable_reason': runtime.state.tracking_disable_reason,
        }

    @app.get('/api/tracking/config')
    def tracking_config():
        runtime = current_app.config['BOB9K_RUNTIME']
        cfg = runtime.tracking.get_config() if runtime.tracking else dict(runtime.config.get('tracking', {}))
        return {
            'ok': True,
            'config': cfg,
        }

    @app.get('/api/tracking/debug')
    def tracking_debug():
        runtime = current_app.config['BOB9K_RUNTIME']
        return {
            'ok': True,
            'enabled': runtime.state.tracking_enabled,
            'mode': runtime.state.tracking_mode,
            'detector': runtime.state.tracking_detector,
            'target_acquired': runtime.state.tracking_target_acquired,
            'disable_reason': runtime.state.tracking_disable_reason,
            'pan_angle': runtime.state.pan_angle,
            'tilt_angle': runtime.state.tilt_angle,
        }

    @app.post('/api/tracking/config')
    def tracking_update_config():
        runtime = current_app.config['BOB9K_RUNTIME']
        payload = request.get_json(force=True, silent=True) or {}
        if not runtime.tracking:
            return {'ok': False, 'error': 'tracking service unavailable'}, 503

        normalized, warnings = runtime.tracking.update_config(payload, persist=True)
        return {
            'ok': True,
            'config': normalized,
            'warnings': warnings,
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
