import asyncio, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            page.on('dialog', lambda d: asyncio.ensure_future(d.accept('40')))
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)

            # 1) abre editando o que já existe (campus atual), sem nada pendente
            st = await page.evaluate("() => ({w:mapedMapa.width,h:mapedMapa.height,sujo:mapedSujo,pecas:mapedMapa.layers.filter(l=>l.type==='objectgroup').reduce((a,l)=>a+l.objects.length,0)})")
            print('abriu editando o atual:', st)
            assert st['w'] == 92 and st['h'] == 72 and st['pecas'] > 500 and st['sujo'] is False, st

            # 2) editar marca como não publicado
            await page.evaluate("() => { mapedSelectTileset('Museum'); mapedSel={c:1,r:1,w:1,h:1}; mapedSetMode('objeto'); mapedSnapshot(); mapedAplicar(3,3); }")
            assert await page.evaluate("() => mapedSujo") is True
            assert 'não publicadas' in await page.evaluate("() => document.getElementById('maped-info').innerHTML")

            # 3) NOVO DO ZERO: 40x40 (o prompt é respondido com '40' pelo handler)
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===40", timeout=8000)
            novo = await page.evaluate("""() => {
                const g=mapedMapa.layers.find(l=>l.type==='tilelayer');
                const fg=SALA_TS_BY_NAME['FloorAndGround'];
                return {w:mapedMapa.width,h:mapedMapa.height,
                        camadas:mapedMapa.layers.length,
                        pecas:mapedMapa.layers.filter(l=>l.type==='objectgroup').reduce((a,l)=>a+l.objects.length,0),
                        tilesets:mapedMapa.tilesets.length, catalogo:SALA_TILESETS.length,
                        chaoVazio:g.data.filter(v=>!v).length,
                        chaoEsperado:fg.f+30*fg.c+5, chao0:g.data[0],
                        spawn:mapedMapa.properties.find(p=>p.name==='spawn').value,
                        sujo:mapedSujo, undo:mapedUndoStack.length};
            }""")
            print('novo do zero:', novo)
            assert novo['w'] == 40 and novo['h'] == 40, novo
            assert novo['pecas'] == 0, 'mapa novo veio com peças'
            assert novo['camadas'] == 1, 'mapa novo devia ter só o Ground'
            assert novo['tilesets'] == novo['catalogo'], 'mapa novo perdeu o catálogo'
            assert novo['chaoVazio'] == 0, 'chão do mapa novo tem buraco (gid 0)'
            assert novo['chao0'] == novo['chaoEsperado'], novo
            assert novo['spawn'] == '20,20', novo
            assert novo['sujo'] is False and novo['undo'] == 0, novo

            # 4) dá pra construir no mapa novo e publicar
            await page.evaluate("""() => {
                mapedSelectTileset('Hospital'); mapedSel={c:0,r:0,w:2,h:2};
                mapedSetMode('objeto'); mapedSnapshot(); mapedAplicar(4,4);
            }""")
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            pub = await page.evaluate("""() => {
                const m=JSON.parse(window.__updateCalls.filter(c=>c.path==='sala_mapa/atual').pop().val.json);
                return {w:m.width,h:m.height,camadas:m.layers.map(l=>l.name),
                        hosp:(m.layers.find(l=>l.name==='Obj_Hospital')||{objects:[]}).objects.length};
            }""")
            print('publicado do zero:', pub)
            assert pub['w'] == 40 and pub['hosp'] == 4, pub
            assert await page.evaluate("() => mapedSujo") is False

            # 5) o jogo consegue montar esse mapa novo (é o teste que importa:
            #    mapa em branco não pode quebrar o Phaser)
            await page.evaluate("() => { salaMapaJSON=null; }")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {
                const g=salaMapaGame; return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""",
                timeout=25000)
            jogo = await page.evaluate("""() => {
                const s=salaMapaGame.scene.keys['salaMapaScene'];
                return {w:s.physics.world.bounds.width,h:s.physics.world.bounds.height,
                        x:Math.round(s.player.x),y:Math.round(s.player.y)};}""")
            print('jogo com o mapa do zero:', jogo)
            assert (jogo['w'], jogo['h']) == (40*32, 40*32), jogo
            assert jogo['x'] == 20*32+16 and jogo['y'] == 20*32+16, jogo

            # 6) voltar pro campus padrão sem despublicar
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.evaluate("() => mapedAbrir('padrao')")
            await page.wait_for_function("() => mapedMapa.width===92", timeout=10000)
            print('abriu o campus padrão de volta: 92x72')

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — dá pra criar do zero, editar o que existe, e o jogo roda o mapa novo')
        finally:
            await browser.close()

asyncio.run(main())
