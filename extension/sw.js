// Service worker de la extensión: abre cada publicación, inyecta el extractor y devuelve el progreso y el resultado a la app.
const VERSION = chrome.runtime.getManifest().version;
const ALLOWED = /^https:\/\/([a-z0-9-]+\.)*(facebook\.com|instagram\.com|tiktok\.com)\//i;
const ports = new Set();          // pestañas de la app conectadas
const jobs = new Map();           // jobId -> { tabId, port, timer, done }
let workWindowId = null;

const sleep = ms => new Promise(r => setTimeout(r, ms));
const send = (job, msg) => { try { (job && job.port ? job.port : [...ports][0])?.postMessage(msg); } catch (e) {} };

chrome.runtime.onConnect.addListener(port => {
  if (port.name !== 'sca-app') return;
  ports.add(port);
  port.postMessage({ type: 'ready', version: VERSION });
  port.onMessage.addListener(msg => onAppMessage(port, msg));
  port.onDisconnect.addListener(() => ports.delete(port));
});

async function onAppMessage(port, msg) {
  if (!msg || !msg.type) return;
  if (msg.type === 'ping') return port.postMessage({ type: 'pong', version: VERSION });
  if (msg.type === 'extract') return startJob(port, msg);
  if (msg.type === 'stop') return stopJob(msg.jobId, 'stopped');
}

// Ventana de trabajo: pequeña en una esquina sin quitar el foco (por defecto), minimizada o normal
async function workWindow(mode) {
  if (workWindowId != null) {
    try { await chrome.windows.get(workWindowId); return workWindowId; } catch (e) { workWindowId = null; }
  }
  let prev = null; try { prev = await chrome.windows.getLastFocused(); } catch (e) {}
  let opts = { url: 'about:blank', type: 'normal', focused: mode === 'normal' };
  if (mode === 'minimized') opts = { url: 'about:blank', type: 'normal', state: 'minimized' };
  else if (mode === 'normal') Object.assign(opts, { width: 1200, height: 900 });
  else {
    const W = 560, H = 760;
    const left = prev && prev.left != null ? Math.max(0, prev.left + prev.width - W - 16) : 40;
    const top = prev && prev.top != null ? Math.max(0, prev.top + prev.height - H - 16) : 40;
    Object.assign(opts, { width: W, height: H, left, top });
  }
  const w = await chrome.windows.create(opts);
  workWindowId = w.id;
  // devolver el foco a la ventana en la que estaba trabajando el usuario
  if (mode !== 'normal' && prev && prev.id !== w.id) { try { await chrome.windows.update(prev.id, { focused: true }); } catch (e) {} }
  return w.id;
}

function waitComplete(tabId, ms) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => { chrome.tabs.onUpdated.removeListener(l); reject(new Error('La publicación tardó demasiado en cargar.')); }, ms);
    const l = (id, info) => { if (id === tabId && info.status === 'complete') { clearTimeout(t); chrome.tabs.onUpdated.removeListener(l); resolve(); } };
    chrome.tabs.onUpdated.addListener(l);
    chrome.tabs.get(tabId).then(tab => { if (tab.status === 'complete') { clearTimeout(t); chrome.tabs.onUpdated.removeListener(l); resolve(); } }).catch(() => {});
  });
}

