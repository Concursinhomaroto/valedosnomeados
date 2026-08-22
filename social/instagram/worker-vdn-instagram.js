/**
 * vdn-instagram — Bot de publicação automática no Instagram (Vale dos Nomeados)
 *
 * Duas filas independentes, com endpoints e armazenamento separados:
 *   - FEED/REELS: /queue/*        (fila original, sem mudança de comportamento)
 *   - STORIES:    /queue-stories/* (fila nova)
 *
 * Segredos/variáveis necessários (Worker → Settings → Variables and Secrets):
 *   IG_ACCESS_TOKEN   (Segredo) long-lived Instagram User Access Token
 *   IG_USER_ID        (Texto)   ID numérico da conta Instagram Business
 *   ADMIN_KEY         (Segredo) senha simples que só você conhece
 *
 * Binding necessário (Worker → Settings → Bindings → KV Namespace):
 *   IG_QUEUE          namespace KV chamado, por ex., "vdn-instagram-queue"
 *   (as duas filas moram no mesmo namespace, em chaves diferentes: "queue" e "queueStories")
 *
 * Trigger necessário (Worker → Settings → Triggers → Cron Triggers):
 *   uma expressão cron, ex. "0 12,18,23 * * *"
 *   -> a cada disparo, publica o próximo item "approved" mais antigo de CADA fila
 *      (um post/reel de feed + um story, na mesma passada).
 *
 * Endpoints — feed/reels (todos exigem adminKey — no body pra POST, ou querystring pra GET):
 *   GET  /queue                       -> lista todos os itens da fila de feed/reels
 *   POST /queue/add                    { mediaType, imageUrl|videoUrl, caption, kind, adminKey }
 *   POST /queue/approve                { id, adminKey }
 *   POST /queue/reject                 { id, adminKey }
 *   POST /queue/publish-now            { id, adminKey }  -> ignora a fila, publica na hora
 *
 * Endpoints — stories (mesma lógica, sem campo de legenda — Stories não exibem legenda):
 *   GET  /queue-stories                -> lista todos os itens da fila de stories
 *   POST /queue-stories/add            { mediaType, imageUrl|videoUrl, kind, adminKey }
 *   POST /queue-stories/approve        { id, adminKey }
 *   POST /queue-stories/reject         { id, adminKey }
 *   POST /queue-stories/publish-now    { id, adminKey }
 *
 *   GET  /token-info                  ?adminKey=...
 */

const GRAPH = 'https://graph.instagram.com/v21.0';

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
      // ---- fila de feed/reels (original) ----
      if (url.pathname === '/queue' && request.method === 'GET') {
        return await handleListQueue(url, env, cors, 'queue');
      }
      if (url.pathname === '/queue/add' && request.method === 'POST') {
        return await handleAddToQueue(request, env, cors, 'queue', { requireCaption: false });
      }
      if (url.pathname === '/queue/approve' && request.method === 'POST') {
        return await handleSetStatus(request, env, cors, 'approved', 'queue');
      }
      if (url.pathname === '/queue/reject' && request.method === 'POST') {
        return await handleSetStatus(request, env, cors, 'rejected', 'queue');
      }
      if (url.pathname === '/queue/publish-now' && request.method === 'POST') {
        return await handlePublishNow(request, env, cors, 'queue', 'FEED');
      }

      // ---- fila de stories (nova) ----
      if (url.pathname === '/queue-stories' && request.method === 'GET') {
        return await handleListQueue(url, env, cors, 'queueStories');
      }
      if (url.pathname === '/queue-stories/add' && request.method === 'POST') {
        return await handleAddToQueue(request, env, cors, 'queueStories', { requireCaption: false });
      }
      if (url.pathname === '/queue-stories/approve' && request.method === 'POST') {
        return await handleSetStatus(request, env, cors, 'approved', 'queueStories');
      }
      if (url.pathname === '/queue-stories/reject' && request.method === 'POST') {
        return await handleSetStatus(request, env, cors, 'rejected', 'queueStories');
      }
      if (url.pathname === '/queue-stories/publish-now' && request.method === 'POST') {
        return await handlePublishNow(request, env, cors, 'queueStories', 'STORIES');
      }

      if (url.pathname === '/token-info' && request.method === 'GET') {
        return await handleTokenInfo(url, env, cors);
      }
      // Endpoint antigo, mantido pra compatibilidade: publica direto sem passar pela fila.
      if (url.pathname === '/publish' && request.method === 'POST') {
        return await handleDirectPublish(request, env, cors);
      }
      // Teste de publicação de vídeo/Reels (fora da fila — só pra validar o formato).
      if (url.pathname === '/publish-video-test' && request.method === 'POST') {
        return await handlePublishVideoTest(request, env, cors);
      }
      return json({ error: 'not found' }, 404, cors);
    } catch (e) {
      return json({ error: String((e && e.message) || e) }, 500, cors);
    }
  },

  // Cron Trigger: publica o próximo item aprovado mais antigo de CADA fila
  // (um de feed/reels + um de stories, a cada disparo).
  async scheduled(event, env, ctx) {
    ctx.waitUntil(publishNextApproved(env, 'queue', 'FEED'));
    ctx.waitUntil(publishNextApproved(env, 'queueStories', 'STORIES'));
  },
};

