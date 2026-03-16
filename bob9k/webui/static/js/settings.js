async function loadServoTrimSettings(){
  if(document.body.dataset.page!=='settings') return;
  const msg = document.getElementById('settings-message');
  try{
    const data = await window.bob9kApi.getServoTrim();
    document.getElementById('trim-steering').value = data.steering_trim ?? 0;
    document.getElementById('trim-pan').value = data.camera_pan_trim ?? 0;
    document.getElementById('trim-tilt').value = data.camera_tilt_trim ?? 0;
    if(msg) msg.textContent = 'Servo trim loaded.';
  }catch(err){
    if(msg) msg.textContent = 'Failed to load trim settings.';
  }
}

async function saveServoTrimSettings(){
  const msg = document.getElementById('settings-message');
  try{
    const payload = {
      steering_trim: parseInt(document.getElementById('trim-steering').value || '0', 10),
      camera_pan_trim: parseInt(document.getElementById('trim-pan').value || '0', 10),
      camera_tilt_trim: parseInt(document.getElementById('trim-tilt').value || '0', 10),
    };
    const data = await window.bob9kApi.saveServoTrim(payload);
    document.getElementById('trim-steering').value = data.steering_trim ?? 0;
    document.getElementById('trim-pan').value = data.camera_pan_trim ?? 0;
    document.getElementById('trim-tilt').value = data.camera_tilt_trim ?? 0;
    if(msg) msg.textContent = 'Servo trim saved.';
    setActionMessage('Servo trim saved.', 'success');
  }catch(err){
    if(msg) msg.textContent = 'Failed to save trim settings.';
    setActionMessage('Failed to save trim settings.', 'error');
  }
}

function adjustTrimInput(id, delta){
  const el = document.getElementById(id);
  if(!el) return;
  const next = Math.max(-20, Math.min(20, parseInt(el.value || '0', 10) + delta));
  el.value = next;
}

function syncCameraSlider(id, digits=2){
  const input = document.getElementById(id);
  const label = document.getElementById(`${id}-label`);
  if(!input || !label) return;
  const value = Number(input.value || 0);
  label.textContent = digits === 0 ? String(Math.round(value)) : value.toFixed(digits);
}

function setCameraManualGainVisibility(){
  const awb = document.getElementById('camera-awb-mode');
  const red = document.getElementById('camera-manual-red-gain');
  const blue = document.getElementById('camera-manual-blue-gain');
  if(!awb || !red || !blue) return;
  const enabled = awb.value === 'custom';
  red.disabled = !enabled;
  blue.disabled = !enabled;
}

function refreshSettingsCameraPreview(){
  const img = document.getElementById('settings-camera-preview');
  if(!img) return;
  img.src = `/video_feed?view=settings&_ts=${Date.now()}`;
}

function cameraPayloadFromForm(){
  const manualRedValue = document.getElementById('camera-manual-red-gain').value;
  const manualBlueValue = document.getElementById('camera-manual-blue-gain').value;
  return {
    awb_mode: document.getElementById('camera-awb-mode').value,
    fps: parseInt(document.getElementById('camera-fps').value || '20', 10),
    brightness: parseFloat(document.getElementById('camera-brightness').value || '0'),
    contrast: parseFloat(document.getElementById('camera-contrast').value || '1'),
    saturation: parseFloat(document.getElementById('camera-saturation').value || '1'),
    sharpness: parseFloat(document.getElementById('camera-sharpness').value || '1'),
    exposure_compensation: parseFloat(document.getElementById('camera-exposure-compensation').value || '0'),
    manual_red_gain: manualRedValue === '' ? null : parseFloat(manualRedValue),
    manual_blue_gain: manualBlueValue === '' ? null : parseFloat(manualBlueValue),
  };
}

function applyCameraSettingsToForm(settings){
  document.getElementById('camera-awb-mode').value = settings.awb_mode ?? 'auto';
  document.getElementById('camera-fps').value = settings.fps ?? 20;
  document.getElementById('camera-brightness').value = settings.brightness ?? 0;
  document.getElementById('camera-contrast').value = settings.contrast ?? 1;
  document.getElementById('camera-saturation').value = settings.saturation ?? 1;
  document.getElementById('camera-sharpness').value = settings.sharpness ?? 1;
  document.getElementById('camera-exposure-compensation').value = settings.exposure_compensation ?? 0;
  document.getElementById('camera-manual-red-gain').value = settings.manual_red_gain ?? '';
  document.getElementById('camera-manual-blue-gain').value = settings.manual_blue_gain ?? '';
  ['camera-fps','camera-brightness','camera-contrast','camera-saturation','camera-sharpness','camera-exposure-compensation'].forEach(id=> syncCameraSlider(id, id === 'camera-fps' ? 0 : 2));
  setCameraManualGainVisibility();
}

