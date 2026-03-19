bob9k — Project Overview and v1.6beta Plan
==========================================

Overview
--------

bob9k is a modular Raspberry Pi robot control system for a PiCar-style rover platform.
It combines:

- real-time hardware control
- camera pan/tilt and live streaming
- controller support
- browser-based control pages
- vision-based target tracking
- telemetry and safety lockouts
- persistent config storage

This codebase has already moved beyond a simple remote-control toy app. It is a structured
robot runtime with hardware, services, API routes, and web UI layers.

Current Major Capabilities
--------------------------

1. Motion and steering
- forward / reverse / stop
- steering center / left / right / direct set
- configurable speed
- motor watchdog timeout
- emergency stop latch
- battery-based motion lock

2. Camera system
- live MJPEG feed
- pan / tilt control
- camera home position
- runtime camera tuning

3. Tracking
- Haar face tracking
- Haar body tracking
- motion detection tracking
- proportional pan/tilt target following
- target-lost grace period
- runtime tracking config

4. Controller support
- USB / Bluetooth gamepad support
- remapping and debug tools
- analog input handling

5. Telemetry
- battery voltage / percentage / status
- ultrasonic distance
- motor state
- pan / tilt / steering angle
- tracking state
- controller connected status

6. Lighting
- RGB status lighting / eyes
- status-aware lighting behavior

7. Web UI
- dashboard
- control
- tracking
- controller pages
- settings
- system page
- remote / HUD page

Architecture Summary
--------------------

Top-level layers:

- app.py
- bob9k/hardware/
- bob9k/services/
- bob9k/vision/
- bob9k/api/
- bob9k/webui/
- config/

Important runtime idea:

The app maintains a shared runtime context and runtime state so UI, services, and hardware
layers all work from the same live state.

v1.6beta Direction
------------------

This version is focused on tightening and stabilizing the project before adding bigger AI
features.

Main priorities:

1. tracking reliability
2. safe follow behavior
3. obstacle protection using ultrasonic
4. controller and UI polish
5. diagnostics and better observability

Planned Development Passes
--------------------------

Pass 1 — Tracking / Detection Stabilization
- better detector status visibility
- cleaner detection filtering
- target lock hysteresis
- lost-target grace handling
- detect-only mode
- improved tracking debug info

Pass 2 — Follow Mode Core
- new follow service
- convert target tracking into steering + forward motion
- safe forward-only follow logic initially
- expose follow state via API and UI

Pass 2.5 — Ultrasonic Obstacle Guard
- obstacle slowdown and stop behavior
- safer follow operation
- obstacle state in telemetry / UI
- no full pathfinding yet, just obstacle guard and cautious behavior

Pass 3 — Controller / UI Polish
- controller deadzones / smoothing / invert options
- better controller debug visibility
- cleaner tracking page
- better remote / phone usability
- better compact telemetry banner

Pass 4 — Diagnostics / Docs
- diagnostics API and page
- clearer service / detector / hardware status
- updated docs matching actual project state

What Was Patched In This Pass
-----------------------------

This patch set is the first practical chunk of Pass 1A.

Implemented:

- tracking config expanded with new stability fields
- ultralytics added to requirements for future YOLO work
- runtime state expanded with richer tracking fields
- detector health reporting added
- Haar face/body detector status helpers added
- motion detector warmup and filtering improved
- target lock hysteresis added in vision tracker
- target switch reasons and lock frames exposed
- detect-only mode added
- better detection filtering added in tracking service
- servo update rate limiting added
- richer tracking debug payload added
- new /api/tracking/detectors endpoint added
- tracking page updated with detector health and debug info
- copy-debug button added to tracking UI

What Is Not Fully Done Yet
--------------------------

Still pending from the master plan:

- actual YOLO detector backend integration in this code tree
- follow service
- ultrasonic obstacle guard integration into follow mode
- controller tuning UI improvements
- diagnostics page
- full README refresh in project markdown

Design Philosophy
-----------------

- Safety first
- Observe everything important
- Make features tunable from the browser
- Separate tracking from follow behavior
- Add autonomy gradually and conservatively

Final Goal for v1.6beta
-----------------------

When this phase is complete, bob9k should:

- detect and track targets more reliably
- hold target lock without constant jitter
- support detect-only testing
- follow a person safely
- slow down or stop for obstacles using ultrasonic
- present clearer state and diagnostics in the UI
- feel like a real robot system instead of a loose prototype

Working Label
-------------

bob9k v1.6beta — Eyes, Wheels, and Less Nonsense