/* ---------- helpers ---------- */

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json', ...cors },
  });
}
function checkAdmin(key, env) {
  return !!env.ADMIN_KEY && key === env.ADMIN_KEY;
}
async function loadQueue(env, key) {
  const raw = await env.IG_QUEUE.get(key);
  return raw ? JSON.parse(raw) : [];
}
async function saveQueue(env, key, queue) {
  await env.IG_QUEUE.put(key, JSON.stringify(queue));
}
function newId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

/* ---------- fila (genérico — usado tanto pra feed/reels quanto pra stories) ---------- */

async function handleListQueue(url, env, cors, kvKey) {
  if (!checkAdmin(url.searchParams.get('adminKey'), env)) return json({ error: 'não autorizado' }, 401, cors);
  const queue = await loadQueue(env, kvKey);
  return json({ ok: true, queue }, 200, cors);
}

async function handleAddToQueue(request, env, cors, kvKey) {
  const body = await request.json().catch(() => ({}));
  if (!checkAdmin(body.adminKey, env)) return json({ error: 'não autorizado' }, 401, cors);
  const mediaType = body.mediaType === 'VIDEO' ? 'VIDEO' : 'IMAGE'; // default IMAGE, compatibilidade com a fila antiga
  const mediaUrl = mediaType === 'VIDEO' ? body.videoUrl : body.imageUrl;
  if (!mediaUrl) return json({ error: mediaType === 'VIDEO' ? 'videoUrl é obrigatório' : 'imageUrl é obrigatório' }, 400, cors);
  const queue = await loadQueue(env, kvKey);
  const item = {
    id: newId(),
    mediaType,
    imageUrl: mediaType === 'IMAGE' ? mediaUrl : undefined, // mantém o nome antigo pra não quebrar o admin.html já publicado
    videoUrl: mediaType === 'VIDEO' ? mediaUrl : undefined,
    // Legenda só faz sentido pra feed/reels — o Instagram não exibe legenda em Stories,
    // então esse campo fica de fora do formulário de stories, mas ainda é aceito aqui
    // (fica só guardado, sem efeito) caso venha preenchido por engano.
    caption: body.caption || '',
    kind: body.kind || '',
    status: 'pending', // pending -> approved -> published (ou rejected/failed)
    createdAt: new Date().toISOString(),
  };
  queue.push(item);
  await saveQueue(env, kvKey, queue);
  return json({ ok: true, item }, 200, cors);
}

async function handleSetStatus(request, env, cors, status, kvKey) {
  const body = await request.json().catch(() => ({}));
  if (!checkAdmin(body.adminKey, env)) return json({ error: 'não autorizado' }, 401, cors);
  const queue = await loadQueue(env, kvKey);
  const item = queue.find((q) => q.id === body.id);
  if (!item) return json({ error: 'item não encontrado' }, 404, cors);
  item.status = status;
  await saveQueue(env, kvKey, queue);
  return json({ ok: true, item }, 200, cors);
}

async function handlePublishNow(request, env, cors, kvKey, target) {
  const body = await request.json().catch(() => ({}));
  if (!checkAdmin(body.adminKey, env)) return json({ error: 'não autorizado' }, 401, cors);
  const queue = await loadQueue(env, kvKey);
  const item = queue.find((q) => q.id === body.id);
  if (!item) return json({ error: 'item não encontrado' }, 404, cors);
  const result = await publishItem(item, env, target);
  if (!result.ok) return json(result, 502, cors);
  item.status = 'published';
  item.mediaId = result.mediaId;
  item.publishedAt = new Date().toISOString();
  await saveQueue(env, kvKey, queue);
  return json({ ok: true, item }, 200, cors);
}

async function publishNextApproved(env, kvKey, target) {
  const queue = await loadQueue(env, kvKey);
  const approved = queue
    .filter((q) => q.status === 'approved')
    .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
  const next = approved[0];
  if (!next) return { ok: false, reason: `fila "${kvKey}" de aprovados vazia` };
  const result = await publishItem(next, env, target);
  if (result.ok) {
    next.status = 'published';
    next.mediaId = result.mediaId;
    next.publishedAt = new Date().toISOString();
    await saveQueue(env, kvKey, queue);
  } else {
    next.status = 'failed';
    next.lastError = result;
    await saveQueue(env, kvKey, queue);
  }
  return result;
}

