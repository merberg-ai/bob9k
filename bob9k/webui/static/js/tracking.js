const trackingPage = () => document.body.dataset.page === 'tracking';
const $t = (id) => document.getElementById(id);
let trackingCurrentState = null;
let trackingCurrentConfig = null;
let trackingLastRefresh = 0;

function trackingConsoleEl() { return $t('console'); }

function trackingLog(msg) {
  const el = trackingConsoleEl();
  if (!el) return;
  const stamp = new Date().toLocaleTimeString();
  el.textContent = `[${stamp}] ${msg}
` + el.textContent;
}

async function trackingFetch(url, opts={}) {
  const r = await fetch(url, {headers: {'Content-Type':'application/json'}, ...opts});
  const data = await r.json();
  if (!r.ok) throw new Error(data?.error || `request failed: ${r.status}`);
  return data;
}

function trackingSetValue(id, value) {
  const el = $t(id);
  if (!el) return;
  el.value = value ?? '';
}

function trackingFillConfig(payload) {
  trackingCurrentConfig = payload.config || {};
  const cfg = payload.config || {};
  [
    'detector','target_label','yolo_model','yolo_imgsz','confidence_min','max_results','min_area',
    'min_target_area','pan_gain','tilt_gain','x_deadzone_px','y_deadzone_px','smoothing_alpha',
    'lost_timeout_s','scan_step','scan_tilt_step','process_every_n_frames','box_padding_px','preferred_target'
  ].forEach((k) => trackingSetValue(k, cfg[k]));
  trackingSetValue('enable_yolo', String(!!cfg.enable_yolo));
  trackingSetValue('yolo_classes', Array.isArray(cfg.yolo_classes) ? cfg.yolo_classes.join(',') : (cfg.yolo_classes || ''));
  ['scan_when_lost','show_labels','show_crosshair','show_metrics_overlay','invert_error_x','invert_error_y'].forEach((k) => trackingSetValue(k, String(!!cfg[k])));

  const servo = payload.servo || {};
  if (servo.pan) {
    $t('manual_pan').min = servo.pan.min ?? servo.pan.min_angle ?? 0;
    $t('manual_pan').max = servo.pan.max ?? servo.pan.max_angle ?? 180;
    $t('manual_pan').value = servo.pan.angle;
    $t('pan_trim').value = servo.pan.trim;
  }
  if (servo.tilt) {
    $t('manual_tilt').min = servo.tilt.min ?? servo.tilt.min_angle ?? 0;
    $t('manual_tilt').max = servo.tilt.max ?? servo.tilt.max_angle ?? 180;
    $t('manual_tilt').value = servo.tilt.angle;
    $t('tilt_trim').value = servo.tilt.trim;
  }
}

function trackingReadConfigForm() {
  const detector = $t('detector').value;
  const enable_yolo = detector === 'yolo' ? true : ($t('enable_yolo').value === 'true');
  return {
    detector,
    preferred_target: $t('preferred_target').value,
    target_label: $t('target_label').value.trim(),
    yolo_model: $t('yolo_model').value.trim() || 'yolov8n.pt',
    yolo_classes: $t('yolo_classes').value.trim().split(',').map(s => s.trim()).filter(Boolean),
    confidence_min: Number($t('confidence_min').value || 0.45),
    max_results: Number($t('max_results').value || 20),
    min_area: Number($t('min_area').value || 1500),
    min_target_area: Number($t('min_target_area').value || 900),
    pan_gain: Number($t('pan_gain').value || 0.06),
    tilt_gain: Number($t('tilt_gain').value || 0.06),
    x_deadzone_px: Number($t('x_deadzone_px').value || 48),
    y_deadzone_px: Number($t('y_deadzone_px').value || 36),
    smoothing_alpha: Number($t('smoothing_alpha').value || 0.4),
    lost_timeout_s: Number($t('lost_timeout_s').value || 1.5),
    scan_when_lost: $t('scan_when_lost').value === 'true',
    scan_step: Number($t('scan_step').value || 2),
    scan_tilt_step: Number($t('scan_tilt_step').value || 0),
    process_every_n_frames: Number($t('process_every_n_frames').value || 3),
    box_padding_px: Number($t('box_padding_px').value || 8),
    show_labels: $t('show_labels').value === 'true',
    show_crosshair: $t('show_crosshair').value === 'true',
    show_metrics_overlay: $t('show_metrics_overlay').value === 'true',
    invert_error_x: $t('invert_error_x').value === 'true',
    invert_error_y: $t('invert_error_y').value === 'true',
    enable_yolo,
    yolo_imgsz: Number($t('yolo_imgsz').value || 320),
    overlay_enabled: true,
  };
}

