const patrolPage = () => document.body.dataset.page === 'patrol';
const $p = (id) => document.getElementById(id);

let patrolCurrentState = null;
let patrolLastRefresh = 0;

async function patrolFetch(url, opts={}) {
  const r = await fetch(url, {headers: {'Content-Type':'application/json'}, ...opts});
  const data = await r.json();
  if (!r.ok) throw new Error(data?.error || `request failed: ${r.status}`);
  return data;
}

function patrolSetValue(id, value) {
  const el = $p(id);
  if (!el) return;
  el.value = value ?? '';
}

function patrolFillConfig(payload) {
  const cfg = payload.config || {};
  [
    'speed', 'avoidance_distance_cm', 'scan_pan_min', 'scan_pan_max', 
    'scan_step', 'scan_tilt_angle', 'detection_behavior'
  ].forEach((k) => patrolSetValue(k, cfg[k]));
  
  patrolSetValue('targets', Array.isArray(cfg.targets) ? cfg.targets.join(',') : (cfg.targets || ''));
}

function patrolReadConfigForm() {
  return {
    speed: Number($p('speed').value || 35),
    avoidance_distance_cm: Number($p('avoidance_distance_cm').value || 30),
    targets: $p('targets').value.trim(),
    detection_behavior: $p('detection_behavior').value || 'log',
    scan_pan_min: Number($p('scan_pan_min').value || 45),
    scan_pan_max: Number($p('scan_pan_max').value || 135),
    scan_step: Number($p('scan_step').value || 2),
    scan_tilt_angle: Number($p('scan_tilt_angle').value || 90)
  };
}

async function patrolRefresh() {
  const now = Date.now();
  if (now - patrolLastRefresh < 500) return;
  patrolLastRefresh = now;
  try {
    const resp = await patrolFetch('/api/patrol/state');
    const s = resp.state || {};
    patrolCurrentState = s;
    
    $p('status-pill-local').textContent = s.enabled ? 'Active' : 'Idle';
    $p('status-pill-local').className = s.enabled ? 'status-pill status-ready' : 'status-pill';
    $p('toggle-patrol').textContent = s.enabled ? 'Disable Patrol' : 'Enable Patrol';
    $p('toggle-patrol').className = s.enabled ? 'danger' : 'primary';
    
    $p('detect-count').textContent = `Total Detections: ${s.detect_count || 0}`;
    if($p('drive-state-stat')) $p('drive-state-stat').textContent = s.drive_state || '--';
    if($p('speed-stat')) $p('speed-stat').textContent = `${s.speed || 0}%`;
    if($p('last-detect-stat')) $p('last-detect-stat').textContent = s.last_detected || 'None';
    
    const usm = s.metrics?.ultrasonic_cm;
    if($p('avoid-dist-stat')) $p('avoid-dist-stat').textContent = usm != null ? `${usm.toFixed(1)} cm` : '--';
    
  } catch (err) {
    console.error('Patrol refresh error', err);
  }
}

async function patrolBoot() {
  try {
    const cfg = await patrolFetch('/api/patrol/config');
    patrolFillConfig(cfg);
    await patrolRefresh();
    setInterval(() => patrolRefresh(), 1000);
  } catch (err) {
    console.error('Patrol boot error', err);
  }
}

function initHelpTooltips() {
  const tooltip = document.getElementById('help-tooltip');
  if (!tooltip) return;
  let hideTimer = null;
  document.querySelectorAll('.help-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      clearTimeout(hideTimer);
      const text = btn.dataset.help || '';
      tooltip.textContent = text;
      tooltip.style.display = 'block';
      const rect = btn.getBoundingClientRect();
      let left = rect.left;
      let top = rect.bottom + 6;
      if (left + 290 > window.innerWidth) left = window.innerWidth - 296;
      tooltip.style.left = left + 'px';
      tooltip.style.top = top + 'px';
      hideTimer = setTimeout(() => { tooltip.style.display = 'none'; }, 4000);
    });
  });
  document.addEventListener('click', () => {
    clearTimeout(hideTimer);
    tooltip.style.display = 'none';
  });
  document.addEventListener('scroll', () => {
    clearTimeout(hideTimer);
    tooltip.style.display = 'none';
  }, {passive: true});
}

document.addEventListener('DOMContentLoaded', () => {
  if (!patrolPage()) return;
  
  initHelpTooltips();
  patrolBoot();

  $p('toggle-patrol').addEventListener('click', async () => {
    try {
      if (patrolCurrentState?.enabled) {
        await patrolFetch('/api/patrol/disable', {method:'POST'});
      } else {
        await patrolFetch('/api/patrol/enable', {method:'POST'});
      }
      patrolRefresh();
    } catch (err) { console.error('toggle error', err); }
  });

  $p('save-config').addEventListener('click', async () => {
    try {
      const payload = patrolReadConfigForm();
      const rawTargets = payload.targets;
      // Convert 'person,dog' to array of strings
      payload.targets = rawTargets.split(',').map(s=>s.trim()).filter(Boolean);
      await patrolFetch('/api/patrol/config', {method:'POST', body: JSON.stringify(payload)});
      
      if (window.setActionMessage) setActionMessage('Patrol config saved.', 'success');
      patrolRefresh();
    } catch (err) {
      if (window.setActionMessage) setActionMessage('Failed to save patrol config.', 'error');
    }
  });
});
