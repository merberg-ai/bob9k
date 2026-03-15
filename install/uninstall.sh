#!/usr/bin/env bash
set -euo pipefail
sudo systemctl disable --now bob9k.service || true
sudo rm -f /etc/systemd/system/bob9k.service
sudo systemctl daemon-reload
echo "bob9k service removed. Project files in ~/bob9k were left intact on purpose."