function trackingUpdateServoReadout(state) {
  $t('logical-pan-readout').textContent = String(state.pan_angle ?? '--');
  $t('logical-tilt-readout').textContent = String(state.tilt_angle ?? '--');
  $t('physical-pan-readout').textContent = String(state.pan_physical ?? '--');
  $t('physical-tilt-readout').textContent = String(state.tilt_physical ?? '--');
  $t('servo-stat').textContent = `P ${state.pan_angle ?? '--'} / T ${state.tilt_angle ?? '--'}`;
}

async function trackingRefresh() {
  const now = Date.now();
  if (now - trackingLastRefresh < 250) return;
  trackingLastRefresh = now;
  const resp = await trackingFetch('/api/tracking/state');
  const s = resp.state || {};
  trackingCurrentState = s;
  $t('status-pill-local').textContent = s.tracking_enabled ? (s.target_acquired ? 'Tracking' : (s.scan_active ? 'Scanning' : 'Armed')) : 'Idle';
  $t('detector-name').textContent = `detector: ${s.detector || '--'}`;
  $t('detect-count').textContent = `detections: ${s.last_detection_count ?? '--'}`;
  $t('fps-stat').textContent = `fps: ${s.metrics?.fps_actual ?? '--'}`;
  $t('toggle-tracking').textContent = s.tracking_enabled ? 'Disable Tracking' : 'Enable Tracking';
  const conf = (typeof s.target_confidence === 'number') ? s.target_confidence.toFixed(2) : '';
  $t('target-stat').textContent = s.target_acquired ? `${s.target_label || 'target'} ${conf}`.trim() : 'None';
  $t('detector-status').textContent = s.detector_status || '--';
  $t('scan-stat').textContent = s.scan_active ? 'active' : 'off';
  $t('servo-driver').textContent = `${s.servo_backend || '--'}${s.servo_ok ? '' : ' (mock)'}`;
  $t('servo-driver').title = s.servo_status || '';
  const detDetails = s.detector_details || {};
  const healthText = detDetails.reason ? `${detDetails.status || '--'} (${detDetails.reason})` : (detDetails.status || '--');
  if ($t('detector-health')) { $t('detector-health').textContent = healthText; $t('detector-health').title = healthText; }
  const yoloOpt = $t('detector').querySelector('option[value="yolo"]');
  if (yoloOpt) {
    yoloOpt.disabled = !s.yolo_available;
    yoloOpt.textContent = s.yolo_available ? 'YOLO Objects' : 'YOLO Objects (unavailable)';
    if (!s.yolo_available) yoloOpt.title = 'ultralytics not installed or unavailable';
  }
  trackingUpdateServoReadout(s);
  $t('detector-status').title = s.detector_status || '';
  if (document.activeElement !== $t('manual_pan')) $t('manual_pan').value = s.pan_angle ?? $t('manual_pan').value;
  if (document.activeElement !== $t('manual_tilt')) $t('manual_tilt').value = s.tilt_angle ?? $t('manual_tilt').value;
  if (s.last_error) trackingLog(`error: ${s.last_error}`);
}

async function trackingApplyServo() {
  const payload = {
    pan: Number($t('manual_pan').value),
    tilt: Number($t('manual_tilt').value),
    pan_trim: Number($t('pan_trim').value || 0),
    tilt_trim: Number($t('tilt_trim').value || 0),
  };
  const res = await trackingFetch('/api/tracking/servo/set', {method:'POST', body: JSON.stringify(payload)});
  trackingLog(`servo set pan=${res.servo.pan.angle} tilt=${res.servo.tilt.angle} trim=(${res.servo.pan.trim},${res.servo.tilt.trim})`);
  trackingUpdateServoReadout({
    pan_angle: res.servo.pan.angle,
    tilt_angle: res.servo.tilt.angle,
    pan_physical: res.servo.pan.physical_angle,
    tilt_physical: res.servo.tilt.physical_angle,
  });
}

