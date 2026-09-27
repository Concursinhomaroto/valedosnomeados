import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'R','studyCharacter':'ash'}))
        try:
            page.on('dialog', lambda d: asyncio.ensure_future(d.accept('30')))
            await page.evaluate("() => showScreen('mapaeditor')")
            await page.wait_for_function("() => !!mapedMapa", timeout=20000)
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===30", timeout=8000)

            # 1) pintar piso com "bloqueia passagem" marcado já cria a parede
            await page.evaluate("""() => {
              mapedSelectTileset('Room_Builder'); mapedSel={c:0,r:0,w:1,h:1};
              mapedSetMode('piso');
              document.getElementById('maped-collide').checked=true;
              mapedSnapshot();
              for(let x=3;x<=10;x++) mapedAplicar(x,3);          // uma parede de 8 tiles
              document.getElementById('maped-collide').checked=false;
              for(let x=3;x<=10;x++) mapedAplicar(x,4);          // e uma faixa de chão
            }""")
            r=await page.evaluate("""() => {
              const sol=mapedGradeSolida(),W=mapedMapa.width;
              let parede=0,chao=0;
              for(let x=3;x<=10;x++){ if(sol[3*W+x])parede++; if(sol[4*W+x])chao++; }
              return {parede,chao};
            }""")
            print('pintando com a caixinha:', r)
            assert r['parede']==8 and r['chao']==0, r
            print('  ✓ marcada vira parede, desmarcada vira chão livre')

            # 2) o cenário do usuário: mapa inteiro pintado SEM bloqueio nenhum
            await page.evaluate("""() => {
              const sol=mapedSolid(); sol.data.fill(0);
              mapedSelectTileset('Room_Builder'); mapedSetMode('piso');
              document.getElementById('maped-collide').checked=false;
              mapedSel={c:2,r:2,w:1,h:1};
              for(let x=5;x<=20;x++){ mapedAplicar(x,10); mapedAplicar(x,20); }  // 2 paredes
            }""")
            antes=await page.evaluate("() => mapedGradeSolida().reduce((a,v)=>a+v,0)")
            assert antes==0, f'devia estar tudo atravessável, veio {antes}'
            print('\nmapa construído sem colisão nenhuma:', antes, 'tiles sólidos (é o seu caso)')

            # 3) "Marcar paredes" lista os tipos e conserta em massa
            await page.evaluate("() => mapedMarcarParedes()")
            tipos=await page.evaluate("""() => [...document.querySelectorAll('.maped-parede-chk')]
              .map(c=>({gid:Number(c.dataset.gid), img:!!c.parentElement.querySelector('img')}))""")
            print('tipos de tile no chão:', len(tipos), '| com miniatura:', sum(1 for t in tipos if t['img']))
            assert len(tipos)>=2, tipos
            assert all(t['img'] for t in tipos), 'algum tipo veio sem miniatura'

            alvo=await page.evaluate("""() => {
              const g=mapedGround(),W=mapedMapa.width;
              return g.data[10*W+5];      // o gid da parede que eu pintei
            }""")
            await page.evaluate("""(gid) => {
              document.querySelectorAll('.maped-parede-chk').forEach(c=>{
                c.checked = Number(c.dataset.gid)===gid;
              });
              mapedAplicarParedes();
            }""", alvo)
            depois=await page.evaluate("""() => {
              const sol=mapedGradeSolida(),W=mapedMapa.width;
              let linha10=0,linha20=0,resto=0;
              for(let i=0;i<sol.length;i++){ if(!sol[i])continue;
                const y=(i/W)|0; if(y===10)linha10++; else if(y===20)linha20++; else resto++; }
              return {total:sol.reduce((a,v)=>a+v,0),linha10,linha20,resto,
                      vercol:document.getElementById('maped-vercol').checked};
            }""")
            print('depois de marcar:', depois)
            assert depois['linha10']==16 and depois['linha20']==16, depois
            assert depois['resto']==0, 'marcou tile que não era daquele tipo'
            assert depois['vercol'] is True, 'devia ligar o "ver colisão" pra mostrar o resultado'
            print('  ✓ as duas paredes do tipo marcado viraram sólidas, o chão não')

            # 4) e o jogo respeita isso
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            await page.evaluate("() => { salaMapaJSON=null; }")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {const g=salaMapaGame;
              return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""", timeout=25000)
            jogo=await page.evaluate("""() => {
              const s=salaMapaGame.scene.keys['salaMapaScene'];
              return s.walls?s.walls.getChildren().length:0;
            }""")
            print('\nparedes montadas no jogo:', jogo)
            assert jogo==32, f'esperava 32 corpos de colisão, veio {jogo}'

            # atravessa? empurra pra baixo contra a parede da linha 10
            await page.evaluate("""() => {const s=salaMapaGame.scene.keys['salaMapaScene'];
              s.player.setPosition(8*32+16, 8*32);}""")
            for _ in range(26):
                await page.keyboard.down('s'); await page.wait_for_timeout(60)
            await page.keyboard.up('s')
            pos=await page.evaluate("()=>{const p=salaMapaGame.scene.keys['salaMapaScene'].player;return Math.round(p.y);}")
            print('andando contra a parede: y =', pos, '-> bloqueou:', pos<10*32)
            assert pos<10*32, 'ainda atravessa a parede'
            print('  ✓ o jogador não passa mais por cima')

            print('\nErros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — parede pintada bloqueia, e mapa pronto se conserta por tipo de tile')
        finally:
            await browser.close()
asyncio.run(main())
