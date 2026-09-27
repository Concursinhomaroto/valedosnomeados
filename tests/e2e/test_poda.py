import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            page.on('dialog', lambda d: asyncio.ensure_future(d.accept('40')))
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)

            cat = await page.evaluate("""() => ({
                folhas: SALA_TILESETS.length,
                cats: [...new Set(SALA_TILESETS.map(t=>t.cat||(t.d?'design':'tema')))].sort(),
                tiles: SALA_TILESETS.reduce((a,t)=>a+t.t,0),
                gidsContiguos: SALA_TILESETS.every((t,i,a)=>i===0||t.f===a[i-1].f+a[i-1].t),
            })""")
            print('catálogo:', cat['folhas'], 'folhas |', cat['tiles'], 'tiles |', cat['cats'])
            assert cat['gidsContiguos'], 'faixa de gid com buraco ou sobreposição'
            assert cat['folhas'] >= 149, cat

            # cada folha do catálogo tem que existir e fatiar como declarado
            faltando = await page.evaluate("""async () => {
              const ruins=[];
              for(const t of SALA_TILESETS){
                const ok=await new Promise(res=>{
                  const im=new Image();
                  im.onload=()=>res(im.naturalWidth===t.c*t.w && Math.floor(im.naturalHeight/t.h)*t.c===t.t);
                  im.onerror=()=>res(false);
                  im.src=SALA_ASSETS+t.i;
                });
                if(!ok)ruins.push(t.n);
              }
              return ruins;
            }""")
            if faltando: print('  ✗ folhas com problema:', faltando[:10])
            assert not faltando, f'{len(faltando)} folhas não carregam ou não fatiam como o catálogo diz'
            print(f'✓ as {cat["folhas"]} folhas carregam e fatiam exatamente como declarado')

            # poda: peça de folha nova tem que sobreviver
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===40", timeout=8000)
            usadas = await page.evaluate("""() => {
              const alvos=['antigos_Colored_ceilings','construcao_Room_Builder_Floors',
                           'sombra_Hospital_Black_Shadow','semsombra_Museum_Shadowless','pacote_Kitchen'];
              alvos.forEach((n,i)=>{
                const t=SALA_TS_BY_NAME[n];
                mapedTS=t; mapedSel={c:0,r:0,w:1,h:1}; mapedModo='objeto';
                document.getElementById('maped-collide').checked=false;
                mapedAplicar(2+i*3, 5);
              });
              const pub=mapedParaPublicar();
              return {alvos, declaradas:pub.tilesets.map(t=>t.name),
                      total:pub.tilesets.length, catalogo:SALA_TILESETS.length};
            }""")
            print('publicado declara', usadas['total'], 'de', usadas['catalogo'], 'folhas')
            for a in usadas['alvos']:
                assert a in usadas['declaradas'], f'a poda derrubou {a}, que o mapa usa'
            assert 'FloorAndGround' in usadas['declaradas'] and 'chair' in usadas['declaradas']
            assert usadas['total'] < 20, usadas['total']
            print('✓ poda mantém toda folha usada e descarta o resto')

            # e o jogo monta esse mapa podado
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            await page.evaluate("() => { salaMapaJSON=null; }")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {const g=salaMapaGame;
                return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""", timeout=25000)
            jogo = await page.evaluate("""() => {
              const s=salaMapaGame.scene.keys['salaMapaScene'];
              const alvos=['antigos_Colored_ceilings','construcao_Room_Builder_Floors',
                           'sombra_Hospital_Black_Shadow','semsombra_Museum_Shadowless','pacote_Kitchen'];
              return {carregadas:SALA_TILESETS.filter(t=>s.textures.exists(t.key)).length,
                      alvosOk:alvos.every(n=>{
                        const t=SALA_TS_BY_NAME[n];
                        return s.textures.exists(t.key) && s.textures.get(t.key).frameTotal-1===t.t;
                      })};
            }""")
            print('jogo carregou', jogo['carregadas'], 'folhas | peças novas ok:', jogo['alvosOk'])
            assert jogo['alvosOk'], 'folha nova não renderiza no jogo'
            assert jogo['carregadas'] < 20, jogo

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — catálogo completo no editor, e o mapa publicado só carrega o que usa')
        finally:
            await browser.close()
asyncio.run(main())
