function bindLightAction(actionName, handler, successMessage){
  const button = document.querySelector(`[data-action="${actionName}"]`);
  if(!button) return;
  button.addEventListener('click', async(event)=>{
    event.preventDefault();
    try{
      await invokeAndRefresh(handler, { successMessage, errorMessage: `Failed light action: ${actionName}` });
    }catch(err){
      console.error(`Light action ${actionName} failed`, err);
    }
  });
}

document.addEventListener('DOMContentLoaded', ()=>{
  bindLightAction('led-off', ()=> window.bob9kApi.lightsOff(), 'Eyes off.');
  bindLightAction('led-ready', ()=> window.bob9kApi.setLightState('READY'), 'Lights set to ready.');
  bindLightAction('led-error', ()=> window.bob9kApi.setLightState('ERROR'), 'Lights set to error.');
  bindLightAction('led-police', ()=> window.bob9kApi.setLightState('POLICE'), 'Police mode engaged.');
  bindLightAction('led-auto', ()=> window.bob9kApi.setLightState('AUTO'), 'Lights returned to auto mode.');
  bindLightAction('led-custom-blue', ()=> window.bob9kApi.setLightColor(0,0,255), 'Lights set to blue.');
  bindLightAction('led-custom-white', ()=> window.bob9kApi.setLightColor(255,255,255), 'Lights set to white.');
});
