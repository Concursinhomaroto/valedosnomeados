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

            # 1) os 14 ambientes de 6_Home_Designs estão no módulo
            cat = await page.evaluate("""() => ({
                tilesets: SALA_TILESETS.length,
                designs: SALA_DESIGNS.length,
                labels: SALA_DESIGNS.map(d=>d.label),
                camadasRegistradas: SALA_DESIGNS.every(d=>d.camadas.every(c=>!!SALA_TS_BY_NAME[c.ts])),
                temPreview: SALA_DESIGNS.every(d=>!!d.preview),
            })""")
            print('catálogo:', cat['tilesets'], 'folhas |', cat['designs'], 'ambientes')
            print('  ', cat['labels'])
            assert cat['designs'] == 14, cat
            assert cat['camadasRegistradas'], 'camada de ambiente sem tileset registrado'
            assert cat['temPreview'], 'ambiente sem preview'
            for esperado in ('Museu — sala 1','Casa japonesa','Sorveteria','Estúdio de TV','Tiro ao alvo','Academia'):
                assert esperado in cat['labels'], esperado

            # 2) galeria renderiza os 14 cartões com a imagem certa
            await page.evaluate("() => mapedSetMode('ambiente')")
            cards = await page.evaluate("() => [...document.querySelectorAll('#maped-gallery .maped-card')].length")
            assert cards == 14, cards
            assert await page.evaluate("() => document.getElementById('maped-tspane').style.display") == 'none'

            # 3) carimbar num mapa em branco: chão vai pro Ground, móveis viram objetos
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===40", timeout=8000)
            antes = await page.evaluate("() => mapedGround().data.slice(0)")
            await page.evaluate("""() => {
                mapedSetMode('ambiente'); mapedEscolheDesign('Museum_room_1');
                mapedSnapshot(); mapedCarimbarAmbiente(3,3);
            }""")
            st = await page.evaluate("""([g00, g3939]) => {
                const d=SALA_DESIGNS.find(x=>x.id==='Museum_room_1');
                const chao=d.camadas[0], obj=d.camadas[1];
                const tsC=SALA_TS_BY_NAME[chao.ts], tsO=SALA_TS_BY_NAME[obj.ts];
                const g=mapedGround(), W=mapedMapa.width;
                const l=mapedMapa.layers.find(l=>l.name==='Obj_'+obj.ts);
                // 1º tile COM arte da camada de chão: o (0,0) do museu é
                // transparente (canto de fora da sala), e ali o chão de baixo
                // tem que ter sido preservado, não sobrescrito.
                const bits=mapedBits(chao.mask);
                let k0=-1;
                for(let k=0;k<chao.cols*chao.rows;k++){if((bits[k>>3]>>(k&7))&1){k0=k;break;}}
                const rx=3+(k0%chao.cols), ry=3+Math.floor(k0/chao.cols);
                return {
                  k0, gid33: g.data[ry*W+rx], esperado33: tsC.f+k0,
                  objetos: l?l.objects.length:0,
                  objDentroDoTileset: l?l.objects.every(o=>o.gid>=tsO.f&&o.gid<tsO.f+tsO.t):false,
                  objColide: l?l.objects.every(o=>o.properties.find(p=>p.name==='collide').value===false):false,
                  foraIntacto: g.data[0]===g00 && g.data[39*W+39]===g3939,
                };
            }""", [antes[0], antes[39*40+39]])
            print('carimbo:', st)
            # o 1º tile com arte da camada de chão foi carimbado no lugar certo
            assert st['gid33'] == st['esperado33'], st
            assert st['objetos'] == 162, f"esperava os 162 tiles com arte da camada de móveis, veio {st['objetos']}"
            assert st['objDentroDoTileset'], 'objeto com gid fora do tileset do ambiente'
            # Regra nova: o carimbo entra como DECORAÇÃO. Uma sala do pacote tem
            # 150+ tiles de móvel; marcar tudo como bloqueio fechava o mapa.
            assert st['objColide'], 'móvel do ambiente devia entrar sem bloquear'
            assert st['foraIntacto'], 'carimbo vazou pra fora da área do ambiente'

            # 4) o tile transparente do ambiente NÃO apaga o chão que já existia
            vazio = await page.evaluate("""() => {
                const d=SALA_DESIGNS.find(x=>x.id==='Museum_room_1'),c=d.camadas[0];
                const bits=mapedBits(c.mask); const g=mapedGround(),W=mapedMapa.width;
                for(let r=0;r<c.rows;r++)for(let cc=0;cc<c.cols;cc++){
                  const k=r*c.cols+cc;
                  if((bits[k>>3]>>(k&7))&1)continue;         // esse tem arte
                  return {x:3+cc,y:3+r,gid:g.data[(3+r)*W+3+cc]};
                }
                return null;
            }""")
            if vazio:
                print('tile transparente preservou o chão:', vazio)
                assert vazio['gid'] == antes[vazio['y']*40+vazio['x']], vazio

            # 5) modo Parede grava a camada Solid
            await page.evaluate("""() => {
                mapedSetMode('parede');
                document.getElementById('maped-collide').checked=true;
                mapedSnapshot(); mapedAplicar(2,2); mapedAplicar(2,3);
            }""")
            sol = await page.evaluate("""() => {
                const l=mapedMapa.layers.find(l=>l.name==='Solid'),W=mapedMapa.width;
                return {existe:!!l, tipo:l&&l.type, a:l.data[2*W+2], b:l.data[3*W+2], total:l.data.filter(v=>v).length};
            }""")
            print('parede:', sol)
            assert sol['existe'] and sol['a']==1 and sol['b']==1 and sol['total']==2, sol

            # 6) publica e o jogo respeita a Solid como colisão
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            await page.evaluate("() => { salaMapaJSON=null; }")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {const g=salaMapaGame;
                return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""", timeout=25000)
            jogo = await page.evaluate("""() => {
                const s=salaMapaGame.scene.keys['salaMapaScene'];
                const raw=s.cache.tilemap.get('tilemap').data;
                return {solidNoJogo:!!raw.layers.find(l=>l.name==='Solid'),
                        paredes:s.walls?s.walls.getChildren().length:null,
                        mundo:[s.physics.world.bounds.width,s.physics.world.bounds.height]};
            }""")
            print('no jogo:', jogo)
            assert jogo['solidNoJogo'], 'camada Solid não chegou no jogo'

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — 14 ambientes de 6_Home_Designs carimbáveis, com chão, móveis e desenho de colisão')
        finally:
            await browser.close()

asyncio.run(main())
