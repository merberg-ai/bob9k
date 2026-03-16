let trackingConsoleLines = [];
const MAX_CONSOLE_LINES = 50;

function appendToTrackingConsole(msg) {
  const cons = document.getElementById('tracking-console');
  if (!cons) return;
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];
  const line = `[${timeStr}] ${msg}`;
  trackingConsoleLines.push(line);
  if (trackingConsoleLines.length > MAX_CONSOLE_LINES) {
    trackingConsoleLines.shift();
  }
  cons.innerHTML = trackingConsoleLines.map(l => `<div>${l}</div>`).join('');
  cons.scrollTop = cons.scrollHeight;
}

async function loadTrackingSettings(){
  const msg = document.getElementById('tracking-settings-message');
  try{
    const data = await window.bob9kApi.getTrackingConfig();
    if(data.ok && data.config) {
        document.getElementById('tracking-detector').value = data.config.detector || 'haar_face';
        document.getElementById('tracking-target-distance').value = data.config.target_distance_cm ?? 30;
        document.getElementById('tracking-dist-tolerance').value = data.config.distance_tolerance_cm ?? 5;
        document.getElementById('tracking-pan-gain').value = data.config.pan_gain ?? 0.05;
        document.getElementById('tracking-tilt-gain').value = data.config.tilt_gain ?? 0.05;
        document.getElementById('tracking-x-deadzone').value = data.config.x_deadzone_px ?? 64;
        document.getElementById('tracking-y-deadzone').value = data.config.y_deadzone_px ?? 48;
        document.getElementById('tracking-lost-timeout').value = data.config.lost_timeout_s ?? 2.0;
        document.getElementById('tracking-scan').value = data.config.scan_when_lost ? 'true' : 'false';
    }
  }catch(err){
    if(msg) msg.textContent = 'Failed to load tracking settings.';
  }
}

async function saveTrackingSettings(){
  const msg = document.getElementById('tracking-settings-message');
  try{
    if(msg) msg.textContent = 'Saving tracking settings…';
    setActionMessage('Saving tracking settings…', 'info');
    const detectorVal = document.getElementById('tracking-detector').value;
    const payload = {
      detector: detectorVal,
      target_label: detectorVal === 'haar_face' ? 'face' : 'body',
      target_distance_cm: parseFloat(document.getElementById('tracking-target-distance').value),
      distance_tolerance_cm: parseFloat(document.getElementById('tracking-dist-tolerance').value),
      pan_gain: parseFloat(document.getElementById('tracking-pan-gain').value),
      tilt_gain: parseFloat(document.getElementById('tracking-tilt-gain').value),
      x_deadzone_px: parseInt(document.getElementById('tracking-x-deadzone').value),
      y_deadzone_px: parseInt(document.getElementById('tracking-y-deadzone').value),
      lost_timeout_s: parseFloat(document.getElementById('tracking-lost-timeout').value),
      scan_when_lost: document.getElementById('tracking-scan').value === 'true'
    };
    const data = await window.bob9kApi.saveTrackingConfig(payload);
    if(data.ok && data.config) {
        if(msg) msg.textContent = 'Tracking settings saved.';
        setActionMessage('Tracking settings saved.', 'success');
        appendToTrackingConsole('Settings updated and saved.');
    } else {
        if(msg) msg.textContent = 'Failed to save tracking settings.';
        setActionMessage('Failed to save tracking settings.', 'error');
    }
  }catch(err){
    if(msg) msg.textContent = 'Failed to save tracking settings.';
    setActionMessage('Failed to save tracking settings.', 'error');
  }
}

async function toggleTracking() {
  try {
    const data = await fetch('/api/tracking/toggle', {method: 'POST'}).then(r => r.json());
    if (data.enabled) {
      appendToTrackingConsole('Tracking system ENABLED manually.');
    } else {
      appendToTrackingConsole('Tracking system DISABLED manually.');
    }
    trackingPoll();
  } catch(e) {}
}

let lastTargetAcquired = null;
async function trackingPoll() {
  if (document.body.dataset.page !== 'tracking') return;
  try {
    const d = await fetch('/api/tracking/debug').then(r => r.json());
    
    const trBadge = document.getElementById('tracking-status-badge');
    const trBtn = document.getElementById('btn-toggle-tracking');
    
    if (d.enabled) {
      trBadge.textContent = 'ENABLED';
      trBadge.style.color = 'var(--accent)';
      trBadge.style.borderColor = 'rgba(0,255,204,0.4)';
      trBtn.textContent = 'Disable Tracking';
      trBtn.style.color = '#ff3366';
      trBtn.style.borderColor = 'rgba(255,51,102,0.4)';
    } else {
      trBadge.textContent = 'DISABLED';
      trBadge.style.color = 'var(--muted)';
      trBadge.style.borderColor = 'rgba(255,255,255,0.12)';
      trBtn.textContent = 'Enable Tracking';
      trBtn.style.color = 'var(--text)';
      trBtn.style.borderColor = 'var(--border)';
      
      if (d.disable_reason && d.disable_reason !== 'mode_off' && lastTargetAcquired !== false) {
          appendToTrackingConsole(`Disabled reason: ${d.disable_reason}`);
          lastTargetAcquired = false;
      }
    }

    if (d.enabled) {
        if (d.target_acquired && lastTargetAcquired !== true) {
            appendToTrackingConsole(`Target acquired! Err: (${d.pan_angle.toFixed(1)}, ${d.tilt_angle.toFixed(1)}) tracking...`);
            lastTargetAcquired = true;
        } else if (!d.target_acquired && lastTargetAcquired !== false) {
            appendToTrackingConsole('Searching for target...');
            lastTargetAcquired = false;
        }
    }

  } catch(e) {}
  setTimeout(trackingPoll, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
  if(document.body.dataset.page !== 'tracking') return;
  
  loadTrackingSettings();
  trackingPoll();
  
  const saveBtn = document.getElementById('save-tracking-settings');
  if(saveBtn) saveBtn.addEventListener('click', saveTrackingSettings);
  
  const toggleBtn = document.getElementById('btn-toggle-tracking');
  if(toggleBtn) toggleBtn.addEventListener('click', toggleTracking);
});
