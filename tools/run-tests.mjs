#!/usr/bin/env node
// Ejecuta las páginas de tests/ en Chrome sin interfaz (tiempo real, vía protocolo DevTools) y muestra el resultado.
//   node tools/run-tests.mjs                     → todos los tests/*.test.html
//   node tools/run-tests.mjs tests/x.test.html   → uno concreto
// Requiere Node 22+ (WebSocket integrado) y Google Chrome. Sin dependencias.
import { spawn } from 'node:child_process';
import { readdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const root = resolve(new URL('..', import.meta.url).pathname);
const files = process.argv.slice(2).length ? process.argv.slice(2).map(f => resolve(f))
  : readdirSync(join(root, 'tests')).filter(f => f.endsWith('.test.html')).map(f => join(root, 'tests', f));
const CHROME = process.env.CHROME || 'google-chrome';
const TIMEOUT = +(process.env.TEST_TIMEOUT || 240000);
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function runOne(file){
  const profile = mkdtempSync(join(tmpdir(), 'sca-test-'));
  const port = 9300 + Math.floor(Math.random() * 500);
  const chrome = spawn(CHROME, ['--headless=new', '--allow-file-access-from-files', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', 'about:blank'], { stdio:'ignore' });
  try{
    let target;
    for(let i = 0; i < 100 && !target; i++){ try{ const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); target = l.find(t => t.type === 'page'); }catch(e){} if(!target) await sleep(100); }
    if(!target) throw new Error('No se pudo conectar con Chrome');
    const ws = new WebSocket(target.webSocketDebuggerUrl); let id = 0; const pend = new Map();
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = e => { const m = JSON.parse(e.data); if(m.id && pend.has(m.id)){ pend.get(m.id)(m); pend.delete(m.id); } };
    const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id:i, method, params })); });
    const evalJs = async expr => (await send('Runtime.evaluate', { expression:expr, returnByValue:true, awaitPromise:true })).result?.result?.value;
    await send('Page.enable');
    await send('Page.navigate', { url:'file://' + file });
    const t0 = Date.now(); let title = '';
    while(Date.now() - t0 < TIMEOUT){ await sleep(500); title = await evalJs('document.title') || ''; if(/^(PASS|FAIL)/.test(title)) break; }
    const lines = await evalJs(`[...document.querySelectorAll('#out li')].map(li => (li.className === 'ok' ? '  ✔ ' : '  ✘ ') + li.childNodes[0].textContent.replace(/^[✔✘] /, '') + ((li.className === 'ko' || /^. DBG/.test(li.textContent)) && li.querySelector('small') ? '\\n      ' + li.querySelector('small').textContent.slice(0, 400) : ''))`) || [];
    ws.close();
    return { title:/^(PASS|FAIL)/.test(title) ? title : 'TIMEOUT', lines };
  } finally { chrome.kill('SIGKILL'); await sleep(200); try{ rmSync(profile, { recursive:true, force:true }); }catch(e){} }
}

let failed = 0;
for(const f of files){
  const r = await runOne(f);
  console.log(`\n${r.title.startsWith('PASS') ? '✔' : '✘'} ${f.replace(root + '/', '')}: ${r.title}`);
  r.lines.forEach(l => console.log(l));
  if(!r.title.startsWith('PASS')) failed++;
}
process.exit(failed ? 1 : 0);
