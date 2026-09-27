import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SEED=make_seed({'studyNickname':'Leo','studyCharacter':'ash'})
OUTRO='UID_ANA'; LONGE='UID_BIA'

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, SEED)
        try:
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_timeout(2500)

            # duas outras pessoas: uma perto e uma com coordenada de mapa antigo
            await page.evaluate("""([a,b]) => {
                window.__writeOtherPlayer(a,{nickname:'Ana',character:'lucy_media',x:1500,y:2100,
                    state:'idle',dir:'down',fora:false,ts:Date.now()});
                window.__writeOtherPlayer(b,{nickname:'Bia',character:'nancy_retinta',x:60,y:60,
                    state:'idle',dir:'down',fora:true,ts:Date.now()});
            }""",[OUTRO,LONGE])
            await page.wait_for_timeout(600)

            r=await page.evaluate("""() => {
              const sc=salaMapaGame.scene.keys['salaMapaScene'];
              return {naCena:Object.keys(sc.otherPlayers),
                      roster:(document.getElementById('sala-chat-quem')||{}).textContent||'',
                      alphas:Object.keys(sc.otherPlayers).map(u=>[u,sc.otherPlayers[u].sprite.alpha]),
                      posBia:sc.otherPlayers['UID_BIA']?[sc.otherPlayers['UID_BIA'].sprite.x,sc.otherPlayers['UID_BIA'].sprite.y]:null};}""")
            print('1) na cena:', r['naCena'])
            print('   lista do painel:', repr(r['roster'].strip()[:90]))
            print('   opacidades:', r['alphas'], '| Bia em', r['posBia'])
            assert OUTRO in r['naCena'] and LONGE in r['naCena']
            assert 'Ana' in r['roster'] and 'Bia' in r['roster'], 'a lista não mostra quem está na sala'

            # --- 2) chat geral: a mensagem aparece e vira balão ---
            await page.evaluate("(u) => window.__sayAs(u,'Ana','bom dia, alguém revisando SUS?')",OUTRO)
            await page.wait_for_timeout(500)
            r=await page.evaluate("""() => {
              const sc=salaMapaGame.scene.keys['salaMapaScene'];
              return {msgs:(document.getElementById('sala-chat-msgs')||{}).textContent||'',
                      baloes:Object.keys(sc.baloes||{}),
                      textoBalao:(sc.baloes&&sc.baloes['UID_ANA'])?sc.baloes['UID_ANA'].t.text:''};}""")
            print('2) painel mostra:', repr(r['msgs'].strip()[:60]))
            print('   balões no mapa:', r['baloes'], '| texto:', repr(r['textoBalao'][:40]))
            assert 'bom dia' in r['msgs'] and 'Ana' in r['msgs']
            assert OUTRO in r['baloes'], 'não apareceu balão na cabeça de quem falou'
            assert 'bom dia' in r['textoBalao']

            # --- 3) eu envio: vai pro Firebase e ganha balão na MINHA cabeça ---
            await page.evaluate("""() => {const i=document.getElementById('sala-chat-inp');
                i.value='vou revisar agora'; salaChatEnviar();}""")
            await page.wait_for_timeout(600)
            r=await page.evaluate("""() => {
              const sc=salaMapaGame.scene.keys['salaMapaScene'];
              const n=window.__root.sala_chat||{};
              return {noBanco:Object.values(n).map(m=>m.txt),
                      meuBalao:!!(sc.baloes&&sc.baloes['TEST_UID_LEO']),
                      campoLimpo:document.getElementById('sala-chat-inp').value===''};}""")
            print('3) no Firebase:', r['noBanco'], '| balão meu:', r['meuBalao'], '| campo limpo:', r['campoLimpo'])
            assert 'vou revisar agora' in r['noBanco']
            assert r['campoLimpo']

            # --- 4) trava de repetição ---
            await page.evaluate("""() => {const i=document.getElementById('sala-chat-inp');
                i.value='spam'; salaChatEnviar();}""")
            await page.wait_for_timeout(300)
            n=await page.evaluate("() => Object.keys(window.__root.sala_chat||{}).length")
            print('4) mensagens no banco depois de tentar mandar 2 seguidas:', n, '(esperado 2: a da Ana + a minha)')
            assert n==2, 'a trava de repetição não segurou'

            # --- 5) HTML na mensagem NAO pode virar HTML ---
            await page.evaluate("(u) => window.__sayAs(u,'Ana','<img src=x onerror=alert(1)>')",OUTRO)
            await page.wait_for_timeout(400)
            r=await page.evaluate("""() => ({temImg:!!document.querySelector('#sala-chat-msgs img'),
                texto:(document.getElementById('sala-chat-msgs')||{}).textContent||''})""")
            print('5) injetou <img>?', r['temImg'], '| aparece como texto?', '<img src=x' in r['texto'])
            assert not r['temImg'] and '<img src=x' in r['texto']

            # --- 6) mensagem privada: chega, abre aba e nao vaza pro geral ---
            await page.evaluate("([meu,de]) => window.__dmTo(meu,de,'Ana','me chama no pv')",['TEST_UID_LEO',OUTRO])
            await page.wait_for_timeout(500)
            r=await page.evaluate("""() => ({abas:[...document.querySelectorAll('.sala-chat-tab')].map(b=>b.textContent.trim()),
                geral:(document.getElementById('sala-chat-msgs')||{}).textContent||'',
                naoLidas:salaDmConversas['UID_ANA']?salaDmConversas['UID_ANA'].naoLidas:-1})""")
            print('6) abas:', r['abas'], '| não lidas:', r['naoLidas'])
            assert any('Ana' in a for a in r['abas']), 'a conversa privada não abriu aba'
            assert 'me chama no pv' not in r['geral'], 'mensagem privada vazou pro chat geral'
            assert r['naoLidas']==1

            # --- 7) abrir a aba mostra a conversa e zera o nao-lido ---
            await page.evaluate("() => salaChatAbrirDM('UID_ANA','Ana')")
            await page.wait_for_timeout(300)
            r=await page.evaluate("""() => ({txt:(document.getElementById('sala-chat-msgs')||{}).textContent||'',
                naoLidas:salaDmConversas['UID_ANA'].naoLidas})""")
            print('7) conversa privada:', repr(r['txt'].strip()[:40]), '| não lidas:', r['naoLidas'])
            assert 'me chama no pv' in r['txt'] and r['naoLidas']==0

            # --- 8) eu respondo no privado: escreve nas DUAS caixas ---
            await page.evaluate("""() => { salaChatUltimoEnvio=0;
                const i=document.getElementById('sala-chat-inp');
                i.value='opa, bora'; salaChatEnviar(); }""")
            await page.wait_for_timeout(600)
            r=await page.evaluate("""() => ({minha:Object.values((window.__root.sala_dm||{}).TEST_UID_LEO?.UID_ANA||{}).map(m=>m.txt),
                dela:Object.values((window.__root.sala_dm||{}).UID_ANA?.TEST_UID_LEO||{}).map(m=>m.txt),
                geral:Object.values(window.__root.sala_chat||{}).map(m=>m.txt)})""")
            print('8) minha caixa:', r['minha'], '| caixa dela:', r['dela'])
            print('   chat geral continua com:', r['geral'])
            assert 'opa, bora' in r['minha'] and 'opa, bora' in r['dela'], 'não entregou nas duas caixas'
            assert 'opa, bora' not in r['geral'], 'mensagem privada foi parar no geral'

            errs=real_errors(errors); assert not errs, errs
            print('\nTODOS OS 8 TESTES DO CHAT PASSARAM')
        finally:
            await browser.close()
asyncio.run(main())
