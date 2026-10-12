import http from 'node:http';
import {sha,canonical,validSignature,withTransaction,appendLedger} from './lib.mjs';
const port = Number(process.env.PORT || 3000);
http.createServer(async (req,res)=>{
 const send=(code,body)=>{res.writeHead(code,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(body));};
 if(req.method==='GET' && req.url==='/health') return send(200,{service:'collector',database:'not_checked'});
 if(req.method!=='POST' || req.url!=='/events') return send(404,{error:'not_found'});
 try {
  const chunks=[];let bytes=0;
  for await(const chunk of req){bytes+=chunk.length;if(bytes>65536){send(413,{error:'too_large'});req.destroy();return;}chunks.push(chunk);}
  const raw=Buffer.concat(chunks).toString('utf8');
  if(!validSignature(raw,req.headers['x-witness-signature'])) return send(401,{error:'invalid_signature'});
  const obj=JSON.parse(raw);
  if(!obj||typeof obj!=='object'||typeof obj.event_id!=='string'||typeof obj.source!=='string'||!obj.source||typeof obj.payload!=='object'||obj.payload===null) return send(400,{error:'invalid_schema'});
  if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(obj.event_id)) return send(400,{error:'invalid_uuid'});
  const digest=sha(canonical(obj.payload));
  const result=await withTransaction(async c=>{
   // serialize duplicates and ledger append under one transaction
   await c.query('SELECT pg_advisory_xact_lock(872145, 1)');
   const inserted=await c.query('INSERT INTO witness_events(event_id,source,body,body_sha256) VALUES ($1,$2,$3::jsonb,$4) ON CONFLICT DO NOTHING RETURNING event_id',[obj.event_id,obj.source,JSON.stringify(obj.payload),digest]);
   if(!inserted.rowCount){
    const existing=await c.query('SELECT source,body_sha256 FROM witness_events WHERE event_id=$1',[obj.event_id]);
    if(existing.rows[0]?.body_sha256!==digest||existing.rows[0]?.source!==obj.source) return {conflict:true};
    return {duplicate:true};
   }
   const receipt=await appendLedger(c,'COLLECTED',obj.event_id,{body_sha256:digest,source:obj.source});
   return {duplicate:false,seq:receipt.seq,entry_hash:receipt.entry_hash};
  });
  return send(result.conflict?409:result.duplicate?200:202,result);
 }catch(e){ if(e instanceof SyntaxError)return send(400,{error:'bad_json'});console.error('collector_failure',e.code||e.message);return send(503,{error:'unavailable'}); }
}).listen(port,()=>console.log('collector_listening',port));
