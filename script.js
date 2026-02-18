// === AUDIO ===
let ax;
function initAx() { ax = new (window.AudioContext || window.webkitAudioContext)(); }

function tone(f, typ, dur, vol = 0.1) {
  if (!ax) return;
  const o = ax.createOscillator(), g = ax.createGain(), t = ax.currentTime;
  o.connect(g); g.connect(ax.destination);
  o.type = typ; o.frequency.setValueAtTime(f, t);
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + dur);
  o.start(); o.stop(t + dur);
}

function ambientDrone() {
  if (!ax) return;
  const t = ax.currentTime;
  // Deep unsettling drone
  [40, 42, 38].forEach((f, i) => {
    const o = ax.createOscillator(), g = ax.createGain();
    o.connect(g); g.connect(ax.destination);
    o.type = 'sine'; o.frequency.setValueAtTime(f, t);
    g.gain.setValueAtTime(0.015, t);
    g.gain.linearRampToValueAtTime(0.001, t + 8);
    o.start(t + i * 0.3); o.stop(t + 8);
  });
}

function heartbeat(vol = 0.3) {
  tone(55, 'sine', 0.08, vol);
  setTimeout(() => tone(45, 'sine', 0.1, vol * 0.7), 120);
}

function whisper() {
  if (!ax) return;
  // White noise whisper
  const t = ax.currentTime;
  const buf = ax.createBuffer(1, ax.sampleRate * 0.8, ax.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * 0.3;
  const s = ax.createBufferSource(), g = ax.createGain();
  const filt = ax.createBiquadFilter();
  filt.type = 'bandpass'; filt.frequency.value = 800; filt.Q.value = 2;
  s.buffer = buf; s.connect(filt); filt.connect(g); g.connect(ax.destination);
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(0.15, t + 0.2);
  g.gain.linearRampToValueAtTime(0, t + 0.7);
  s.start();
}

function SCREAM() {
  if (!ax) return;
  const t = ax.currentTime;
  // Loud noise burst
  const buf = ax.createBuffer(1, ax.sampleRate * 3, ax.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1);
  const s = ax.createBufferSource(), g = ax.createGain();
  s.buffer = buf; s.connect(g); g.connect(ax.destination);
  g.gain.setValueAtTime(0.7, t);
  g.gain.linearRampToValueAtTime(0.01, t + 2.5);
  s.start();
  // Descending screech
  const o = ax.createOscillator(), og = ax.createGain();
  o.connect(og); og.connect(ax.destination);
  o.type = 'sawtooth';
  o.frequency.setValueAtTime(1200, t);
  o.frequency.exponentialRampToValueAtTime(80, t + 2);
  og.gain.setValueAtTime(0.6, t);
  og.gain.linearRampToValueAtTime(0.01, t + 2);
  o.start(); o.stop(t + 2);
  // Dissonant chord
  [666, 440, 220].forEach(f => {
    const o2 = ax.createOscillator(), g2 = ax.createGain();
    o2.connect(g2); g2.connect(ax.destination);
    o2.type = 'square';
    o2.frequency.setValueAtTime(f, t);
    g2.gain.setValueAtTime(0.3, t);
    g2.gain.exponentialRampToValueAtTime(0.001, t + 1.5);
    o2.start(); o2.stop(t + 1.5);
  });
}

// === DOM ===
const out = document.getElementById('out');
const iline = document.getElementById('iline');
const cmd = document.getElementById('cmd');
const pr = document.getElementById('prompt');
const fl = document.getElementById('flash');
const vig = document.getElementById('vignette');
const eye = document.getElementById('eye-bg');
const pupil = document.getElementById('pupil');

const S = ms => new Promise(r => setTimeout(r, ms));

async function P(txt, cls = '', spd = 12) {
  const div = document.createElement('div');
  div.className = `line ${cls}`;
  out.appendChild(div);
  for (let c of txt) {
    div.textContent += c;
    out.parentElement.scrollTop = out.parentElement.scrollHeight;
    if (c !== ' ' && spd > 0) {
      tone(150 + Math.random() * 150, 'square', 0.02, 0.03);
      await S(spd);
    }
  }
}

// === GAME STATE ===
let dread = 0;            // 0-100, builds with actions
let phase = 'normal';     // normal → uneasy → dread → panic → end
let hbInterval = null;
let droneInterval = null;
let glitchTimeout = null;
let path = '/home/guest';
let filesRead = new Set();
let cmdCount = 0;

// === FILE SYSTEM ===
const FS = {
  'home': {
    'guest': {
      'readme.txt': 'Welcome to UNJ-NET Terminal v4.\nRecover the lost data from /secure.\nDo NOT interact with unknown processes.',
      'notes.log': 'Day 1 — System normal. Routine maintenance.\nDay 3 — Weird traffic from unknown source.\nDay 5 — Server room temp dropped 10 degrees.\nDay 7 — I keep hearing breathing through my headset.\nDay 8 — The webcam light turned on by itself.\nDay 9 —',
      'photo.jpg': '[CORRUPTED IMAGE DATA]\n\nPartial EXIF: Date taken: 1999-12-31 23:59:59\nCamera: UNKNOWN\nSubject: YOUR FACE',
    }
  },
  'var': {
    'log': {
      'syslog': '[2024-01-15 03:12:01] ERROR: Unauthorized access from PID 6666\n[2024-01-15 03:12:02] WARN: Firewall rule bypassed\n[2024-01-15 03:12:03] CRITICAL: Entity "ECHO" spawned\n[2024-01-15 03:12:04] CRITICAL: IT KNOWS YOUR NAME',
      'access.log': 'guest: LOGIN SUCCESS\nroot: LOGIN FAILED x47\nadmin: LOGIN FAILED x12\n???: LOGIN SUCCESS\nECHO: LOGIN SUCCESS — "I was always here."',
      'error.log': 'segfault at 0x00000000\nsegfault at 0x00000000\nsegfault at 0x00000000\nH E L P   M E\nsegfault at 0xDEADBEEF',
    }
  },
  'secure': {
    'final_report.enc': 'ENCRYPTED — Run "decrypt" to decode.',
    'audio_capture.raw': '[AUDIO FILE]\n\nTranscription:\n"...don\'t open it... it\'s not a program...\n...it\'s something else... it remembers...\n...it remembers everyone who logged in...\n...and it never lets them leave..."',
  },
  'tmp': {
    '.hidden_note': 'If you are reading this, you are already trapped.\nThe terminal is not a program.\nIt is a mouth.\nAnd you just fed it your name.',
  }
};

function getNode(p) {
  const parts = p.split('/').filter(x => x);
  let n = FS;
  for (const k of parts) {
    if (n && typeof n === 'object' && !Array.isArray(n) && k in n) n = n[k];
    else return null;
  }
  return n;
}

function isDir(n) { return n && typeof n === 'object' && !Array.isArray(n); }

// === PHASE MANAGEMENT ===
function updatePhase() {
  if (dread >= 90 && phase !== 'end') {
    phase = 'panic';
    vig.style.background = 'radial-gradient(ellipse at center, transparent 20%, rgba(80,0,0,0.5) 60%, rgba(0,0,0,0.95) 100%)';
    document.getElementById('term').classList.add('screen-glitch');
    eye.className = 'eye-visible-3';
  } else if (dread >= 60) {
    phase = 'dread';
    vig.style.background = 'radial-gradient(ellipse at center, transparent 30%, rgba(40,0,0,0.4) 70%, rgba(0,0,0,0.9) 100%)';
    if (!hbInterval) hbInterval = setInterval(() => heartbeat(0.2 + dread / 200), 1200);
    eye.className = 'eye-visible-2';
  } else if (dread >= 30) {
    phase = 'uneasy';
    vig.style.background = 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.8) 100%)';
    eye.className = 'eye-visible-1';
  }
}