async function loadCameraSettings(){
  if(document.body.dataset.page!=='settings') return;
  const msg = document.getElementById('camera-settings-message');
  try{
    const data = await window.bob9kApi.getCameraSettings();
    applyCameraSettingsToForm(data.settings || {});
    refreshSettingsCameraPreview();
    if(msg) msg.textContent = data.camera_running ? 'Camera settings loaded. Live camera is running.' : 'Camera settings loaded. Camera is currently offline.';
  }catch(err){
    if(msg) msg.textContent = 'Failed to load camera settings.';
  }
}

async function saveCameraSettings(){
  const msg = document.getElementById('camera-settings-message');
  try{
    if(msg) msg.textContent = 'Saving camera settings and restarting camera…';
    setActionMessage('Saving camera settings and restarting camera…', 'info');
    const data = await window.bob9kApi.saveCameraSettings(cameraPayloadFromForm());
    applyCameraSettingsToForm(data.settings || {});
    refreshSettingsCameraPreview();
    const warnings = Array.isArray(data.warnings) && data.warnings.length ? ` ${data.warnings.join(' ')}` : '';
    if(msg) msg.textContent = data.camera_running ? `Camera settings saved and camera restarted.${warnings}` : `Camera settings saved, but camera is offline after restart.${warnings}`;
  }catch(err){
    if(msg) msg.textContent = 'Failed to save camera settings.';
    setActionMessage('Failed to save camera settings.', 'error');
  }
}

async function resetCameraSettings(){
  const msg = document.getElementById('camera-settings-message');
  try{
    if(msg) msg.textContent = 'Resetting camera settings to defaults and restarting camera…';
    setActionMessage('Resetting camera settings to defaults and restarting camera…', 'info');
    const data = await window.bob9kApi.resetCameraSettings();
    applyCameraSettingsToForm(data.settings || {});
    refreshSettingsCameraPreview();
    const warnings = Array.isArray(data.warnings) && data.warnings.length ? ` ${data.warnings.join(' ')}` : '';
    if(msg) msg.textContent = data.camera_running ? `Camera defaults restored and camera restarted.${warnings}` : `Camera defaults restored, but camera is offline after restart.${warnings}`;
  }catch(err){
    if(msg) msg.textContent = 'Failed to reset camera settings.';
    setActionMessage('Failed to reset camera settings.', 'error');
  }
}

async function loadTrackingSettings(){
  if(document.body.dataset.page!=='settings') return;
  const msg = document.getElementById('tracking-settings-message');
  try{
    const data = await window.bob9kApi.getTrackingConfig();
    if(data.ok && data.config) {
        document.getElementById('tracking-detector').value = data.config.detector || 'haar_face';
    }
    if(msg) msg.textContent = 'Tracking settings loaded.';
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
      target_label: detectorVal === 'haar_face' ? 'face' : 'body'
    };
    const data = await window.bob9kApi.saveTrackingConfig(payload);
    if(data.ok && data.config) {
        document.getElementById('tracking-detector').value = data.config.detector || 'haar_face';
        if(msg) msg.textContent = 'Tracking settings saved.';
        setActionMessage('Tracking settings saved.', 'success');
    } else {
        if(msg) msg.textContent = 'Failed to save tracking settings.';
        setActionMessage('Failed to save tracking settings.', 'error');
    }
  }catch(err){
    if(msg) msg.textContent = 'Failed to save tracking settings.';
    setActionMessage('Failed to save tracking settings.', 'error');
  }
}

async function loadNetworkStatus(){
  if(document.body.dataset.page!=='settings') return;
  const statusTxt = document.getElementById('network-status-text');
  const ipTxt = document.getElementById('network-ip-text');
  try{
    const data = await window.bob9kApi.getNetworkStatus();
    if(statusTxt) statusTxt.textContent = data.connected ? `Connected to ${data.ssid}` : 'Disconnected';
    if(ipTxt) ipTxt.textContent = data.ip || '---';
  }catch(err){
    if(statusTxt) statusTxt.textContent = 'Error checking status';
  }
}

