import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {sha,canonical,validSignature} from './lib.mjs';
test('canonicalization ignores object key insertion order',()=>{
 assert.equal(canonical({z:1,a:{y:2,x:3}}),canonical({a:{x:3,y:2},z:1}));
});
test('body digest changes when evidence changes',()=>{
 assert.notEqual(sha(canonical({price:1})),sha(canonical({price:2})));
});
test('ingest MAC requires correct exact raw body',()=>{
 const key='local-test-key';process.env.WITNESS_INGEST_SECRET=key;
 const raw='{"event_id":"abc","payload":{"x":1}}';
 const signature=crypto.createHmac('sha256',key).update(raw).digest('hex');
 assert.equal(validSignature(raw,signature),true);
 assert.equal(validSignature(raw+' ',signature),false);
 assert.equal(validSignature(raw,'0'.repeat(64)),false);
 delete process.env.WITNESS_INGEST_SECRET;
});
