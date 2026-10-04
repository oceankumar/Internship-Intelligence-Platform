import assert from 'node:assert/strict';
import {backendUrl, allowedHost} from '../lib/service-url.ts';
assert.equal(backendUrl({BACKEND_URL:'https://internal/backend/',API_BASE_URL:'http://localhost:8000'}),'https://internal/backend');
assert.equal(backendUrl({API_BASE_URL:'http://localhost:8000'}),'http://localhost:8000');
assert.equal(backendUrl({}),'http://127.0.0.1:8000');
process.env.VERCEL_URL='preview.vercel.app';
assert.equal(allowedHost('preview.vercel.app'),true);
assert.equal(allowedHost('attacker.vercel.app'),false);
console.log('PASS: binding precedence, local fallback and exact generated hostname validation');