async function scanNetworks(){
  const btn = document.getElementById('network-scan-btn');
  const sel = document.getElementById('network-ssid-select');
  if(!btn || !sel) return;
  
  btn.disabled = true;
  btn.textContent = 'Scanning...';
  sel.innerHTML = '<option value="">-- Scanning --</option>';
  
  try{
    const data = await window.bob9kApi.scanNetworks();
    sel.innerHTML = '<option value="">-- Select a Network --</option>';
    if(data.networks && data.networks.length > 0) {
      data.networks.forEach(net => {
        const opt = document.createElement('option');
        opt.value = net.ssid;
        opt.textContent = `${net.ssid} (${net.signal}%${net.security ? ' - ' + net.security : ''})`;
        sel.appendChild(opt);
      });
    } else {
      sel.innerHTML = '<option value="">-- No Networks Found --</option>';
    }
  }catch(err){
    sel.innerHTML = '<option value="">-- Error Scanning --</option>';
    setActionMessage('Failed to scan networks.', 'error');
  }finally{
    btn.disabled = false;
    btn.textContent = 'Scan';
  }
}

async function connectNetwork(){
  const sel = document.getElementById('network-ssid-select');
  const pwd = document.getElementById('network-password-input');
  const btn = document.getElementById('network-connect-btn');
  const msg = document.getElementById('network-message');
  
  if(!sel || !pwd || !btn) return;
  const ssid = sel.value;
  if(!ssid) {
    if(msg) msg.textContent = 'Please select a network first.';
    return;
  }
  
  btn.disabled = true;
  btn.textContent = 'Connecting...';
  if(msg) msg.textContent = `Attempting to connect to ${ssid}... this may take a moment.`;
  setActionMessage(`Connecting to ${ssid}...`, 'info');
  
  try{
    const data = await window.bob9kApi.connectNetwork(ssid, pwd.value);
    if(data.ok) {
        if(msg) msg.textContent = 'Successfully connected. Validating IP address...';
        setActionMessage(`Connected to ${ssid}!`, 'success');
        pwd.value = '';
    } else {
        if(msg) msg.textContent = `Connection failed: ${data.error || 'Unknown error'}`;
        setActionMessage('Connection failed.', 'error');
    }
  }catch(err){
    if(msg) msg.textContent = 'Error connecting to network.';
    setActionMessage('Connection error.', 'error');
  }finally{
    btn.disabled = false;
    btn.textContent = 'Connect';
    setTimeout(loadNetworkStatus, 3000);
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  if(document.body.dataset.page!=='settings') return;
  loadServoTrimSettings();
  loadCameraSettings();
  loadTrackingSettings();
  loadNetworkStatus();

  document.querySelectorAll('[data-trim-target]').forEach(btn=>{
    btn.addEventListener('click', ()=> adjustTrimInput(btn.dataset.trimTarget, parseInt(btn.dataset.delta || '0', 10)));
  });

  ['camera-fps','camera-brightness','camera-contrast','camera-saturation','camera-sharpness','camera-exposure-compensation'].forEach(id=>{
    const input = document.getElementById(id);
    if(input) input.addEventListener('input', ()=> syncCameraSlider(id, id === 'camera-fps' ? 0 : 2));
  });

  const awb = document.getElementById('camera-awb-mode');
  if(awb) awb.addEventListener('change', setCameraManualGainVisibility);

  const saveBtn = document.getElementById('save-servo-trims');
  if(saveBtn) saveBtn.addEventListener('click', saveServoTrimSettings);

  const saveCameraBtn = document.getElementById('save-camera-settings');
  if(saveCameraBtn) saveCameraBtn.addEventListener('click', saveCameraSettings);

  const resetCameraBtn = document.getElementById('reset-camera-settings');
  if(resetCameraBtn) resetCameraBtn.addEventListener('click', resetCameraSettings);

  const saveTrackingBtn = document.getElementById('save-tracking-settings');
  if(saveTrackingBtn) saveTrackingBtn.addEventListener('click', saveTrackingSettings);

  const centerBtn = document.getElementById('test-steering-center');
  if(centerBtn) centerBtn.addEventListener('click', async()=>{ await window.bob9kApi.steeringCenter(); await refreshStatus(); });

  const homeBtn = document.getElementById('test-camera-home');
  if(homeBtn) homeBtn.addEventListener('click', async()=>{ await window.bob9kApi.cameraHome(); await refreshStatus(); });
  
  const scanBtn = document.getElementById('network-scan-btn');
  if(scanBtn) scanBtn.addEventListener('click', scanNetworks);
  
  const connectBtn = document.getElementById('network-connect-btn');
  if(connectBtn) connectBtn.addEventListener('click', connectNetwork);
});
