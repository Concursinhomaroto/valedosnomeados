/**
 * vdn-tiktok — Bot de publicação no TikTok (Vale dos Nomeados), Content Posting API.
 *
 * Segredos necessários (Worker → Settings → Variables and Secrets):
 *   TIKTOK_CLIENT_KEY     (Texto)   client key do app TikTok for Developers
 *   TIKTOK_CLIENT_SECRET  (Segredo) client secret do app
 *   ADMIN_KEY             (Segredo) senha sua, protege os endpoints administrativos
 *
 * Binding necessário (Worker → Settings → Bindings → KV Namespace):
 *   TT_KV   namespace KV pra guardar o code_verifier (PKCE) durante o login e
 *           depois o access_token/refresh_token de longa duração
 *
 * Fluxo (OAuth 2.0 + PKCE, exigido pelo TikTok):
 *   1) GET /auth?adminKey=...          -> redireciona pro login do TikTok
 *   2) TikTok redireciona de volta pro /callback com ?code=...&state=...
 *   3) /callback troca o code por access_token + refresh_token, salva no KV
 *   4) GET  /creator-info?adminKey=... -> consulta conta logada (obrigatório
 *      pela TikTok ANTES de mostrar qualquer opção de publicação pro usuário —
 *      é o que a revisão deles checa: nada de nível de privacidade "chumbado"
 *      no código, tem que vir dessa consulta e a pessoa escolhe na hora)
 *   5) POST /publish-video-test        -> publica um vídeo
 *   6) GET  /status?adminKey=...&publishId=... -> acompanha o status
 *
 * IMPORTANTE: enquanto o app não passar pela revisão da TikTok, QUALQUER post
 * sai forçado como privado (SELF_ONLY) pelo lado da própria TikTok, não
 * importa o que a gente mande — é a regra deles pra apps não auditados. Por
 * isso é seguro deixar a pessoa escolher o nível de privacidade de verdade na
 * tela (em vez de travar SELF_ONLY no código): é exatamente isso que o vídeo
 * de revisão precisa mostrar.
 */

const REDIRECT_PATH = '/callback';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const cors = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };
    if (request.method === 'OPTIONS') return new Response(null, { headers: cors });

    try {
      if (url.pathname === '/auth' && request.method === 'GET') {
        return await handleAuthStart(url, env);
      }
      if (url.pathname === REDIRECT_PATH && request.method === 'GET') {
        return await handleCallback(url, env, cors);
      }
      if (url.pathname === '/creator-info' && request.method === 'GET') {
        return await handleCreatorInfo(url, env, cors);
      }
      if (url.pathname === '/publish-video-test' && request.method === 'POST') {
        return await handlePublishTest(request, env, cors);
      }
      if (url.pathname === '/status' && request.method === 'GET') {
        return await handleStatus(url, env, cors);
      }
      return json({ error: 'not found' }, 404, cors);
    } catch (e) {
      return json({ error: String((e && e.message) || e) }, 500, cors);
    }
  },
};

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json', ...(cors || {}) },
  });
}
function checkAdmin(key, env) {
  return !!env.ADMIN_KEY && key === env.ADMIN_KEY;
}
function redirectUri(url) {
  return `${url.protocol}//${url.host}${REDIRECT_PATH}`;
}