async function startJob(port, { jobId, url, options = {} }) {
  if (!jobId || !ALLOWED.test(url || '')) return port.postMessage({ type: 'error', jobId, error: 'Enlace no admitido. Solo Facebook, Instagram o TikTok.' });
  const job = { port, tabId: null, done: false };
  jobs.set(jobId, job);
  try {
    send(job, { type: 'progress', jobId, phase: 'opening' });
    const winId = await workWindow(options.window || (options.visible ? 'normal' : 'small'));
    const tab = await chrome.tabs.create({ windowId: winId, url, active: true });
    job.tabId = tab.id;
    // quitar la pestaña en blanco inicial de la ventana de trabajo
    chrome.tabs.query({ windowId: winId }).then(ts => ts.filter(t => t.url === 'about:blank' && t.id !== tab.id).forEach(t => chrome.tabs.remove(t.id).catch(() => {})));
    await waitComplete(tab.id, 60000);
    await sleep(options.settleMs || 3500);
    if (job.done) return;
    const now = await chrome.tabs.get(tab.id);
    if (/\/login|\/accounts\/login|checkpoint/i.test(now.url || '')) throw new Error('Inicia sesión en ' + new URL(url).hostname.replace(/^www\./, '') + ' en este navegador y vuelve a intentarlo.');
    if (!ALLOWED.test(now.url || '')) throw new Error('La publicación redirigió a otra página.');
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: (id) => {
      window.__fbcx = false;
      window.__scaAuto = { jobId: id, stopRequested: false, emit: e => { try { chrome.runtime.sendMessage(Object.assign({ sca: true, jobId: id }, e)); } catch (err) {} },
        // espera medida por el service worker (sin el frenado de temporizadores de las pestañas ocultas)
        sleep: ms => new Promise(r => { let done = false; const fin = () => { if (!done) { done = true; r(); } };
          try { chrome.runtime.sendMessage({ sca: true, jobId: id, type: 'sleep', ms }, () => { void chrome.runtime.lastError; fin(); }); } catch (err) { setTimeout(fin, ms); }
          setTimeout(fin, ms + 60000); }) };
    }, args: [jobId] });
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['extractor.js'] });
    send(job, { type: 'progress', jobId, phase: 'extracting' });
    job.timer = setTimeout(() => stopJob(jobId, 'timeout'), (options.maxMinutes || 20) * 60000);
  } catch (e) {
    finishJob(jobId, { type: 'error', jobId, error: e.message || String(e) }, options.keepOpen);
  }
}

async function stopJob(jobId, why) {
  const job = jobs.get(jobId); if (!job || job.done) return;
  job.stopWhy = why;
  if (job.tabId != null) {
    try { await chrome.scripting.executeScript({ target: { tabId: job.tabId }, func: () => { if (window.__scaAuto) window.__scaAuto.stopRequested = true; } }); } catch (e) {}
  }
  // si el extractor no responde, se cierra a los 15 s
  setTimeout(() => { const j = jobs.get(jobId); if (j && !j.done) finishJob(jobId, { type: 'stopped', jobId, reason: why }); }, 15000);
}

function finishJob(jobId, msg, keepOpen) {
  const job = jobs.get(jobId); if (!job || job.done) return;
  job.done = true; clearTimeout(job.timer);
  send(job, msg);
  if (job.tabId != null && !keepOpen) chrome.tabs.remove(job.tabId).catch(() => {});
  jobs.delete(jobId);
}

// Mensajes del extractor (desde la pestaña de la red social)
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.sca) return;
  if (msg.type === 'sleep') { setTimeout(() => { try { sendResponse(true); } catch (e) {} }, Math.min(30000, Math.max(0, +msg.ms || 0))); return true; }
  const job = jobs.get(msg.jobId); if (!job) return;
  if (msg.type === 'progress') send(job, { type: 'progress', jobId: msg.jobId, phase: 'extracting', count: msg.count, visible: msg.visible, total: msg.total, round: msg.round, note: msg.note });
  else if (msg.type === 'done') finishJob(msg.jobId, { type: 'result', jobId: msg.jobId, data: msg.data, stopped: !!job.stopWhy, reason: job.stopWhy || '' });
  else if (msg.type === 'error') finishJob(msg.jobId, { type: 'error', jobId: msg.jobId, error: msg.error });
});

// Si el usuario cierra la pestaña de trabajo, el trabajo termina con error
chrome.tabs.onRemoved.addListener(tabId => {
  for (const [id, job] of jobs) if (job.tabId === tabId && !job.done) finishJob(id, { type: 'error', jobId: id, error: 'Se cerró la pestaña de la publicación.' });
});
chrome.windows.onRemoved.addListener(id => { if (id === workWindowId) workWindowId = null; });
