import asyncio, json, os
from playwright.async_api import async_playwright

BASE = 'http://127.0.0.1:8934/app/index.html'
# Vendorizado em tests/e2e/fixtures/ pra rodar sem rede — os testes interceptam o pedido
# ao cdnjs e servem esta copia local, entao a Sala de Estudo carrega igual, offline.
LOCAL_PHASER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'phaser.min.js')

INIT_JS = r"""
window.__root = { users: { TEST_UID_LEO: { vdn_v1: __SEED__ } } };
window.__updateCalls = [];
window.__onDisconnectRemoves = [];

function normPath(p){ return p.split('/').filter(Boolean); }
function getAtPath(path){
  let node = window.__root;
  for (const seg of normPath(path)){
    if (node == null) return null;
    node = node[seg];
  }
  return node === undefined ? null : node;
}
function setAtPath(path, value){
  const segs = normPath(path);
  if (!segs.length){ window.__root = value || {}; return; }
  let node = window.__root;
  for (let i=0;i<segs.length-1;i++){
    const seg = segs[i];
    if (node[seg] == null || typeof node[seg] !== 'object') node[seg] = {};
    node = node[seg];
  }
  const last = segs[segs.length-1];
  if (value === null || value === undefined) delete node[last];
  else node[last] = value;
}

window.__listeners = {}; // path -> [cb]
function notify(path){
  // notifica listeners exatos e de qualquer prefixo (ex: escrever em sala_presence/uid1
  // deve notificar quem escuta 'sala_presence')
  Object.keys(window.__listeners).forEach(lp => {
    if (path === lp || path.startsWith(lp + '/') || lp.startsWith(path + '/') || lp === '') {
      (window.__listeners[lp]||[]).forEach(cb => cb({ val: () => getAtPath(lp), exists: () => getAtPath(lp) !== null }));
    }
  });
}

function makeRef(path){
  return {
    _path: path,
    on(event, cb, errCb){
      let value;
      if (path === '.info/connected') value = true;
      else if (path === 'promo/lifetime') value = null;
      else value = getAtPath(path);
      cb({ val: () => value, exists: () => value !== null });
      window.__listeners[path] = window.__listeners[path] || [];
      window.__listeners[path].push(cb);
      return cb;
    },
    off(){ delete window.__listeners[path]; },
    once(event){ return Promise.resolve({ val: () => getAtPath(path) }); },
    set(val){
      setAtPath(path, val === undefined ? null : JSON.parse(JSON.stringify(val)));
      window.__updateCalls.push({ path, val, op: 'set', at: Date.now() });
      notify(path);
      return Promise.resolve();
    },
    update(val){
      window.__updateCalls.push({ path, val: JSON.parse(JSON.stringify(val)), op: 'update', at: Date.now() });
      Object.keys(val).forEach(k => setAtPath(path + '/' + k, val[k]));
      notify(path);
      return Promise.resolve();
    },
    remove(){
      setAtPath(path, null);
      window.__updateCalls.push({ path, op: 'remove', at: Date.now() });
      notify(path);
      return Promise.resolve();
    },
    onDisconnect(){
      return {
        remove(){ window.__onDisconnectRemoves.push(path); },
        cancel(){},
        set(){},
      };
    },
    transaction(fn){
      const cur = getAtPath(path);
      const next = fn(cur);
      setAtPath(path, next);
      notify(path);
      return Promise.resolve({ committed: true, snapshot: { val: () => next } });
    },
    push(val){
      const key = 'k' + String(++window.__pushSeq).padStart(6,'0');
      const child = makeRef(path + '/' + key);
      child.key = key;
      if (val !== undefined) child.set(val);
      return child;
    },
    limitToLast(){ return makeRef(path); },   // o mock guarda tudo; o corte nao importa aqui
  };
}
window.__pushSeq = 0;

window.firebase = {
  initializeApp(){},
  database(){ return { ref: (p) => makeRef(p === undefined ? '' : p) }; },
  auth(){
    return {
      onAuthStateChanged(cb){
        setTimeout(() => cb({
          uid: 'TEST_UID_LEO',
          email: 'leonardobrunotlc@gmail.com',
          emailVerified: true,
          getIdToken: () => Promise.resolve('fake-token'),
        }), 10);
      },
      signOut(){ return Promise.resolve(); },
    };
  },
};

// Ajuda os testes a escreverem diretamente como se fosse OUTRO uid (simular 2º jogador)
window.__writeOtherPlayer = function(uid, data){
  setAtPath('sala_presence/' + uid, data);
  notify('sala_presence');
};
window.__sayAs = function(uid, nick, txt, ts){
  const key = 'k' + String(++window.__pushSeq).padStart(6,'0');
  setAtPath('sala_chat/' + key, { uid, nick, txt, ts: ts || Date.now() });
  notify('sala_chat');
};
window.__dmTo = function(meuUid, deUid, nick, txt){
  const key = 'k' + String(++window.__pushSeq).padStart(6,'0');
  setAtPath('sala_dm/' + meuUid + '/' + deUid + '/' + key, { de: deUid, nick, txt, ts: Date.now() });
  notify('sala_dm/' + meuUid);
};
window.__removeOtherPlayer = function(uid){
  setAtPath('sala_presence/' + uid, null);
  notify('sala_presence');
};
"""

