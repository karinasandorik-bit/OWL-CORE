import crypto from 'node:crypto';
import pg from 'pg';
export const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, ssl: process.env.PGSSL === 'disable' ? false : { rejectUnauthorized: true }, max: 4 });
export const sha = s => crypto.createHash('sha256').update(s).digest('hex');
export const canonical = v => {
 if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
 if (v && typeof v === 'object') return '{' + Object.keys(v).sort().map(k => JSON.stringify(k)+':'+canonical(v[k])).join(',') + '}';
 return JSON.stringify(v);
};
export function validSignature(raw, provided) {
 const key = process.env.WITNESS_INGEST_SECRET;
 if (!key || !provided || !/^[0-9a-f]{64}$/.test(provided)) return false;
 const expected = crypto.createHmac('sha256', key).update(raw).digest();
 return crypto.timingSafeEqual(expected, Buffer.from(provided,'hex'));
}
export async function appendLedger(client, kind, eventId, payload) {
 // Same advisory lock shared by all ledger writers, including independent verifier.
 await client.query('SELECT pg_advisory_xact_lock(872145, 1)');
 const prior = await client.query('SELECT entry_hash FROM witness_ledger ORDER BY seq DESC LIMIT 1');
 const previous = prior.rows[0]?.entry_hash ?? 'GENESIS';
 const entryHash = sha(canonical({kind,event_id:eventId,payload,previous_hash:previous}));
 const out = await client.query(
 'INSERT INTO witness_ledger(kind,event_id,payload,previous_hash,entry_hash) VALUES($1,$2,$3::jsonb,$4,$5) RETURNING seq,entry_hash',
 [kind,eventId,JSON.stringify(payload),previous,entryHash]);
 return out.rows[0];
}
export async function withTransaction(fn) {
 const c = await pool.connect();
 try { await c.query('BEGIN'); const result=await fn(c); await c.query('COMMIT'); return result; }
 catch(e){ await c.query('ROLLBACK'); throw e; }
 finally { c.release(); }
}
