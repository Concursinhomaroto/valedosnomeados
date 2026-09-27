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

            # o cenário do usuário: sala carimbada (móveis como decoração) + carteiras soltas
            st=await page.evaluate("""() => {
              mapedSetMode('ambiente'); mapedEscolheDesign('Museum_room_4'); mapedCarimbarAmbiente(2,2);
              mapedSelectTileset('Classroom_and_library'); mapedSetMode('objeto');
              document.getElementById('maped-collide').checked=false;
              mapedSel={c:2,r:1,w:1,h:2};
              for(const x of [4,8,12,16]) mapedAplicar(x,20);
              mapedMapa.properties=[{name:'spawn',type:'string',value:'1,28'}];
              const d=mapedDiagnostico();
              return {solidos:mapedGradeSolida().reduce((a,v)=>a+v,0),
                      objetos:mapedMapa.layers.filter(l=>l.type==='objectgroup').reduce((a,l)=>a+l.objects.length,0),
                      alcance:d.alcance};
            }""")
            print('antes (é o seu caso — anda por cima de tudo):', st)
            assert st['solidos']==0 and st['objetos']>50, st

            await page.evaluate("() => mapedBloquearMoveis()")
            dep=await page.evaluate("""() => {
              const d=mapedDiagnostico();
              return {solidos:mapedGradeSolida().reduce((a,v)=>a+v,0), alcance:d.alcance, livre:d.livre,
                      objetos:mapedMapa.layers.filter(l=>l.type==='objectgroup').reduce((a,l)=>a+l.objects.length,0),
                      todosTrue:mapedMapa.layers.filter(l=>l.type==='objectgroup'&&l.name!=='Chair')
                        .every(l=>l.objects.every(o=>o.properties.find(p=>p.name==='collide').value===true)),
                      vercol:document.getElementById('maped-vercol').checked};
            }""")
            print('depois de bloquear:', dep)
            assert dep['todosTrue'], 'sobrou móvel sem bloqueio'
            assert dep['solidos']>0 and dep['objetos']==st['objetos'], 'não pode apagar móvel'
            assert dep['alcance']<st['alcance'], 'o alcance devia diminuir'
            assert dep['vercol'] is True, 'devia ligar o "ver colisão"'
            print('✓ todos os móveis bloqueiam, nenhum foi apagado, e mostra o alcance novo')

            # desfazer volta atrás
            await page.evaluate("() => mapedUndo()")
            volta=await page.evaluate("() => mapedGradeSolida().reduce((a,v)=>a+v,0)")
            print('depois do desfazer:', volta, 'tiles sólidos')
            assert volta==0, volta
            print('✓ desfazer reverte')

            # e no jogo o personagem não sobe na carteira
            await page.evaluate("() => mapedBloquearMoveis()")
            await page.evaluate("() => mapedSalvar()")
            await page.wait_for_function("() => window.__updateCalls.some(c=>c.path==='sala_mapa/atual')", timeout=8000)
            await page.evaluate("() => { salaMapaJSON=null; }")
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {const g=salaMapaGame;
              return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}""", timeout=25000)
            # a carteira em (4,20) ocupa (4,19)-(4,20). Vem de cima e tenta subir nela.
            await page.evaluate("""() => {const s=salaMapaGame.scene.keys['salaMapaScene'];
              s.player.setPosition(4*32+16, 16*32);}""")
            for _ in range(26):
                await page.keyboard.down('s'); await page.wait_for_timeout(60)
            await page.keyboard.up('s')
            info=await page.evaluate("""()=>{const s=salaMapaGame.scene.keys['salaMapaScene'];
              const corpos=(s.solids?s.solids.getChildren():[]).map(o=>({x:Math.round(o.x),y:Math.round(o.y)}))
                .filter(o=>Math.abs(o.x-(4*32+16))<20).sort((a,b)=>a.y-b.y);
              return {y:Math.round(s.player.y), corpos:corpos.slice(0,4), nSolids:(s.solids?s.solids.getChildren().length:0)};}""")
            print('\nandando contra a carteira:', info)
            # a carteira ocupa as linhas 20 e 21 (seleção de 1x2), então o jogador
            # tem que parar antes da linha 20
            assert info['y']<20*32, 'ainda entra dentro do móvel'
            print('✓ o personagem não entra mais no móvel')

            print('\nErros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — móveis voltam a barrar em um clique, com o impacto à vista')
        finally:
            await browser.close()
asyncio.run(main())