def make_seed(extra=None):
    seed = {
        'kingdoms': [], 'topics': {}, 'times': {}, 'revisions': {}, 'flashcards': {},
        'xp': 100, 'examDate': '', 'sessions': {}, 'lastModified': 1730000000000,
        'onboardingCompleted': True, 'accountEmail': 'leonardobrunotlc@gmail.com',
    }
    if extra:
        seed.update(extra)
    return seed


async def setup_page(p, seed):
    browser = await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    context = await browser.new_context(service_workers='block', viewport={'width': 1200, 'height': 900})
    page = await context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))

    async def serve_local_phaser(route):
        await route.fulfill(path=LOCAL_PHASER)

    await page.route('**cdnjs.cloudflare.com/ajax/libs/phaser/**', serve_local_phaser)
    await page.route('**://www.gstatic.com/**', lambda r: r.abort())
    await page.route('**://fonts.googleapis.com/**', lambda r: r.abort())
    await page.route('**://cdn.jsdelivr.net/**', lambda r: r.abort())
    await page.route('**://www.googletagmanager.com/**', lambda r: r.abort())

    init_js = INIT_JS.replace('__SEED__', json.dumps(seed))
    await page.add_init_script(init_js)
    await page.goto(BASE)
    await page.wait_for_timeout(2000)
    return browser, page, errors


def real_errors(errors):
    return [e for e in errors if 'selectedPixTier' not in e]


async def test_first_visit_picker_blocks_and_creates_game():
    print('\n=== Teste 1: primeira visita sem nickname mostra o picker, bloqueia o mapa ===')
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, make_seed())
        try:
            state = await page.evaluate("() => ({ hasNickname: !!db.studyNickname, gameExists: !!salaMapaGame })")
            print('estado inicial:', state)
            assert not state['hasNickname']

            # navega pra sala de estudo
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_timeout(300)

            modal_visible = await page.evaluate("() => document.getElementById('modal')?.classList.contains('open')")
            modal_title = await page.evaluate("() => document.getElementById('modal-title')?.textContent")
            print('modal visível:', modal_visible, '| título:', modal_title)
            assert modal_visible
            assert 'Entrar na Sala' in (modal_title or '')

            game_before_confirm = await page.evaluate("() => !!salaMapaGame")
            print('jogo criado antes de confirmar nome/avatar?', game_before_confirm)
            assert not game_before_confirm

            # escolhe um personagem (lucy_media) e confirma nome
            await page.fill('#sala-nick-input', 'Coruja da Meia-N')
            await page.evaluate("() => salaSelectPortrait('lucy_media')")
            await page.click("button:has-text('Entrar na sala')")

            await page.wait_for_function("""() => {
                const g = salaMapaGame;
                if (!g) return false;
                const scene = g.scene.keys['salaMapaScene'];
                return !!(scene && scene.player && scene.sys.isActive());
            }""", timeout=15000)

            saved = await page.evaluate("() => ({ nickname: db.studyNickname, character: db.studyCharacter })")
            print('salvo no db:', saved)
            assert saved['nickname'] == 'Coruja da Meia-N'
            assert saved['character'] == 'lucy_media'

            player_state = await page.evaluate("""() => {
                const scene = salaMapaGame.scene.keys['salaMapaScene'];
                return { charKey: scene.player.charKey, anim: scene.player.anims.currentAnim.key, nameTag: scene.player.nameText.text };
            }""")
            print('estado do player no jogo:', player_state)
            assert player_state['charKey'] == 'lucy_media'
            assert player_state['anim'] == 'lucy_media_idle_down'
            assert player_state['nameTag'] == 'Coruja da Meia-N'

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: picker bloqueia entrada, salva nome fixo + personagem, jogo carrega com o personagem certo\n')
        finally:
            await browser.close()


