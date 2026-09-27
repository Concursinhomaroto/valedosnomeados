import asyncio, json, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, make_seed({'studyNickname':'Reitor','studyCharacter':'ash'}))
        try:
            # 1) o botão só existe pra quem é admin, e a tela abre
            await page.evaluate("() => showScreen('admin')")
            assert await page.locator("button:has-text('Abrir o editor de mapa')").count() == 1
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)

            base = await page.evaluate("""() => ({
                w: mapedMapa.width, h: mapedMapa.height,
                tilesets: mapedMapa.tilesets.length,
                catalogo: SALA_TILESETS.length,
                temHospital: mapedMapa.tilesets.some(t => t.name === 'Hospital'),
                temMuseu: mapedMapa.tilesets.some(t => t.name === 'Museum'),
                opcoes: [...document.querySelectorAll('#maped-ts option')].length,
                grupos: [...document.querySelectorAll('#maped-ts optgroup')].length,
            })""")
            print('editor abriu:', base)
            assert base['tilesets'] == base['catalogo'], base
            assert base['temHospital'] and base['temMuseu'], 'faltou tileset do pacote'
            assert base['opcoes'] == base['catalogo'], base
            assert base['grupos'] >= 5, base

            # 2) coloca uma peça de HOSPITAL 2x2 no tile (5,5)
            antes = await page.evaluate("() => (mapedMapa.layers.find(l=>l.name==='Obj_Hospital')||{objects:[]}).objects.length")
            await page.evaluate("""() => {
                mapedSelectTileset('Hospital');
                mapedSel = {c:2, r:3, w:2, h:2};
                mapedSetMode('objeto');
                mapedSnapshot();
                mapedAplicar(5, 5);
            }""")
            depois = await page.evaluate("""() => {
                const l = mapedMapa.layers.find(l=>l.name==='Obj_Hospital');
                const ts = SALA_TS_BY_NAME['Hospital'];
                return {n:l.objects.length, gids:l.objects.map(o=>o.gid),
                        esperado:[0,1,ts.c,ts.c+1].map(k=>ts.f + 3*ts.c + 2 + (k>=ts.c?ts.c-ts.c:0)),
                        first:ts.f, cols:ts.c,
                        pos:l.objects.map(o=>[o.x/32,(o.y-o.height)/32]),
                        col:l.objects[0].properties.find(p=>p.name==='collide').value};
            }""")
            print('peça hospital:', depois['n'], 'objetos | gids', depois['gids'], '| pos', depois['pos'])
            assert depois['n'] == antes + 4, 'peça 2x2 devia virar 4 objetos'
            f, c = depois['first'], depois['cols']
            assert depois['gids'] == [f+3*c+2, f+3*c+3, f+4*c+2, f+4*c+3], depois['gids']
            assert depois['pos'] == [[5,5],[6,5],[5,6],[6,6]], depois['pos']
            assert depois['col'] is True

            # 3) desfazer volta ao estado anterior
            await page.evaluate("() => mapedUndo()")
            n = await page.evaluate("() => (mapedMapa.layers.find(l=>l.name==='Obj_Hospital')||{objects:[]}).objects.length")
            assert n == antes, f'undo não voltou ({n} != {antes})'

            # 4) pintar piso troca o gid do Ground, sem mexer em objeto
            await page.evaluate("""() => {
                mapedSelectTileset('FloorAndGround');
                mapedSel = {c:9, r:20, w:1, h:1};
                mapedSetMode('piso');
                mapedSnapshot(); mapedAplicar(3, 3);
            }""")
            piso = await page.evaluate("""() => {
                const g = mapedMapa.layers.find(l=>l.type==='tilelayer');
                const ts = SALA_TS_BY_NAME['FloorAndGround'];
                return {gid: g.data[3*mapedMapa.width+3], esperado: ts.f + 20*ts.c + 9};
            }""")
            assert piso['gid'] == piso['esperado'], piso

            # 5) cadeira vai pra camada Chair, com direção
            await page.evaluate("""() => {
                mapedSelectTileset('chair');
                mapedSel = {c:0, r:1, w:1, h:1};
                mapedSetMode('cadeira'); mapedSnapshot(); mapedAplicar(4, 4);
            }""")
            cad = await page.evaluate("""() => {
                const l = mapedMapa.layers.find(l=>l.name==='Chair');
                const o = l.objects[l.objects.length-1];
                return {dir:o.properties.find(p=>p.name==='direction').value, h:o.height, x:o.x/32};
            }""")
            print('cadeira:', cad)
            assert cad['dir'] == 'left' and cad['h'] == 64 and cad['x'] == 4, cad

            # 6) borracha tira a peça mais de cima daquele tile
            await page.evaluate("""() => {
                mapedSelectTileset('Museum'); mapedSel={c:1,r:1,w:1,h:1};
                mapedSetMode('objeto'); mapedSnapshot(); mapedAplicar(9, 9);
                mapedSetMode('borracha'); mapedSnapshot(); mapedAplicar(9, 9);
            }""")
            mus = await page.evaluate("() => (mapedMapa.layers.find(l=>l.name==='Obj_Museum')||{objects:[]}).objects.length")
            assert mus == 0, f'borracha não apagou (sobrou {mus})'

            # 7) ponto de entrada
            await page.evaluate("() => { mapedSetMode('spawn'); mapedAplicar(11, 12); }")
            sp = await page.evaluate("() => mapedMapa.properties.find(p=>p.name==='spawn').value")
            assert sp == '11,12', sp

            # 8) publicar grava em sala_mapa/atual e derruba o jogo antigo
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c => c.path === 'sala_mapa/atual')", timeout=8000)
            pub = await page.evaluate("""() => {
                const c = window.__updateCalls.filter(c => c.path === 'sala_mapa/atual').pop();
                const m = JSON.parse(c.val.json);
                return {op:c.op, w:m.width, h:m.height, spawn:m.properties.find(p=>p.name==='spawn').value,
                        tilesets:m.tilesets.length, camadas:m.layers.length};
            }""")
            print('publicado:', pub)
            assert pub['op'] == 'set' and pub['spawn'] == '11,12', pub
            # publicado vem PODADO: só as folhas que o mapa usa
            assert 0 < pub['tilesets'] < 40, f"esperava mapa podado, veio {pub['tilesets']} folhas"

            # 9) a Sala passa a ler a planta publicada em vez do arquivo
            lida = await page.evaluate("""async () => {
                const m = await salaMapaFetchMap();
                return {w:m.width, spawn:(m.properties||[]).find(p=>p.name==='spawn')?.value};
            }""")
            print('sala lê do Firebase:', lida)
            assert lida['spawn'] == '11,12', lida

            # 10) voltar ao padrão remove o nó e volta pro arquivo do repositório
            page.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
            await page.evaluate("() => mapedRestaurarPadrao()")
            await page.wait_for_function("() => window.__updateCalls.some(c => c.path==='sala_mapa/atual' && c.op==='remove')", timeout=8000)
            volta = await page.evaluate("""async () => {
                const m = await salaMapaFetchMap();
                return {w:m.width, h:m.height, spawn:(m.properties||[]).find(p=>p.name==='spawn')?.value};
            }""")
            print('depois de restaurar:', volta)
            assert volta['w'] == 92 and volta['h'] == 72 and volta['spawn'] == '45,64', volta

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — editor de mapa: catálogo completo do pacote, peça/piso/cadeira/borracha/entrada, desfazer, publicar e restaurar')
        finally:
            await browser.close()

asyncio.run(main())
