function bindClickAction(actionName, handler, options={}){
  const button = document.querySelector(`[data-action="${actionName}"]`);
  if(!button) return;
  button.addEventListener('click', async(event)=>{
    event.preventDefault();
    try{
      await invokeAndRefresh(handler, options);
    }catch(err){
      console.error(`Action ${actionName} failed`, err);
    }
  });
}

document.addEventListener('DOMContentLoaded', ()=>{
  const page = document.body?.dataset?.page;

  const speedSlider = document.getElementById('drive-speed');
  const speedLabel = document.getElementById('drive-speed-label');
  if(speedSlider && speedLabel){
    const updateLabel = ()=>{ speedLabel.textContent = `${Number(speedSlider.value || 40)}%`; };
    speedSlider.addEventListener('input', updateLabel);
    updateLabel();
  }

  bindHoldButton('motor-forward-hold', ()=> window.bob9kApi.motorForward(getDriveSpeed()));
  bindHoldButton('motor-backward-hold', ()=> window.bob9kApi.motorBackward(getDriveSpeed()));

  bindClickAction('motor-stop', ()=> window.bob9kApi.motorStop(), { successMessage: 'Motors stopped.', errorMessage: 'Failed to stop motors.' });
  bindClickAction('motor-clear-estop', ()=> window.bob9kApi.motorClearEstop(), { pendingMessage: 'Clearing E-STOP…', successMessage: 'E-STOP cleared.', errorMessage: 'Failed to clear E-STOP.' });
  bindClickAction('stop-all', ()=> window.bob9kApi.stopAll(), { successMessage: 'Stop command sent.', errorMessage: 'Failed to stop robot.' });

  bindClickAction('steering-left', ()=> window.bob9kApi.steeringLeft(), { successMessage: 'Steering left.', errorMessage: 'Failed to steer left.' });
  bindClickAction('steering-center', ()=> window.bob9kApi.steeringCenter(), { successMessage: 'Steering centered.', errorMessage: 'Failed to center steering.' });
  bindClickAction('steering-right', ()=> window.bob9kApi.steeringRight(), { successMessage: 'Steering right.', errorMessage: 'Failed to steer right.' });

  bindClickAction('camera-pan-left', ()=> window.bob9kApi.cameraPanLeft(), { successMessage: 'Camera panned left.', errorMessage: 'Failed to pan camera left.' });
  bindClickAction('camera-pan-right', ()=> window.bob9kApi.cameraPanRight(), { successMessage: 'Camera panned right.', errorMessage: 'Failed to pan camera right.' });
  bindClickAction('camera-tilt-up', ()=> window.bob9kApi.cameraTiltUp(), { successMessage: 'Camera tilted up.', errorMessage: 'Failed to tilt camera up.' });
  bindClickAction('camera-tilt-down', ()=> window.bob9kApi.cameraTiltDown(), { successMessage: 'Camera tilted down.', errorMessage: 'Failed to tilt camera down.' });
  bindClickAction('camera-home', ()=> window.bob9kApi.cameraHome(), { successMessage: 'Camera centered.', errorMessage: 'Failed to home camera.' });

  if(page === 'control'){
    refreshStatus().catch(()=>{});
  }
});
