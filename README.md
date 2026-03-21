<div align="center">
  <img src="https://img.icons8.com/color/96/000000/robot-3.png" alt="bob9k logo" width="100"/>
  <h1>bob9k 🤖 (v1.6-beta)</h1>
  <p><em>Modular Raspberry Pi robot control system for the Adeept PiCar platform.</em> 🚗💨</p>

  [![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey.svg)](https://flask.palletsprojects.com/)
  [![Hardware](https://img.shields.io/badge/Hardware-Adeept_PiCar-orange.svg)](https://www.adeept.com/)
  [![Status](https://img.shields.io/badge/Status-Beta-yellow.svg)]()
</div>

<br />

`bob9k` is a structured, extensible robot runtime for the **Adeept PiCar** platform. It combines real-time hardware control, computer vision object tracking, a live camera stream, gamepad support, and a polished browser-based UI into a single cohesive system.

## ✨ Features

### 🤖 Motion & Safety
- Forward / reverse / stop with configurable speed
- Steering center / left / right / direct angle set
- Motor watchdog timeout (auto-stop if connection goes silent)
- Emergency stop latch (`estop`) with motion lock
- Battery voltage monitoring with low/critical warnings
- **Safe-boot follow mode** — `object_follow` mode is always disabled on startup to prevent autonomous driving on reboot

### 🎥 Camera & Vision
- **Live MJPEG streaming** via `picamera2` with tunable exposure, contrast, saturation, and AWB
- **Pan/tilt camera servo** with software trim, configurable limits, and home position
- **Computer Vision Tracking** with multiple detector backends:
  - Haar Cascade face & body detection (built-in, zero extra dependencies)
  - Motion detection tracking
  - YOLO object detection (optional; requires `ultralytics`)
- Two tracking modes:
  - **`camera_track`** — Servo-only; camera follows target using proportional pan/tilt control
  - **`object_follow`** — Full autonomous follow; steers and drives motors to maintain distance from target (with optional ultrasonic obstacle guard)
- Scan-when-lost behaviour: camera sweeps to re-acquire a lost target
- Configurable detection filters, deadzone, smoothing, and scan speed

### 🎮 Gamepad / Controller
- USB and Bluetooth gamepad support via the browser Gamepad API
- Interactive **input remapping** for every axis and button
- Cinematic right-stick camera smoothing
- Quick-cycle headlight states (Off → Green → Red → Blue → White → Police → Custom)
- Live controller debug view

### 💡 RGB Lighting
- WS2812 RGB "eye" LEDs with system-status-aware behaviour (booting, ready, error, battery critical, police flash)
- Interactive **custom colour picker** in the web UI

### 📊 Telemetry
- Live battery voltage / percentage / status
- Ultrasonic distance reading
- Motor and steering state
- Pan / tilt / tracking state
- Controller connected status

### 🌐 Web UI Tabs
| Tab | Description |
|-----|-------------|
| **Dashboard** | Live telemetry overview |
| **Remote** | Full-HUD camera + drive controls (mobile-optimised) |
| **Control** | Drive buttons and camera controls |
| **Tracking** | Vision detector selection, mode toggle, all tuning parameters |
| **Controller** | Gamepad input test and remapping |
| **Lights** | RGB eye control and colour picker |
| **Settings** | API and hardware settings |
| **System** | App version, git info, system diagnostics |

### 🕹️ API First Design
- Complete RESTful API for all subsystems (`/api/motion`, `/api/tracking`, `/api/lights`, etc.)
- All settings tunable at runtime with persistent overrides via `runtime.yaml`

---

## 🛠️ Hardware Requirements
- **Raspberry Pi** (3 / 4 / Zero 2 W recommended)
- **Adeept PiCar Kit** or compatible:
  - Motor driver (PCA9685 / TB6612)
  - Steering and camera pan/tilt servos
  - WS2812 RGB LED strip ("eyes")
  - HC-SR04 ultrasonic sensor (optional; used for `object_follow` obstacle guard)

---

## 🚀 Installation

`bob9k` ships with a comprehensive install script that sets up the Python environment, installs all dependencies, and registers it as a `systemd` service.

**1. Clone the repository:**
```bash
git clone https://github.com/yourusername/bob9k.git
cd bob9k
```

**2. Run the install script:**
```bash
cd install
sudo ./install.sh
```

The script will:
- Check for conflicting Adeept / PiCar services and warn if any are found
- Install required `apt` packages (`python3-gpiozero`, `i2c-tools`, `python3-venv`, `libcamera` tools, etc.)
- Create a dedicated Python virtual environment and install all `requirements.txt` packages
- Register and enable `bob9k.service` with `systemd`

> **Optional — YOLO detection:** To use the YOLO detector backend, install ultralytics in the venv after installation:
> ```bash
> /opt/bob9k/venv/bin/pip install ultralytics
> ```

---

## 🎮 Usage

Once running, open the web interface from any device on your network:

```
http://<raspberry-pi-ip>:8080/
```

### ⚙️ Managing the Service

```bash
# Check status
sudo systemctl status bob9k --no-pager -l

# Start / Restart
sudo systemctl restart bob9k

# Stop
sudo systemctl stop bob9k

# Watch live logs
journalctl -u bob9k -f
```

### 🔄 Reloading Without a Full Restart
```bash
./reload.sh
```

---

## 📂 Project Structure

```
bob9k/
├── app.py                  # Entry point
├── bob9k/
│   ├── api/                # REST API route handlers (motion, tracking, lights, …)
│   ├── hardware/           # Low-level hardware drivers (motors, servos, camera, …)
│   ├── services/           # Application services (tracking, gamepad, telemetry, …)
│   ├── vision/             # Vision detectors and tracker logic
│   ├── webui/              # Flask templates + static JS/CSS
│   ├── config.py           # Config loading and merging
│   └── state.py            # Shared runtime state dataclass
├── config/
│   ├── default.yaml        # Base configuration (checked in)
│   └── runtime.yaml        # User overrides / persistent state (gitignored)
└── install/                # Install, uninstall, and conflict-check scripts
```

---

## 🔧 Configuration

All hardware pin assignments, limits, and feature defaults live in `config/default.yaml`. User overrides and persistent UI settings are automatically saved to `config/runtime.yaml` (not committed to git).

To reset all settings to factory defaults:
```bash
rm config/runtime.yaml
sudo systemctl restart bob9k
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome. Feel free to open an issue or pull request.

---
<div align="center">
  <i>Built with ❤️ for Raspberry Pi robotics.</i>
</div>
