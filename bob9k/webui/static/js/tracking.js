let trackingConsoleLines = [];
const MAX_CONSOLE_LINES = 50;
let lastTrackingSnapshot = null;
let lastTargetAcquired = null;

function appendToTrackingConsole(msg) {
  const cons = document.getElementById('tracking-console');
  if (!cons) return;
  const now = new Date();
  const timeStr = now.toTimeString().split(' ')[0];
  const line = `[${timeStr}] ${msg}`;
  trackingConsoleLines.push(line);
  if (trackingConsoleLines.length > MAX_CONSOLE_LINES) trackingConsoleLines.shift();
  cons.innerHTML = trackingConsoleLines.map(l => `<div>${l}</div>`).join('');
  cons.scrollTop = cons.scrollHeight;
}

function setText(id, value){
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

async function loadDetectorStatus() {
  try {
    const data = await fetch('/api/tracking/detectors').then(r => r.json());
    if (!data.ok || !data.status) return;
    const active = data.status.active_detector;
    const detectors = data.status.detectors || {};
    const current = detectors[active] || {};
    setText('tracking-active-detector', active || '--');
    setText('tracking-detector-status', current.available ? 'READY' : 'UNAVAILABLE');
    setText('tracking-detector-reason', current.reason || 'ok');
    const yolo = data.status.yolo || {};
    setText('tracking-yolo-status', yolo.reason ? `Unavailable (${yolo.reason})` : 'Ready');
  } catch (err) {}
}

async function loadTrackingSettings(){
  const msg = document.getElementById('tracking-settings-message');
  try{
    const data = await window.bob9kApi.getTrackingConfig();
    if(data.ok && data.config) {
      document.getElementById('tracking-detector').value = data.config.detector || 'haar_face';
      document.getElementById('tracking-detect-only').value = data.config.detect_only_mode ? 'true' : 'false';
      document.getElementById('tracking-target-distance').value = data.config.target_distance_cm ?? 30;
      document.getElementById('tracking-dist-tolerance').value = data.config.distance_tolerance_cm ?? 5;
      document.getElementById('tracking-pan-gain').value = data.config.pan_gain ?? 0.05;
      document.getElementById('tracking-tilt-gain').value = data.config.tilt_gain ?? 0.05;
      document.getElementById('tracking-x-deadzone').value = data.config.x_deadzone_px ?? 64;
      document.getElementById('tracking-y-deadzone').value = data.config.y_deadzone_px ?? 48;
      document.getElementById('tracking-min-area').value = data.config.min_detection_area ?? 0.01;
      document.getElementById('tracking-edge-margin').value = data.config.edge_reject_margin_px ?? 12;
      document.getElementById('tracking-lost-timeout').value = data.config.lost_timeout_s ?? 2.0;
      document.getElementById('tracking-scan').value = data.config.scan_when_lost ? 'true' : 'false';
      document.getElementById('tracking-switch-margin').value = data.config.switch_margin ?? 0.15;
      document.getElementById('tracking-min-lock-frames').value = data.config.min_lock_frames ?? 3;
    }
    await loadDetectorStatus();
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
      detect_only_mode: document.getElementById('tracking-detect-only').value === 'true',
      target_label: detectorVal === 'haar_face' ? 'face' : detectorVal === 'haar_body' ? 'body' : 'motion',
      target_distance_cm: parseFloat(document.getElementById('tracking-target-distance').value),
      distance_tolerance_cm: parseFloat(document.getElementById('tracking-dist-tolerance').value),
      pan_gain: parseFloat(document.getElementById('tracking-pan-gain').value),
      tilt_gain: parseFloat(document.getElementById('tracking-tilt-gain').value),
      x_deadzone_px: parseInt(document.getElementById('tracking-x-deadzone').value),
      y_deadzone_px: parseInt(document.getElementById('tracking-y-deadzone').value),
      min_detection_area: parseFloat(document.getElementById('tracking-min-area').value),
      edge_reject_margin_px: parseInt(document.getElementById('tracking-edge-margin').value),
      lost_timeout_s: parseFloat(document.getElementById('tracking-lost-timeout').value),
      scan_when_lost: document.getElementById('tracking-scan').value === 'true',
      switch_margin: parseFloat(document.getElementById('tracking-switch-margin').value),
      min_lock_frames: parseInt(document.getElementById('tracking-min-lock-frames').value)
    };
    const data = await window.bob9kApi.saveTrackingConfig(payload);
    if(data.ok && data.config) {
      if(msg) msg.textContent = 'Tracking settings saved.';
      setActionMessage('Tracking settings saved.', 'success');
      appendToTrackingConsole('Settings updated and saved.');
      await loadDetectorStatus();
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
    appendToTrackingConsole(data.enabled ? 'Tracking system ENABLED manually.' : 'Tracking system DISABLED manually.');
    trackingPoll();
  } catch(e) {}
}

async function copyTrackingDebug() {
  try {
    const d = await fetch('/api/tracking/debug').then(r => r.json());
    await navigator.clipboard.writeText(JSON.stringify(d, null, 2));
    appendToTrackingConsole('Copied tracking debug snapshot to clipboard.');
    setActionMessage('Tracking debug copied.', 'success');
  } catch (err) {
    setActionMessage('Failed to copy tracking debug.', 'error');
  }
}

function updateBadge(id, text, active) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.style.color = active ? 'var(--accent)' : 'var(--muted)';
  el.style.borderColor = active ? 'rgba(0,255,204,0.35)' : 'rgba(255,255,255,0.12)';
}

