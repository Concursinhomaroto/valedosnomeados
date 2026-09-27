import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors


async def apertar_e_ate(page, alvo, tentativas=6):
    """A tecla so chega ao Phaser com o canvas focado, e isso leva um frame ou dois.
    Sem isso o teste falhava de vez em quando e culpava o codigo."""
    for i in range(tentativas):
        await page.evaluate("()=>{const c=document.querySelector('#sala-game canvas')||document.querySelector('canvas');if(c){c.setAttribute('tabindex','0');c.focus();}}")
        await page.keyboard.press('e')
        await page.wait_for_timeout(180)
        st=await page.evaluate("()=>salaMapaGame.scene.keys['salaMapaScene'].player.playerBehavior")
        if st==alvo: return st
    return st

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'R','studyCharacter':'ash'}))
        try:
            def _dlg(d):
                print('DIALOGO:',d.type,'|',d.message[:90].replace('\n',' '))
                asyncio.ensure_future(d.accept('30'))
            page.on('dialog', _dlg)
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===30", timeout=8000)

            # 1) coloca um sofá de folha de TEMA (não da folha de cadeiras) e marca
            #    como assento — que é o caso que antes não dava pra sentar
            r=await page.evaluate("""() => {
              mapedSelectTileset('LivingRoom'); mapedSel={c:5,r:1,w:2,h:1};
              mapedSetMode('objeto'); document.getElementById('maped-collide').checked=false;
              mapedAplicar(10,10);
              mapedSetMode('sentar');
              document.getElementById('maped-sitdir').value='4';   // virado pra cima
              document.getElementById('maped-collide').checked=true;
              mapedAplicar(10,10);
              document.getElementById('maped-sitdir').value='1';   // pra baixo
              mapedAplicar(11,10);
              const l=mapedMapa.layers.find(x=>x.name==='Sit'),W=mapedMapa.width;
              return {existe:!!l, tipo:l&&l.type, a:l.data[10*W+10], b:l.data[10*W+11],
                      total:l.data.filter(v=>v).length,
                      cadeirasDaFolhaAntiga:(mapedMapa.layers.find(x=>x.name==='Chair')||{objects:[]}).objects.length};
            }""")
            print('camada Sit:', r)
            assert r['existe'] and r['tipo']=='tilelayer' and r['a']==4 and r['b']==1 and r['total']==2, r
            assert r['cadeirasDaFolhaAntiga']==0, 'não devia depender da folha de cadeiras'
            assert 'display' in await page.evaluate("()=>document.getElementById('maped-sitdir-wrap').getAttribute('style')")
            print('✓ qualquer móvel vira assento, com direção')

            # 2) a poda não pode confundir a camada Sit com gids
            pub=await page.evaluate("""() => {
              const m=mapedParaPublicar();
              return {temSit:!!m.layers.find(l=>l.name==='Sit'),
                      folhas:m.tilesets.length,
                      sitPreservada:(m.layers.find(l=>l.name==='Sit')||{}).data.filter(v=>v).length};
            }""")
            print('publicado:', pub)
            assert pub['temSit'] and pub['sitPreservada']==2, pub

            # 3) no jogo: os assentos existem e o E senta
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            await page.evaluate("() => { salaMapaJSON=null; }")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {const g=salaMapaGame;
              return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""", timeout=25000)
            info=await page.evaluate("""() => {
              const s=salaMapaGame.scene.keys['salaMapaScene'];
              return {n:(s.assentos||[]).length, dirs:(s.assentos||[]).map(a=>a.direction)};}""")
            print('assentos no jogo:', info)
            assert info['n']==2 and sorted(info['dirs'])==['down','up'], info

            # anda até o assento e aperta E
            await page.evaluate("""() => {const s=salaMapaGame.scene.keys['salaMapaScene'];
              s.player.setPosition(10*32+16, 10*32+16);}""")
            await page.wait_for_timeout(120)
            diag=await page.evaluate('''()=>{
              const s=salaMapaGame.scene.keys['salaMapaScene'],p=s.player;
              return {jogador:{x:p.x,y:p.y},
                      assentos:(s.assentos||[]).map(a=>({x:a.x,y:a.y,d:a.direction})),
                      dist:(s.assentos||[]).map(a=>Math.round(Math.hypot(p.x-a.x,p.y-a.y))),
                      temKeyE:!!s.keyE, comportamento:p.playerBehavior};
            }''')
            print('DIAG antes do E:',diag)
            await apertar_e_ate(page,'sitting')
            st=await page.evaluate("""() => {const p=salaMapaGame.scene.keys['salaMapaScene'].player;
              return {comportamento:p.playerBehavior, anim:p.anims.currentAnim&&p.anims.currentAnim.key};}""")
            print('depois do E:', st)
            assert st['comportamento']=='sitting', 'não sentou'
            assert '_sit_up' in (st['anim'] or ''), st

            st2=await apertar_e_ate(page,'idle')
            assert st2=='idle', 'não levantou'
            print('✓ senta com E e levanta com E')

            print('\nErros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — qualquer móvel pode virar assento e o personagem senta nele')
        finally:
            await browser.close()
asyncio.run(main())