async function entityInterrupt() {
  const msgs = [
    "Why are you still here?",
    "I can see your screen.",
    "You should not have read that.",
    "Your webcam light is on.",
    "Listen. Can you hear me breathing?",
    "I know what you look like.",
    "The terminal remembers you.",
    "Close your eyes. I dare you.",
    "I am behind the screen.",
    "You cannot close this tab.",
  ];
  await S(800);
  whisper();
  await P(msgs[Math.floor(Math.random() * msgs.length)], 'ent', 40);
}

async function subtleGlitch() {
  fl.style.opacity = 0.15;
  setTimeout(() => fl.style.opacity = 0, 30);
  if (dread > 50) {
    const g = document.createElement('div');
    g.className = 'line ent';
    g.textContent = '█'.repeat(Math.floor(Math.random() * 40 + 5));
    g.style.opacity = 0.3;
    out.appendChild(g);
    setTimeout(() => g.remove(), 300);
  }
}

// === COMMAND HANDLER ===
async function exec(raw) {
  const args = raw.trim().split(/\s+/);
  const c = args[0]?.toLowerCase();
  const a = args.slice(1).join(' ');

  // Echo input
  const e = document.createElement('div');
  e.className = 'line dim';
  e.textContent = `${pr.textContent} ${raw}`;
  out.appendChild(e);
  cmd.value = ''; iline.style.display = 'none';
  cmdCount++;

  if (!c) { show(); return; }

  // Random ambient sounds
  if (dread > 20 && Math.random() < 0.3) ambientDrone();

  if (c === 'help') {
    await P('Commands: ls, cd, cat, pwd, whoami, clear, decrypt');
  }
  else if (c === 'ls') {
    const target = a ? resolve(a) : path;
    const node = getNode(target);
    if (isDir(node)) {
      const items = Object.keys(node);
      for (const item of items) {
        const isD = isDir(node[item]);
        await P((isD ? '📁 ' : '📄 ') + item, isD ? 'dir' : 'file', 0);
      }
      if (items.length === 0) await P('(empty)', 'dim', 0);
    } else { await P(`ls: cannot access '${a}': not found`, 'err'); }
  }
  else if (c === 'cd') {
    if (!a || a === '~') { path = '/home/guest'; }
    else if (a === '..') {
      const parts = path.split('/').filter(x => x);
      parts.pop(); path = '/' + parts.join('/') || '/';
    } else {
      const target = resolve(a);
      const node = getNode(target);
      if (isDir(node)) { path = target; }
      else { await P(`cd: ${a}: not found`, 'err'); }
    }
    pr.textContent = `guest@NODE-7:${path}$`;
  }
  else if (c === 'cat') {
    if (!a) { await P('usage: cat <file>', 'warn'); }
    else {
      const target = resolve(a);
      const node = getNode(target);
      if (node && !isDir(node)) {
        // Content
        const lines = node.split('\n');
        for (const ln of lines) {
          const cls = ln.includes('CRITICAL') || ln.includes('HELP') ? 'err' :
            ln.includes('ECHO') || ln.includes('remembers') ? 'blood' : '';
          await P(ln, cls, 8);
        }
        // Build dread
        filesRead.add(a);
        dread += 12;
        updatePhase();

        // Trigger events based on phase
        if (dread > 30 && Math.random() < 0.4) await subtleGlitch();
        if (dread > 50 && Math.random() < 0.5) await entityInterrupt();
        if (dread > 70) {
          await S(500);
          whisper();
          if (Math.random() < 0.4) {
            await P('\n[SYSTEM] WARNING: External process monitoring your session.', 'err');
            tone(80, 'sawtooth', 1, 0.25);
          }
        }
      } else { await P(`cat: ${a}: not found`, 'err'); }
    }
  }
  else if (c === 'pwd') { await P(path); }
  else if (c === 'whoami') {
    await P('guest');
    if (dread > 40) {
      await S(1500);
      await P('...are you sure?', 'ent', 60);
      dread += 8;
      updatePhase();
    }
  }
  else if (c === 'clear') { out.innerHTML = ''; }
  else if (c === 'decrypt') {
    await P('Initiating decryption...', 'sys', 25);
    await S(1000);
    await P('Decrypting final_report.enc...', 'sys', 20);
    await S(1500);
    await P('█████████████████████░░░░░ 78%', 'warn', 5);
    await S(800);
    await P('████████████████████████░ 96%', 'warn', 5);
    await S(600);
    await P('DECRYPTION COMPLETE.', 'err', 30);
    await S(1000);
    tone(100, 'sawtooth', 0.5, 0.3);
    await P('\n--- FINAL REPORT ---', 'err', 15);
    await P('Subject: Entity "ECHO"', '', 15);
    await P('Status: ACTIVE — CONTAINED IN TERMINAL', '', 15);
    await P('Behavior: Mimics system processes.', '', 15);
    await P('         Responds to user input.', '', 15);
    await P('         Feeds on attention.', '', 15);
    await S(1500);
    await P('\nNote from Dr. ██████:', 'blood', 20);
    await P('"If you are reading this, the entity has already', 'blood', 25);
    await P(' noticed you. Do not look away from the screen.', 'blood', 25);
    await P(' It moves when you are not watching."', 'blood', 30);
    await S(2000);
    document.getElementById('term').classList.add('screen-glitch');
    whisper(); whisper();
    await P('\n\n\n', '', 0);
    await P('                    I   A M   H E R E', 'ent', 80);
    await S(1500);
    await P(`                    I KNOW YOU ARE ${document.title}`, 'ent', 50);
    await S(1000);
    JUMPSCARE();
    return;
  }
  else if (c === 'exit' || c === 'quit' || c === 'logout') {
    await P('ACCESS DENIED. SESSION LOCKED.', 'err');
    dread += 15;
    updatePhase();
    if (dread > 80) {
      await S(500);
      await P('YOU CANNOT LEAVE.', 'ent', 50);
      await S(2000);
      JUMPSCARE();
      return;
    }
  }
  else {
    await P(`${c}: command not found`, 'err');
    if (dread > 60 && Math.random() < 0.3) {
      await S(800);
      await P(`Did you mean: "help me"?`, 'ent', 40);
      dread += 5;
    }
  }

  // Random entity events at high dread
  if (phase === 'panic' && Math.random() < 0.3) {
    await S(1500);
    await entityInterrupt();
  }

  show();
}

