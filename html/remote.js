var websocket;
var handlers = [];
var scripts = JSON.parse(localStorage.getItem('scripts')) || {};
var scriptEditor, scriptTitleInput;

function message(severity, message){
  console.log(`${severity}: ${message}`);
  let log = document.querySelector('#messages');
  if(log){
    log.innerText = message + '\n' + log.innerText;
  }
  if(severity == 'error'){
    alert(message);
  }
}

function downloadObj(obj, name){
  let a = document.createElement('a');
  a.download = name;
  a.href = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(obj));
  a.dataset.downloadurl = ['text/json', a.download, a.href].join(':');
  let e = document.createEvent('MouseEvents');
  e.initMouseEvent('click', true, false, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
  a.dispatchEvent(e);
}

function isEditorSaved(){
  let title = getScriptTitle();
  let current = scriptEditor.value;
  let saved = scripts[title];
  if(!current.trim())
    return true;
  if(!title)
    return false;
  if(saved !== current)
    return false;
  return true;
}

function getScriptTitle(){
  return scriptTitleInput.value.trim();
}

function saveScript(){
  if(isEditorSaved())
    return false;
  let title = getScriptTitle();
  let contents = scriptEditor.value;
  if(!title){
    message('error', 'Empty title!');
    return false;
  }
  if(!contents){
    message('error', 'Empty script!');
    return false;
  }
  scripts[title] = contents;
  localStorage.setItem('scripts', JSON.stringify(scripts));
  updateScriptList();
  return true;
}

function loadScript(name){
  let script = scripts[name];
  if(!script){
    message('error', `No script named '${name}'`);
    return false;
  }
  if(!isEditorSaved() && !confirm('Current script is not saved! Lose changes?')){
    return false;
  }
  scriptTitleInput.value = name;
  scriptEditor.value = script;
}

function updateScriptList(){
  const list = document.querySelector('#saved-scripts');
  list.innerHTML = '';
  let frag = new DocumentFragment();
  for(const title in scripts){
    let li = document.createElement('li');
    let a = document.createElement('a');
    li.appendChild(a);
    a.innerText = title;
    a.href = '#';
    a.addEventListener('click', (evt) => {
      loadScript(title);
      evt.preventDefault();
      return false;
    });
    frag.appendChild(li);
  }
  list.appendChild(frag);
}

handlers['message'] = (msg) => message(msg.severity, msg.message);
handlers['status'] = (msg) => {
  document.querySelector('#status').innerText = msg.ok;
}

function connect(){
  let host = location.hostname || '127.0.0.1';
  let ws = new WebSocket(`ws://${host}:6789/`);
  websocket = ws;

  ws.addEventListener('message', (evt) => {
    let msg = JSON.parse(evt.data);
    let handler = handlers[msg.action];
    if(handler){
      handler(msg);
    }else{
      message('error', `Unhandled message:\n${evt.data}`);
    }
  });
  ws.addEventListener('error', (err) => {
    message('warning', `WebSocket error: ${err.message}`);
    ws.close();
  });
  ws.addEventListener('close', (evt) => {
    message('warning', `WebSocket closed: ${evt.reason}`);
    updateStatus();
    setTimeout(connect, 3000);
  });
  ws.addEventListener('open', () => {
    updateStatus();
  });
}

function updateStatus(){
  document.querySelector('#status').innerText = '???';
  if (websocket.readyState == WebSocket.OPEN) {
    sendObj({action: 'status'});
  } else {
    document.querySelector('#status').innerText = 'disconnected';
  }
}

function sendObj(obj){
  if (websocket && websocket.readyState == WebSocket.OPEN) {
    websocket.send(JSON.stringify(obj));
  }
}

document.addEventListener('DOMContentLoaded', () => {
  scriptEditor = document.querySelector('#script-editor');
  scriptTitleInput = document.querySelector('#script-title');
  connect();
  updateScriptList();
  document.querySelector('#test').addEventListener('click', updateStatus);
  document.querySelector('#run-script').addEventListener('click', () => {
    sendObj({
      action: 'run-script',
      text: scriptEditor.value
    });
  });
  document.querySelector('#abort-script').addEventListener('click', () => {
    sendObj({action: 'abort-script'});
  });
  document.querySelector('#restart').addEventListener('click', () => {
    sendObj({action: 'restart'});
  });
  document.querySelector('#save-script').addEventListener('click', saveScript);
  document.querySelector('#save-backup').addEventListener('click', () => {
    downloadObj(scripts, 'fakecon_scripts.json');
  });
});