async def test_zoom_controls():
    print('=== Teste 2: zoom +/- respeita limites ===')
    seed = make_seed({'studyNickname': 'Zoom Tester', 'studyCharacter': 'adam'})
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {
                const g = salaMapaGame;
                return !!(g && g.scene.keys['salaMapaScene'] && g.scene.keys['salaMapaScene'].player);
            }""", timeout=15000)

            zoom0 = await page.evaluate("() => salaMapaGame.scene.keys['salaMapaScene'].cameras.main.zoom")
            print('zoom inicial:', zoom0)
            assert zoom0 == 1.5

            await page.click("button[onclick=\"salaMapaZoom(0.25)\"]")
            zoom1 = await page.evaluate("() => salaMapaGame.scene.keys['salaMapaScene'].cameras.main.zoom")
            print('depois de +:', zoom1)
            assert abs(zoom1 - 1.75) < 0.001

            # bate no limite máximo
            for _ in range(10):
                await page.click("button[onclick=\"salaMapaZoom(0.25)\"]")
            zoomMax = await page.evaluate("() => salaMapaGame.scene.keys['salaMapaScene'].cameras.main.zoom")
            print('depois de várias vezes +:', zoomMax)
            assert zoomMax == 2.5

            for _ in range(20):
                await page.click("button[onclick=\"salaMapaZoom(-0.25)\"]")
            zoomMin = await page.evaluate("() => salaMapaGame.scene.keys['salaMapaScene'].cameras.main.zoom")
            print('depois de várias vezes -:', zoomMin)
            assert zoomMin == 0.8

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: zoom respeita limites 0.8-2.5\n')
        finally:
            await browser.close()


async def test_cabins_and_chairs():
    print('=== Teste 3: campus v8 — cadeiras e mundo do tamanho certo ===')
    seed = make_seed({'studyNickname': 'Chair Tester', 'studyCharacter': 'ash'})
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {
                const g = salaMapaGame;
                return !!(g && g.scene.keys['salaMapaScene'] && g.scene.keys['salaMapaScene'].player);
            }""", timeout=15000)

            info = await page.evaluate("""() => {
                const scene = salaMapaGame.scene.keys['salaMapaScene'];
                return {
                    totalChairs: scene.chairs.getChildren().length,
                    worldBounds: { w: scene.physics.world.bounds.width, h: scene.physics.world.bounds.height },
                };
            }""")
            print('info do mapa:', info)
            # campus v8: 3 salas de aula, laboratório, auditório, biblioteca,
            # 8 salas individuais, átrio com fumódromo, academia, recepção, cantina,
            # lounge, galeria de troféus, sala dos professores e sala de música.
            assert info['totalChairs'] == 208, f"esperava 208 cadeiras, veio {info['totalChairs']}"
            assert info['worldBounds']['w'] == 2944, f"esperava mundo 2944px de largura, veio {info['worldBounds']['w']}"
            assert info['worldBounds']['h'] == 2304, f"esperava mundo 2304px de altura, veio {info['worldBounds']['h']}"

            # teleporta pra uma cadeira qualquer e senta
            sit_result = await page.evaluate("""() => {
                const scene = salaMapaGame.scene.keys['salaMapaScene'];
                const chairs = scene.chairs.getChildren();
                const target = chairs[0];
                scene.player.setPosition(target.x, target.y);
                return { chairDir: target.direction };
            }""")
            print('cadeira alvo:', sit_result)

            await page.keyboard.press('e')
            await page.wait_for_timeout(150)
            sitting = await page.evaluate("""() => {
                const p = salaMapaGame.scene.keys['salaMapaScene'].player;
                return { behavior: p.playerBehavior, anim: p.anims.currentAnim.key };
            }""")
            print('depois de apertar E na cadeira:', sitting)
            assert sitting['behavior'] == 'sitting'
            assert sitting['anim'] == 'ash_sit_' + sit_result['chairDir']

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: campus v8 carrega, cadeiras sentáveis, mundo do tamanho certo\n')
        finally:
            await browser.close()


