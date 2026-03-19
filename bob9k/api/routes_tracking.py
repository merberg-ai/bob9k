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
            'target_locked': runtime.state.tracking_target_locked,
            'target_lock_frames': runtime.state.tracking_target_lock_frames,
            'target_label': runtime.state.tracking_target_label,
            'target_confidence': runtime.state.tracking_target_confidence,
            'target_area_ratio': runtime.state.tracking_target_area_ratio,
            'disable_reason': runtime.state.tracking_disable_reason,
            'detect_only_mode': runtime.state.tracking_detect_only_mode,
        }

    @app.get('/api/tracking/config')
    def tracking_config():
        runtime = current_app.config['BOB9K_RUNTIME']
        cfg = runtime.tracking.get_config() if runtime.tracking else dict(runtime.config.get('tracking', {}))
        return {
            'ok': True,
            'config': cfg,
        }

    @app.get('/api/tracking/detectors')
    def tracking_detectors():
        runtime = current_app.config['BOB9K_RUNTIME']
        if not runtime.tracking:
            return {'ok': False, 'error': 'tracking service unavailable'}, 503
        return {
            'ok': True,
            'status': runtime.tracking.get_detector_status(),
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
            'target_locked': runtime.state.tracking_target_locked,
            'target_lock_frames': runtime.state.tracking_target_lock_frames,
            'target_switch_reason': runtime.state.tracking_target_switch_reason,
            'target_lost_age_s': runtime.state.tracking_target_lost_age_s,
            'target_label': runtime.state.tracking_target_label,
            'target_confidence': runtime.state.tracking_target_confidence,
            'target_area_ratio': runtime.state.tracking_target_area_ratio,
            'error_x': runtime.state.tracking_error_x,
            'error_y': runtime.state.tracking_error_y,
            'disable_reason': runtime.state.tracking_disable_reason,
            'detect_only_mode': runtime.state.tracking_detect_only_mode,
            'detector_status': runtime.state.tracking_detector_status,
            'pan_angle': runtime.state.pan_angle,
            'tilt_angle': runtime.state.tilt_angle,
            'tracking_box': runtime.state.tracking_box,
            'debug': runtime.state.tracking_debug,
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

    @app.post('/api/tracking/detect_only')
    def tracking_detect_only():
        runtime = current_app.config['BOB9K_RUNTIME']
        payload = request.get_json(force=True, silent=True) or {}
        enabled = bool(payload.get('enabled', True))
        if not runtime.tracking:
            return {'ok': False, 'error': 'tracking service unavailable'}, 503
        normalized, warnings = runtime.tracking.update_config({'detect_only_mode': enabled}, persist=True)
        return {'ok': True, 'config': normalized, 'warnings': warnings}

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