/* ---------- publicação (Instagram Graph API) ---------- */

// target: 'FEED' (foto normal) | 'REELS' (definido automaticamente pra vídeo) | 'STORIES'
async function publishItem(item, env, target) {
  if (!env.IG_ACCESS_TOKEN || !env.IG_USER_ID) {
    return { ok: false, error: 'Worker sem IG_ACCESS_TOKEN / IG_USER_ID configurados' };
  }
  const isVideo = item.mediaType === 'VIDEO';
  const isStory = target === 'STORIES';

  const createBody = { access_token: env.IG_ACCESS_TOKEN };
  if (isVideo) {
    createBody.video_url = item.videoUrl;
    createBody.media_type = isStory ? 'STORIES' : 'REELS';
  } else {
    createBody.image_url = item.imageUrl;
    if (isStory) createBody.media_type = 'STORIES';
  }
  // Stories não exibem legenda no Instagram — não envia esse campo nesse caso
  // (evita depender de comportamento não documentado da API pra um campo inútil ali).
  if (!isStory) createBody.caption = item.caption || '';

  const createRes = await fetch(`${GRAPH}/${env.IG_USER_ID}/media`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(createBody),
  });
  const createData = await createRes.json();
  if (!createRes.ok || !createData.id) {
    return { ok: false, error: 'falha ao criar container', detail: createData };
  }

  // Vídeo demora bem mais pra processar que imagem — espera bem mais tempo pra ele.
  const ready = isVideo
    ? await waitUntilFinished(createData.id, env.IG_ACCESS_TOKEN, { attempts: 60, intervalMs: 3000 })
    : await waitUntilFinished(createData.id, env.IG_ACCESS_TOKEN);
  if (!ready.ok) {
    return { ok: false, error: 'mídia não ficou pronta a tempo', detail: ready };
  }

  const publishRes = await fetch(`${GRAPH}/${env.IG_USER_ID}/media_publish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ creation_id: createData.id, access_token: env.IG_ACCESS_TOKEN }),
  });
  const publishData = await publishRes.json();
  if (!publishRes.ok || !publishData.id) {
    return { ok: false, error: 'falha ao publicar', detail: publishData };
  }
  return { ok: true, mediaId: publishData.id };
}

async function waitUntilFinished(creationId, accessToken, opts) {
  const attempts = (opts && opts.attempts) || 15;
  const intervalMs = (opts && opts.intervalMs) || 2000;
  for (let i = 0; i < attempts; i++) {
    const res = await fetch(`${GRAPH}/${creationId}?fields=status_code&access_token=${encodeURIComponent(accessToken)}`);
    const data = await res.json();
    if (data.status_code === 'FINISHED') return { ok: true };
    if (data.status_code === 'ERROR') return { ok: false, reason: 'status ERROR', detail: data };
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return { ok: false, reason: `timeout depois de ${(attempts * intervalMs) / 1000}s` };
}

// Publica vídeo/Reels fora da fila — útil pra teste avulso. Reusa publishItem().
async function handlePublishVideoTest(request, env, cors) {
  const body = await request.json().catch(() => ({}));
  if (!checkAdmin(body.adminKey, env)) return json({ error: 'não autorizado' }, 401, cors);
  if (!body.videoUrl) return json({ error: 'videoUrl é obrigatório' }, 400, cors);
  const result = await publishItem({ mediaType: 'VIDEO', videoUrl: body.videoUrl, caption: body.caption || '' }, env, 'REELS');
  return json(result, result.ok ? 200 : 502, cors);
}

async function handleDirectPublish(request, env, cors) {
  const body = await request.json().catch(() => ({}));
  if (!checkAdmin(body.adminKey, env)) return json({ error: 'não autorizado' }, 401, cors);
  if (!body.imageUrl) return json({ error: 'imageUrl é obrigatório' }, 400, cors);
  const result = await publishItem({ imageUrl: body.imageUrl, caption: body.caption || '' }, env, 'FEED');
  return json(result, result.ok ? 200 : 502, cors);
}

async function handleTokenInfo(url, env, cors) {
  if (!checkAdmin(url.searchParams.get('adminKey'), env)) return json({ error: 'não autorizado' }, 401, cors);
  const res = await fetch(`${GRAPH}/me?fields=id,username,account_type&access_token=${encodeURIComponent(env.IG_ACCESS_TOKEN || '')}`);
  const data = await res.json();
  return json({ ok: res.ok, data }, res.ok ? 200 : 502, cors);
}
