<div align="center">
  <img src="https://img.icons8.com/color/96/000000/robot-3.png" alt="bob9k logo" width="100"/>
  <h1>bob9k 🤖 (v1.1 Stable)</h1>
  <p><em>Mobile-first robot control scaffold for the Adeept PiCar platform.</em> 🚗💨</p>

  [![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey.svg)](https://flask.palletsprojects.com/)
  [![Hardware](https://img.shields.io/badge/Hardware-Adeept_PiCar-orange.svg)](https://www.adeept.com/)
  [![Status](https://img.shields.io/badge/Status-Stable-brightgreen.svg)]()
</div>

<br />

`bob9k` is a modern, lightweight, and extensible web interface and API for controlling the **Adeept PiCar**, providing a robust foundation for your Raspberry Pi robotics projects. 

Version 1.1 brings drastically improved controller support, custom RGB headlight tuning, and silky-smooth cinematic camera controls. 🚀

## ✨ Features
- 🚀 **Safe Boot-time Initialization**: Orderly startup of I2C and GPIO resources to avoid conflicts.
- 🔒 **Single-Process IO Ownership**: Prevents resource conflicts and hardware glitches.
- 🚦 **RGB Eye Status Control**: Visual system status feedback with an interactive **Custom Color Picker** UI.
- 📱 **Mobile-Friendly Web UI**: Responsive dark flat-glassmorphic interface designed natively for smartphones and tablets.
- 🎮 **Robust Gamepad Support**: Deep integration with Xbox/Bluetooth controllers featuring:
  - Dynamic right-stick camera mappings with **Cinematic Smoothing**.
  - Interactive Web UI to test inputs and natively remap any axis/button on the fly.
  - Quick-toggle cycle for Headlight states (Off -> Green -> Red -> Blue -> White -> Police -> Custom).
- 🕹️ **API First Design**: Complete RESTful interface for external control and scripting.

## 🛠️ Hardware Requirements
- **Raspberry Pi** (3 / 4 / Zero 2 W recommended)
- **Adeept PiCar Kit** or compatible components:
  - Motor Driver (PCA9685/TB6612)
  - Servos for steering and camera
  - WS2812 RGB LED strip ("eyes")

## 🚀 Installation

`bob9k` comes with a comprehensive installation script that sets up the Python environment, installs dependencies, and configures it to seamlessly run as a `systemd` service.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/bob9k.git
   cd bob9k
   ```

2. **Run the install script:**
   ```bash
   cd install
   sudo ./install.sh
   ```

The script will handle:
- Checking for conflicting Adeept/PiCar services.
- Installing required `apt` dependencies (`python3-gpiozero`, `i2c-tools`, etc.).
- Creating a dedicated Python virtual environment.
- Registering `bob9k.service` with `systemd`.

## 🎮 Usage

Once installed and running, you can access the responsive web interface via any browser on your network.

```text
http://<raspberry-pi-ip>:5000/
```

### ⚙️ Managing the Service
If installed via `install.sh`, it runs transparently as a background service:

```bash
# Check the service status
sudo systemctl status bob9k --no-pager -l

# Start / Restart the service
sudo systemctl restart bob9k

# Stop the service
sudo systemctl stop bob9k

# Watch live application logs
journalctl -u bob9k -f
```

## 📂 Project Structure
- `app.py`: The Flask application entry point.
- `bob9k/`: Core Python package directory.
  - `api/`: REST API route definitions (`lights`, `motion`, `settings`, etc.).
  - `services/`: Hardware control, telemetry, safety handlers, and gamepad logic.
  - `webui/`: HTML templates and static assets for the frontend.
- `config/`: Configuration files (e.g., `config.yaml`, `runtime.yaml`).
- `install/`: Installation, checking, and uninstallation scripts for system deployment.

## 🔧 Configuration
The main configuration is located at `config/config.yaml`. It seamlessly manages pin assignments, API settings, and hardware limits. Overrides and persistent state are automatically saved to `config/runtime.yaml`.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

---
<div align="center">
  <i>Built with ❤️ for Raspberry Pi robotics.</i>
</div>