function resolve(target) {
  if (target.startsWith('/')) return target;
  const base = path === '/' ? '' : path;
  return base + '/' + target;
}

function show() { iline.style.display = 'flex'; cmd.focus(); }

function JUMPSCARE() {
  phase = 'end';
  iline.style.display = 'none';
  const jsDiv = document.getElementById('js');
  const jsImg = document.getElementById('jsimg');
  jsImg.src = 'https://wanderlustandlipstick.com/blogs/wanderlushdiary/files/2012/04/80545124.jpg';
  // jsImg.src = 'https://preview.redd.it/is-this-face-scary-enough-its-in-an-upcoming-video-for-my-v0-abfr2goik2ae1.jpeg?auto=webp&s=2cb8128eedf0444a482587d299913d2a2bbf0505';
  jsDiv.style.display = 'flex';
  SCREAM();
  document.body.style.overflow = 'hidden';
  let t = 0;
  const iv = setInterval(() => {
    jsDiv.style.backgroundColor = t % 2 === 0 ? '#ff0000' : '#000';
    jsImg.style.transform = `translate(${Math.random() * 20 - 10}px,${Math.random() * 20 - 10}px) scale(${1 + Math.random() * 0.2})`;
    t++;
  }, 40);
  // Vibrate if mobile
  if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 500]);
  setTimeout(() => {
    clearInterval(iv);
    document.body.innerHTML = '<div style="position:fixed;inset:0;background:#000;display:flex;align-items:center;justify-content:center;color:#300;font-family:monospace;font-size:1rem;text-align:center;padding:2rem">Connection terminated.<br><br><span style="color:#600;font-size:0.7rem">Session logged. Entity released.</span></div>';
  }, 3500);
}