/* ---------- PKCE helpers ---------- */
function randomString(len) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let out = '';
  const bytes = crypto.getRandomValues(new Uint8Array(len));
  for (let i = 0; i < len; i++) out += chars[bytes[i] % chars.length];
  return out;
}
async function sha256Base64Url(input) {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest('SHA-256', data);
  let str = String.fromCharCode(...new Uint8Array(digest));
  return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/* ---------- /auth ---------- */
async function handleAuthStart(url, env) {
  if (!checkAdmin(url.searchParams.get('adminKey'), env)) return json({ error: 'não autorizado' }, 401);
  const codeVerifier = randomString(64);
  const codeChallenge = await sha256Base64Url(codeVerifier);
  const state = randomString(24);

  await env.TT_KV.put(`pkce:${state}`, codeVerifier, { expirationTtl: 600 }); // 10 min pra completar o login

  const authorizeUrl = new URL('https://www.tiktok.com/v2/auth/authorize/');
  authorizeUrl.searchParams.set('client_key', env.TIKTOK_CLIENT_KEY);
  authorizeUrl.searchParams.set('scope', 'video.publish,video.upload');
  authorizeUrl.searchParams.set('response_type', 'code');
  authorizeUrl.searchParams.set('redirect_uri', redirectUri(url));
  authorizeUrl.searchParams.set('state', state);
  authorizeUrl.searchParams.set('code_challenge', codeChallenge);
  authorizeUrl.searchParams.set('code_challenge_method', 'S256');

  return Response.redirect(authorizeUrl.toString(), 302);
}

/* ---------- /callback ---------- */
async function handleCallback(url, env, cors) {
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const error = url.searchParams.get('error');
  if (error) return json({ error, detail: url.searchParams.get('error_description') }, 400, cors);
  if (!code || !state) return json({ error: 'faltou code ou state' }, 400, cors);

  const codeVerifier = await env.TT_KV.get(`pkce:${state}`);
  if (!codeVerifier) return json({ error: 'state inválido ou expirado — tenta /auth de novo' }, 400, cors);

  const body = new URLSearchParams({
    client_key: env.TIKTOK_CLIENT_KEY,
    client_secret: env.TIKTOK_CLIENT_SECRET,
    code,
    grant_type: 'authorization_code',
    redirect_uri: redirectUri(url),
    code_verifier: codeVerifier,
  });

  const res = await fetch('https://open.tiktokapis.com/v2/oauth/token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Cache-Control': 'no-cache' },
    body: body.toString(),
  });
  const data = await res.json();
  if (!res.ok || !data.access_token) {
    return json({ error: 'falha ao trocar code por token', detail: data }, 502, cors);
  }

  await env.TT_KV.put('access_token', data.access_token);
  await env.TT_KV.put('refresh_token', data.refresh_token);
  await env.TT_KV.put('open_id', data.open_id);
  await env.TT_KV.delete(`pkce:${state}`);

  return new Response(
    `<h2>Login concluído!</h2><p>open_id: ${data.open_id}</p><p>Pode fechar essa aba e voltar pro chat.</p>`,
    { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
  );
}

/* ---------- /creator-info ---------- */
async function handleCreatorInfo(url, env, cors) {
  if (!checkAdmin(url.searchParams.get('adminKey'), env)) return json({ error: 'não autorizado' }, 401, cors);
  const accessToken = await env.TT_KV.get('access_token');
  if (!accessToken) return json({ error: 'ainda não logou — visita /auth?adminKey=... primeiro' }, 400, cors);

  const res = await fetch('https://open.tiktokapis.com/v2/post/publish/creator_info/query/', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json; charset=UTF-8' },
  });
  const data = await res.json();
  if (!res.ok || data?.error?.code !== 'ok') {
    return json({ error: 'falha ao consultar creator info', detail: data }, 502, cors);
  }
  return json({ ok: true, creator: data.data }, 200, cors);
}

/* ---------- publicação ---------- */
async function handlePublishTest(request, env, cors) {
  const body = await request.json().catch(() => ({}));
  if (!checkAdmin(body.adminKey, env)) return json({ error: 'não autorizado' }, 401, cors);
  if (!body.videoUrl) return json({ error: 'videoUrl é obrigatório' }, 400, cors);
  if (!body.privacyLevel) return json({ error: 'privacyLevel é obrigatório — consulta /creator-info e deixa a pessoa escolher' }, 400, cors);

  const accessToken = await env.TT_KV.get('access_token');
  if (!accessToken) return json({ error: 'ainda não logou — visita /auth?adminKey=... primeiro' }, 400, cors);

  const initRes = await fetch('https://open.tiktokapis.com/v2/post/publish/video/init/', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      post_info: {
        title: body.caption || '',
        privacy_level: body.privacyLevel,
        disable_duet: !!body.disableDuet,
        disable_comment: !!body.disableComment,
        disable_stitch: !!body.disableStitch,
        video_cover_timestamp_ms: 1000,
      },
      source_info: {
        source: 'PULL_FROM_URL',
        video_url: body.videoUrl,
      },
    }),
  });
  const initData = await initRes.json();
  if (!initRes.ok || initData?.error?.code !== 'ok') {
    return json({ error: 'falha ao iniciar publicação', detail: initData }, 502, cors);
  }

  return json({ ok: true, publishId: initData.data.publish_id, raw: initData }, 200, cors);
}

async function handleStatus(url, env, cors) {
  if (!checkAdmin(url.searchParams.get('adminKey'), env)) return json({ error: 'não autorizado' }, 401, cors);
  const publishId = url.searchParams.get('publishId');
  if (!publishId) return json({ error: 'publishId é obrigatório' }, 400, cors);
  const accessToken = await env.TT_KV.get('access_token');
  const res = await fetch('https://open.tiktokapis.com/v2/post/publish/status/fetch/', {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ publish_id: publishId }),
  });
  const data = await res.json();
  return json(data, res.ok ? 200 : 502, cors);
}
