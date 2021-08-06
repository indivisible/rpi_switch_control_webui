const enabledGamepads = new Set();
const bindings = new Map();
const activeGamepads = [];
let controllerTable = null;
let socket=null;
let handlers = {};

// hardcoded config for nintendo switch pro controller on chrome linux
bindings.set('Nintendo Co., Ltd. Pro Controller (STANDARD GAMEPAD Vendor: 057e Product: 2009)', {
  'buttons': {
    'A': 1,
    'B': 0,
    'X': 3,
    'Y': 2,
    'L': 4,
    'R': 5,
    'ZL': 6,
    'ZR': 7,
    '+': 9,
    '-': 8,
    'LS': 10,
    'RS': 11,
    'Up': 12,
    'Right': 15,
    'Down': 13,
    'Left': 14,
    'Home': 16,
    'Capture': 17,
  },
  'axes': [
    [0, 1], [2, 3]
  ]
});

function updateControllers() {
  controllerTable.innerHTML = '';
  // clear the array
  activeGamepads.splice(0, activeGamepads.length);
  for (const gp of navigator.getGamepads()) {
    if (!gp)
      continue;

    const tr = document.createElement('tr');

    const connectedCell = document.createElement('td');
    connectedCell.innerText = '' + gp.connected;
    tr.appendChild(connectedCell);

    const enabledCell = document.createElement('td');
    const enableInput = document.createElement('input');
    const isEnabled = enabledGamepads.has(gp.id);
    enableInput.setAttribute('type', 'checkbox');
    if (isEnabled) {
      enableInput.setAttribute('checked', 'true')
    }
    enableInput.addEventListener('change', () => {
      const enabled = enableInput.checked;
      if (enabled) {
        enabledGamepads.add(gp.id);
      } else {
        enabledGamepads.delete(gp.id);
      }
      updateControllers();
    });
    enabledCell.appendChild(enableInput);
    tr.appendChild(enabledCell);

    const labelCell = document.createElement('td');
    labelCell.innerText = '' + gp.id;
    tr.appendChild(labelCell);

    controllerTable.appendChild(tr);

    if (isEnabled && gp.connected) {
      activeGamepads.push(gp.id);
    }
  }
  if (activeGamepads.length) {
    requestAnimationFrame(updateInput);
  }
}

let lastState = null;
function updateInput() {
  for (const gp of navigator.getGamepads()) {
    if (!gp || !gp.connected)
      continue;
    if (!activeGamepads.includes(gp.id))
      continue;
    const binds = bindings.get(gp.id);
    if (!binds)
      continue;
    const state = {'buttons': {}, 'sticks': []};
    for (const [name, idx] of Object.entries(binds['buttons'])) {
      const val = gp.buttons[idx];
      let pressed = val == 1.0;
      if (typeof(val) == 'object') {
        pressed = val.pressed;
      }
      state['buttons'][name] = pressed;
    }
    state['sticks'] = [];
    function axisValue(idx) {
      if (idx === null )
        return 0.0;
      return gp.axes[idx];
    }
    for (const stick of binds['axes']) {
      state['sticks'].push([axisValue(stick[0]), axisValue(stick[1])]);
    }

    state['serial'] = gp.timestamp;
    lastState = state;
    communicate();

    // we only really want data from 1 controller
    requestAnimationFrame(updateInput);
    return;
  }
}

function communicate() {
  // TODO: make it so that we don't send useless data while a script is running
  if (lastState == null || !socket || socket.readyState != WebSocket.OPEN || socket.bufferedAmount > 0) {
    return;
  }
  socket.send(JSON.stringify({'action': 'input', 'state': lastState}))
  lastState = null;
}

function message(a, b) {
  console.log(a, b)
}

handlers['ack'] = () => {}
handlers['message'] = (msg) => { console.log(msg); }

function connect(){
  const host = location.hostname || '127.0.0.1';
  const ws = new WebSocket(`ws://${host}:6789/`);
  socket = ws;

  //*
  ws.addEventListener('message', (evt) => {
    const msg = JSON.parse(evt.data);
    const handler = handlers[msg.action];
    if(handler){
      handler(msg);
    }else{
      message('error', `Unhandled message:\n${evt.data}`);
    }
  });
  // */
  ws.addEventListener('error', (err) => {
    message('warning', `WebSocket error: ${err.message}`);
    ws.close();
  });
  ws.addEventListener('close', (evt) => {
    message('warning', `WebSocket closed: ${evt.reason}`);
    //updateStatus();
    setTimeout(connect, 3000);
  });
  ws.addEventListener('open', () => {
    console.log('connected!')
    //updateStatus();
  });
}

document.addEventListener('DOMContentLoaded', () => {
  controllerTable = document.querySelector('#controller-table')
  document.querySelector('#setup-controller').addEventListener('click', () => {
  });

  updateControllers();
  window.addEventListener("gamepadconnected", () => updateControllers());
  window.addEventListener("gamepaddisconnected", () => updateControllers());
  connect();
});
