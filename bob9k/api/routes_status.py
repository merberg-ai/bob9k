from __future__ import annotations
from flask import Flask, Response, current_app, request


def register_status_routes(app: Flask) -> None:
    @app.get('/api/status')
    def api_status():
        runtime = current_app.config['BOB9K_RUNTIME']
        return runtime.telemetry.get_snapshot()

    @app.get('/api/camera/status')
    def api_camera_status():
        runtime = current_app.config['BOB9K_RUNTIME']
        cam = runtime.registry.camera
        return {
            'ok': True,
            'running': bool(cam and cam.running),
        }

    @app.get('/video_feed')
    def video_feed():
        runtime = current_app.config['BOB9K_RUNTIME']
        cam = runtime.registry.camera
        if not cam or not cam.running:
            return Response('camera unavailable', status=503, mimetype='text/plain')
        view = (request.args.get('view') or '').strip().lower()
        if getattr(runtime, 'tracking', None):
            if view == 'tracking':
                gen = runtime.tracking.mjpeg()
            elif getattr(runtime.state, 'tracking_overlay_enabled', False):
                gen = runtime.tracking.mjpeg()
            else:
                gen = cam.mjpeg_generator(runtime=runtime)
        else:
            gen = cam.mjpeg_generator(runtime=runtime)
        return Response(gen, mimetype='multipart/x-mixed-replace; boundary=frame')