async function trackingBoot() {
  const cfg = await trackingFetch('/api/tracking/config');
  trackingFillConfig(cfg);
  await trackingRefresh();
  setInterval(() => trackingRefresh().catch(err => trackingLog(`refresh failed: ${err.message || err}`)), 800);
}

document.addEventListener('DOMContentLoaded', () => {
  if (!trackingPage()) return;

  trackingBoot().catch(err => trackingLog(`boot failed: ${err.message || err}`));

  $t('toggle-tracking').addEventListener('click', async () => {
    try {
      if (trackingCurrentState?.tracking_enabled) {
        await trackingFetch('/api/tracking/disable', {method:'POST'});
        trackingLog('tracking disabled');
      } else {
        await trackingFetch('/api/tracking/enable', {method:'POST'});
        trackingLog('tracking enabled');
      }
      trackingRefresh();
    } catch (err) { trackingLog(`toggle failed: ${err.message || err}`); }
  });

  $t('save-config').addEventListener('click', async () => {
    try {
      const payload = {tracking: trackingReadConfigForm()};
      await trackingFetch('/api/tracking/config', {method:'POST', body: JSON.stringify(payload)});
      trackingLog(`config saved for detector=${payload.tracking.detector}`);
      if (window.setActionMessage) setActionMessage('Tracking config saved.', 'success');
      trackingRefresh();
    } catch (err) {
      trackingLog(`save failed: ${err.message || err}`);
      if (window.setActionMessage) setActionMessage('Failed to save tracking config.', 'error');
    }
  });

  $t('servo-home').addEventListener('click', async () => {
    try {
      const res = await trackingFetch('/api/tracking/servo/home', {method:'POST'});
      trackingLog(`servo homed pan=${res.servo.pan.angle} tilt=${res.servo.tilt.angle}`);
      trackingRefresh();
    } catch (err) { trackingLog(`home failed: ${err.message || err}`); }
  });

  $t('apply-servo').addEventListener('click', () => trackingApplyServo().catch(err => trackingLog(`servo apply failed: ${err.message || err}`)));
  $t('refresh-now').addEventListener('click', () => trackingRefresh().catch(err => trackingLog(`refresh failed: ${err.message || err}`)));
  $t('clear-console').addEventListener('click', () => { trackingConsoleEl().textContent = ''; });
  $t('copy-console').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(trackingConsoleEl().textContent);
      trackingLog('console copied to clipboard');
    } catch (err) { trackingLog(`copy failed: ${err.message || err}`); }
  });

  const copyDebugBtn = $t('copy-debug');
  if (copyDebugBtn) {
    copyDebugBtn.addEventListener('click', () => trackingCopyDebugSnapshot().catch(err => trackingLog(`copy debug failed: ${err.message || err}`)));
  }

  document.querySelectorAll('[data-nudge]').forEach(btn => btn.addEventListener('click', async () => {
    try {
      const res = await trackingFetch('/api/tracking/servo/nudge', {method:'POST', body: JSON.stringify({direction: btn.dataset.nudge})});
      trackingLog(`servo nudged ${btn.dataset.nudge} -> pan=${res.servo.pan.angle} tilt=${res.servo.tilt.angle}`);
      trackingRefresh();
    } catch (err) { trackingLog(`nudge failed: ${err.message || err}`); }
  }));

  $t('detector').addEventListener('change', () => {
    if ($t('detector').value === 'yolo') {
      trackingSetValue('enable_yolo', 'true');
      trackingLog('YOLO selected — Enable YOLO automatically set to Yes. Save Tracking Config to apply.');
    }
  });
});


async function trackingCopyDebugSnapshot() {
  const debug = await trackingFetch('/api/tracking/debug');
  const detectors = await trackingFetch('/api/tracking/detectors');
  const snapshot = {
    ts: new Date().toISOString(),
    state: trackingCurrentState,
    config: trackingCurrentConfig,
    debug,
    detectors: detectors.details || {},
  };
  const body = JSON.stringify(snapshot, null, 2);
  await navigator.clipboard.writeText(body);
  trackingLog('debug snapshot copied to clipboard');
}
