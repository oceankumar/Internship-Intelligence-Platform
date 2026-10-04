import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const frontend=fileURLToPath(new URL('..',import.meta.url));
const backend=fileURLToPath(new URL('../../backend',import.meta.url));
const children=[];
function start(cmd,args,cwd,env={}) {
  const child=spawn(cmd,args,{cwd,env:{...process.env,...env},detached:true,stdio:['ignore','pipe','pipe']});
  child.stdout.on('data',d => process.stdout.write(d));
  child.stderr.on('data',d => process.stderr.write(d));
  children.push(child);
  return child;
}
async function ready(url) {
  for(let i=0;i<60;i++) {
    try {const r=await fetch(url);if(r.ok)return;} catch {}
    await delay(500);
  }
  throw new Error('Startup timed out: '+url);
}
try {
  start('.venv/bin/python',['-m','scripts.serve_test_workspace'],backend);
  await ready('http://127.0.0.1:8011/health');
  assert.equal((await fetch('http://127.0.0.1:8011/ready')).status,200);
  start('npm',['run','start','--','--hostname','127.0.0.1','--port','3011'],frontend,{API_BASE_URL:'http://127.0.0.1:8011',ALLOWED_HOSTS:'127.0.0.1:3011,localhost:3011'});
  await ready('http://127.0.0.1:3011');
  const browser=start('node',['scripts/browser-check.mjs'],frontend);
  const code=await new Promise(resolve => browser.on('exit',resolve));
  assert.equal(code,0,'Browser workflow failed');
  console.log('PASS: complete product smoke startup -> fixture discovery -> browser -> persistence -> export');
  start('.venv/bin/python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8012'],backend,{PUBLIC_DEMO_MODE:'true',APP_ENV:'production',API_TOKEN:'isolated-demo-test',ALLOWED_HOSTS:'["127.0.0.1","localhost"]'});
  await ready('http://127.0.0.1:8012/health');
  start('npm',['run','start','--','--hostname','127.0.0.1','--port','3012'],frontend,{PUBLIC_DEMO_MODE:'true',API_BASE_URL:'http://127.0.0.1:8012',API_TOKEN:'isolated-demo-test',ALLOWED_HOSTS:'127.0.0.1:3012,localhost:3012'});
  await ready('http://127.0.0.1:3012');
  const demo=start('node',['scripts/demo-check.mjs'],frontend);
  const demoCode=await new Promise(resolve=>demo.on('exit',resolve));
  assert.equal(demoCode,0,'Public demo workflow failed');
} finally {
  for (const child of children.reverse()) {
    // npm launches a server child; terminate the whole isolated process group.
    try { process.kill(-child.pid,'SIGTERM'); } catch (e) { if(e.code!=='ESRCH') throw e; }
    child.stdout.destroy();
    child.stderr.destroy();
    child.unref();
  }
  await delay(500);
}