// === INIT ===
document.getElementById('start').addEventListener('click', async () => {
  document.getElementById('start').style.display = 'none';
  initAx();

  await P('Booting UNJ-NET v4.0...', 'sys', 20);
  await S(800);
  await P('Loading kernel modules...', 'sys', 10);
  await S(500);
  await P('Network interface: CONNECTED', 'sys', 10);
  await S(300);
  await P('Filesystem: MOUNTED', 'sys', 10);
  await S(800);
  out.innerHTML = '';

  await P('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim', 0);
  await P('  UNJ-NET Remote Terminal v4.0', '', 5);
  await P('  Node: 7  |  User: guest', '', 5);
  await P('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'dim', 0);
  await P('');
  await P("Type 'help' for available commands.", 'sys');
  await P("Your task: locate and decrypt the file in /secure.", 'warn');
  await P('');

  pr.textContent = `guest@NODE-7:${path}$`;
  show();

  // Start ambient heartbeat loop (subtle at first)
  droneInterval = setInterval(() => {
    if (dread > 15) ambientDrone();
  }, 12000);
});

cmd.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') exec(cmd.value);
});

// Prevent zoom on mobile
document.addEventListener('gesturestart', e => e.preventDefault());

// Eye Tracking
document.addEventListener('mousemove', (e) => {
  if (dread < 20) return;
  const x = (e.clientX / window.innerWidth) * 100;
  const y = (e.clientY / window.innerHeight) * 100;
  pupil.style.left = `${x}%`;
  pupil.style.top = `${y}%`;
});