async function trackingPoll() {
  if (document.body.dataset.page !== 'tracking') return;
  try {
    const d = await fetch('/api/tracking/debug').then(r => r.json());
    lastTrackingSnapshot = d;
    const trBadge = document.getElementById('tracking-status-badge');
    const trBtn = document.getElementById('btn-toggle-tracking');
    const summary = document.getElementById('tracking-state-summary');

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

    updateBadge('tracking-lock-badge', d.target_locked ? 'LOCKED' : 'UNLOCKED', !!d.target_locked);
    updateBadge('tracking-detectonly-badge', d.detect_only_mode ? 'DETECT ONLY' : 'LIVE SERVO', !d.detect_only_mode);

    if (summary) {
      const pieces = [];
      pieces.push(`Detector: ${d.detector || '--'}`);
      if (d.target_label) pieces.push(`Target: ${d.target_label}`);
      if (d.target_confidence != null) pieces.push(`Conf: ${Number(d.target_confidence).toFixed(2)}`);
      if (d.disable_reason) pieces.push(`Reason: ${d.disable_reason}`);
      summary.textContent = pieces.join(' • ') || 'Waiting for tracking state…';
    }

    if (d.enabled) {
      if (d.target_acquired && lastTargetAcquired !== true) {
        const pan = d.pan_angle != null ? Number(d.pan_angle).toFixed(1) : '?';
        const tilt = d.tilt_angle != null ? Number(d.tilt_angle).toFixed(1) : '?';
        appendToTrackingConsole(`Target acquired! Pos: pan=${pan}° tilt=${tilt}°`);
        lastTargetAcquired = true;
      } else if (!d.target_acquired && lastTargetAcquired !== false) {
        appendToTrackingConsole('Searching for target...');
        lastTargetAcquired = false;
      }
    }

    setText('tracking-debug-target', d.target_label || '--');
    setText('tracking-debug-confidence', d.target_confidence != null ? Number(d.target_confidence).toFixed(2) : '--');
    setText('tracking-debug-area', d.target_area_ratio != null ? Number(d.target_area_ratio).toFixed(4) : '--');
    setText('tracking-debug-error', `${Number(d.error_x || 0).toFixed(1)} / ${Number(d.error_y || 0).toFixed(1)}`);
    setText('tracking-debug-lockframes', d.target_lock_frames != null ? String(d.target_lock_frames) : '--');
    setText('tracking-debug-switchreason', d.target_switch_reason || '--');
    setText('tracking-debug-lostage', d.target_lost_age_s != null ? `${Number(d.target_lost_age_s).toFixed(2)}s` : '--');
    const dbg = d.debug || {};
    setText('tracking-debug-candidates', `${dbg.filtered_candidate_count ?? '--'} / raw ${dbg.raw_candidate_count ?? '--'}`);

    const detectorStatus = d.detector_status || {};
    const active = (detectorStatus.detectors || {})[d.detector || ''] || {};
    setText('tracking-active-detector', d.detector || '--');
    setText('tracking-detector-status', active.available ? 'READY' : 'UNAVAILABLE');
    setText('tracking-detector-reason', active.reason || 'ok');

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
  const copyBtn = document.getElementById('btn-copy-tracking-debug');
  if(copyBtn) copyBtn.addEventListener('click', copyTrackingDebug);
});
