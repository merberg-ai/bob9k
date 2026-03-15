from __future__ import annotations
from flask import Flask, current_app, request
from bob9k.services.bluetooth_manager import BluetoothManager
from bob9k.config import load_runtime_config, save_runtime_config

def register_bluetooth_routes(app: Flask) -> None:
    @app.post('/api/bluetooth/cmd')
    def bluetooth_command():
        runtime = current_app.config['BOB9K_RUNTIME']
        payload = request.get_json(force=True, silent=True) or {}
        cmd = payload.get('cmd', '')
        mac = payload.get('mac', '')
        
        bt = BluetoothManager.get_instance(runtime.logger)
        
        if cmd == 'scan_on':
            bt.start_scan()
        elif cmd == 'scan_off':
            bt.stop_scan()
        elif cmd == 'pair':
            bt.pair_device(mac)
        elif cmd == 'connect':
            bt.connect_device(mac)
        elif cmd == 'disconnect':
            bt.disconnect_device(mac)
        elif cmd == 'remove':
            bt.remove_device(mac)
        elif cmd == 'raw':
            raw_cmd = payload.get('raw_cmd', '')
            if raw_cmd:
                bt.send_command(raw_cmd)
        else:
            return {'ok': False, 'error': 'Unknown command'}, 400
            
        return {'ok': True, 'cmd': cmd}

    @app.get('/api/bluetooth/logs')
    def bluetooth_logs():
        runtime = current_app.config['BOB9K_RUNTIME']
        bt = BluetoothManager.get_instance(runtime.logger)
        return {
            'ok': True, 
            'is_scanning': bt.is_scanning,
            'logs': bt.get_logs()
        }



    @app.get('/api/gamepad/debug')
    def get_gamepad_debug():
        runtime = current_app.config['BOB9K_RUNTIME']
        if getattr(runtime, 'gamepad', None):
            return runtime.gamepad.get_debug_snapshot()
        return {'ok': False, 'error': 'Gamepad service not running'}

    @app.get('/api/bluetooth/mapping')
    def get_gamepad_mapping():
        runtime = current_app.config['BOB9K_RUNTIME']
        if getattr(runtime, 'gamepad', None):
             return {'ok': True, 'mapping': runtime.gamepad.mapping}
        return {'ok': False, 'error': 'Gamepad service not running'}

    @app.post('/api/bluetooth/mapping')
    def save_gamepad_mapping():
        runtime = current_app.config['BOB9K_RUNTIME']
        payload = request.get_json(force=True, silent=True) or {}
        new_map = payload.get('mapping', {})
        if not new_map:
            return {'ok': False, 'error': 'No mapping provided'}
        
        # update live
        if getattr(runtime, 'gamepad', None):
            runtime.gamepad.mapping = new_map
            
        # save persistent
        cfg = load_runtime_config()
        cfg['gamepad_mapping'] = new_map
        save_runtime_config(cfg)
        
        # runtime config memory
        runtime.config['gamepad_mapping'] = new_map
        
        return {'ok': True}
