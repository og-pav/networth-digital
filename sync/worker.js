/* NetWorth Routine — private sync endpoint.
 *
 * Holds two blobs per user: the routine state, and the calendar snapshot the
 * phone can't get any other way (calendar.json never leaves the Mac, because
 * it carries client names and live Meet links).
 *
 * Auth is a single shared secret sent as X-Sync-Key. It is never stored: the
 * KV key is a SHA-256 of it, so a dump of the namespace does not reveal a
 * working key. That is the appropriate bar for one person syncing their own
 * two devices — it is not multi-user auth and should not be reused as such.
 *
 *   GET  /state     -> {} or the stored state
 *   PUT  /state     -> store (merged client-side; the Worker never merges)
 *   GET  /calendar  -> {} or the stored calendar
 *   PUT  /calendar  -> store
 *   GET  /health    -> {ok:true}
 */

const MAX_BYTES = 2 * 1024 * 1024;   // a decade of days is far under this
const MIN_KEY   = 20;                // reject trivially guessable keys

const CORS = {
  'Access-Control-Allow-Origin':  '*',
  'Access-Control-Allow-Methods': 'GET,PUT,OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type,X-Sync-Key',
  'Access-Control-Max-Age':       '86400',
};

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...CORS },
  });

async function kvKey(secret, slot) {
  const bytes = new TextEncoder().encode(`nwr:v1:${secret}`);
  const hash  = await crypto.subtle.digest('SHA-256', bytes);
  const hex   = [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
  return `${hex}:${slot}`;
}

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });

    const url  = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';

    if (path === '/health') return json({ ok: true });

    const slot = path === '/state' ? 'state' : path === '/calendar' ? 'calendar' : null;
    if (!slot) return json({ error: 'not found' }, 404);

    const secret = request.headers.get('X-Sync-Key') || '';
    if (secret.length < MIN_KEY) return json({ error: 'missing or too-short sync key' }, 401);

    const key = await kvKey(secret, slot);

    if (request.method === 'GET') {
      const stored = await env.ROUTINE.get(key);
      return json(stored ? JSON.parse(stored) : {});
    }

    if (request.method === 'PUT') {
      const body = await request.text();
      if (body.length > MAX_BYTES) return json({ error: 'payload too large' }, 413);
      let parsed;
      try { parsed = JSON.parse(body); }
      catch { return json({ error: 'body is not JSON' }, 400); }
      // Never let an empty or malformed push wipe a good copy.
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed))
        return json({ error: 'body must be a JSON object' }, 400);

      await env.ROUTINE.put(key, body);
      return json({ ok: true, bytes: body.length, at: new Date().toISOString() });
    }

    return json({ error: 'method not allowed' }, 405);
  },
};