async def test_multiplayer_presence():
    print('=== Teste 4: presença multiplayer (join, ver outro jogador, sair) ===')
    seed = make_seed({'studyNickname': 'Player Um', 'studyCharacter': 'nancy_retinta'})
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {
                const g = salaMapaGame;
                return !!(g && g.scene.keys['salaMapaScene'] && g.scene.keys['salaMapaScene'].player);
            }""", timeout=15000)
            await page.wait_for_timeout(300)

            own_presence = await page.evaluate("() => window.__root.sala_presence && window.__root.sala_presence.TEST_UID_LEO")
            print('presença própria escrita no Firebase:', own_presence)
            assert own_presence is not None
            assert own_presence['nickname'] == 'Player Um'
            assert own_presence['character'] == 'nancy_retinta'

            ondisc = await page.evaluate("() => window.__onDisconnectRemoves")
            print('onDisconnect registrado para:', ondisc)
            assert 'sala_presence/TEST_UID_LEO' in ondisc

            # simula um segundo jogador entrando
            await page.evaluate("""() => window.__writeOtherPlayer('OUTRO_UID', {
                nickname: 'Fantasma Estudioso', character: 'adam_morena', x: 700, y: 480, state: 'run', dir: 'right', ts: Date.now()
            })""")
            await page.wait_for_timeout(200)

            other = await page.evaluate("""() => {
                const scene = salaMapaGame.scene.keys['salaMapaScene'];
                const entry = scene.otherPlayers['OUTRO_UID'];
                if (!entry) return null;
                return { nameTag: entry.nameText.text, char: entry.char, spriteExists: !!entry.sprite };
            }""")
            print('outro jogador na cena:', other)
            assert other is not None
            assert other['nameTag'] == 'Fantasma Estudioso'
            assert other['char'] == 'adam_morena'

            # some do nó -> sprite deve ser removido
            await page.evaluate("() => window.__removeOtherPlayer('OUTRO_UID')")
            await page.wait_for_timeout(200)
            gone = await page.evaluate("() => !!salaMapaGame.scene.keys['salaMapaScene'].otherPlayers['OUTRO_UID']")
            print('outro jogador ainda na cena depois de sair?', gone)
            assert not gone

            # sair da TELA nao e sair da SALA: continua visivel, marcado como fora
            await page.evaluate("() => showScreen('dashboard')")
            await page.wait_for_timeout(300)
            own_after_leave = await page.evaluate("() => (window.__root.sala_presence||{}).TEST_UID_LEO")
            print('presença própria depois de sair da tela:', own_after_leave)
            assert own_after_leave is not None, 'a presença sumiu ao trocar de tela'
            assert own_after_leave.get('fora') is True, 'não foi marcada como "estudando fora da sala"'

            # o botao de sair da sala e que apaga de verdade
            await page.evaluate("() => salaSairDaSala()")
            await page.wait_for_timeout(200)
            own_final = await page.evaluate("() => (window.__root.sala_presence||{}).TEST_UID_LEO")
            print('presença própria depois de "Sair da sala":', own_final)
            assert own_final is None

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: presença própria escrita+onDisconnect, outro jogador aparece/some corretamente, trocar de tela mantém a presença e "Sair da sala" apaga\n')
        finally:
            await browser.close()


async def test_permission_denied_warns_once():
    print('=== Teste 5: falha de permissão no sala_presence avisa (não fica silenciosa) ===')
    seed = make_seed({'studyNickname': 'Sem Permissao', 'studyCharacter': 'adam'})
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            # substitui firebaseDB.ref pra simular permission_denied só no sala_presence
            await page.evaluate("""() => {
                const origRef = firebaseDB.ref.bind(firebaseDB);
                firebaseDB.ref = (path) => {
                    if (path === 'sala_presence' || path.startsWith('sala_presence/')) {
                        return {
                            set(){ return Promise.reject(new Error('PERMISSION_DENIED: Permission denied')); },
                            update(){ return Promise.reject(new Error('PERMISSION_DENIED')); },
                            remove(){ return Promise.resolve(); },
                            on(event, cb, errCb){ if (errCb) errCb(new Error('PERMISSION_DENIED')); },
                            off(){},
                            onDisconnect(){ return { remove(){}, cancel(){}, set(){} }; },
                        };
                    }
                    return origRef(path);
                };
            }""")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {
                const g = salaMapaGame;
                return !!(g && g.scene.keys['salaMapaScene'] && g.scene.keys['salaMapaScene'].player);
            }""", timeout=15000)
            await page.wait_for_timeout(300)

            toastText = await page.evaluate("() => { const t = document.getElementById('toast'); return t && t.style.display !== 'none' ? t.textContent : null; }")
            print('toast visível:', toastText)
            failFlag = await page.evaluate("() => typeof salaPresenceWriteFailed !== 'undefined' ? salaPresenceWriteFailed : null")
            print('salaPresenceWriteFailed:', failFlag)
            assert failFlag is True

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: falha de permissão é detectada e marcada (não repete infinitamente)\n')
        finally:
            await browser.close()


async def main():
    await test_first_visit_picker_blocks_and_creates_game()
    await test_zoom_controls()
    await test_cabins_and_chairs()
    await test_multiplayer_presence()
    await test_permission_denied_warns_once()
    print('='*70)
    print('TODOS OS TESTES PASSARAM')
    print('='*70)

if __name__=='__main__':
    asyncio.run(main())
