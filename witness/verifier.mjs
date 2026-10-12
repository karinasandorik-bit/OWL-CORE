import {pool,sha,canonical,withTransaction,appendLedger} from './lib.mjs';
// Run as an independent worker with read access to evidence and insert-only ledger permissions.
// Re-hashing detects corruption or mismatch, NOT truth of an external provider's claim.
async function run(){
 const rows=await pool.query(`SELECT event_id,source,body,body_sha256 FROM witness_events e
 WHERE NOT EXISTS (SELECT 1 FROM witness_ledger l WHERE l.event_id=e.event_id AND l.kind IN ('VERIFIED','REJECTED'))
 ORDER BY received_at LIMIT 100`);
 for(const event of rows.rows){
  await withTransaction(async c=>{
   await c.query('SELECT pg_advisory_xact_lock(872145, 1)');
   const already=await c.query("SELECT 1 FROM witness_ledger WHERE event_id=$1 AND kind IN ('VERIFIED','REJECTED')",[event.event_id]);
   if(already.rowCount)return;
   const valid=sha(canonical(event.body))===event.body_sha256;
   await appendLedger(c,valid?'VERIFIED':'REJECTED',event.event_id,{check:'body_digest',digest:sha(canonical(event.body)),validator:'witness-verifier-v1'});
  });
 }
 const ledger=await pool.query('SELECT seq,kind,event_id,payload,previous_hash,entry_hash FROM witness_ledger ORDER BY seq ASC');
 let previous='GENESIS',broken=0;
 for(const row of ledger.rows){
  const expected=sha(canonical({kind:row.kind,event_id:row.event_id,payload:row.payload,previous_hash:previous}));
  if(row.previous_hash!==previous||row.entry_hash!==expected)broken++;
  previous=row.entry_hash;
 }
 console.log(JSON.stringify({checked:ledger.rowCount,broken,head:previous}));
 if(broken)process.exitCode=2;
}
run().catch(e=>{console.error(e.code||e.message);process.exitCode=1}).finally(()=>pool.end());
