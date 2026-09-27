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
            await page.evaluate("() => mapedNovo()")
            await page.wait_for_function("() => mapedMapa.width===40", timeout=8000)

            # 1) o modo Ambiente já entra sem bloqueio
            await page.evaluate("() => { document.getElementById('maped-collide').checked=true; mapedSetMode('ambiente'); }")
            assert await page.evaluate("() => document.getElementById('maped-collide').checked") is False, \
                'entrar no modo Ambiente devia desmarcar "bloqueia passagem"'
            r = await page.evaluate("""() => {
              [['Museum_room_1',1,1],['Gym',22,1],['Generic_Home_1',1,20],['Japanese_Home_1',18,20]]
                .forEach(([id,x,y])=>{ mapedEscolheDesign(id); mapedCarimbarAmbiente(x,y); });
              const d=mapedDiagnostico();
              return {solidos:mapedGradeSolida().reduce((a,v)=>a+v,0), alcance:d.alcance, livre:d.livre,
                      objetos:mapedMapa.layers.filter(l=>l.type==='objectgroup').reduce((a,l)=>a+l.objects.length,0)};
            }""")
            print('4 ambientes carimbados:', r)
            assert r['objetos'] > 400, r
            assert r['solidos'] == 0, f"carimbo ainda bloqueia ({r['solidos']} tiles)"
            assert r['alcance'] == r['livre'], r
            print('✓ ambiente carimbado entra como decoração, mapa 100% andável')

            # 2) quem quiser bloqueio marca a caixinha e continua funcionando
            bloq = await page.evaluate("""() => {
              mapedMapa.layers=mapedMapa.layers.filter(l=>l.type==='tilelayer');
              document.getElementById('maped-collide').checked=true;
              mapedEscolheDesign('Museum_room_1'); mapedCarimbarAmbiente(1,1);
              return mapedGradeSolida().reduce((a,v)=>a+v,0);
            }""")
            print('mesmo carimbo com a caixinha marcada:', bloq, 'tiles sólidos')
            assert bloq > 100, 'marcar a caixinha devia voltar a bloquear'

            # 3) "Liberar móveis" conserta um mapa já travado, de uma vez
            antes = await page.evaluate("() => mapedGradeSolida().reduce((a,v)=>a+v,0)")
            await page.evaluate("() => mapedLiberarMoveis()")
            depois = await page.evaluate("""() => {
              const d=mapedDiagnostico();
              return {solidos:mapedGradeSolida().reduce((a,v)=>a+v,0), alcance:d.alcance, livre:d.livre,
                      objetos:mapedMapa.layers.filter(l=>l.type==='objectgroup').reduce((a,l)=>a+l.objects.length,0),
                      todosFalse:mapedMapa.layers.filter(l=>l.type==='objectgroup'&&l.name!=='Chair')
                        .every(l=>l.objects.every(o=>o.properties.find(p=>p.name==='collide').value===false))};
            }""")
            print(f'liberar móveis: {antes} -> {depois["solidos"]} sólidos | {depois["objetos"]} objetos continuam no mapa')
            assert depois['solidos'] == 0 and depois['todosFalse'], depois
            assert depois['objetos'] > 100, 'liberar não pode apagar móvel'
            assert depois['alcance'] == depois['livre'], depois
            print('✓ "Liberar móveis" destrava sem apagar nada')

            # 4) a camada Parede sobrevive ao "liberar" — ela é o desenho de parede
            sobrou = await page.evaluate("""() => {
              mapedSetMode('parede'); document.getElementById('maped-collide').checked=true;
              mapedAplicar(5,5); mapedAplicar(5,6);
              const a=mapedGradeSolida().reduce((x,v)=>x+v,0);
              mapedLiberarMoveis();
              return {antes:a, depois:mapedGradeSolida().reduce((x,v)=>x+v,0)};
            }""")
            print('parede desenhada à mão:', sobrou)
            assert sobrou['depois'] == 2, 'liberar móveis não pode apagar a parede desenhada'
            print('✓ parede desenhada no modo Parede continua de pé')

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — ambiente não trava mais o mapa, e dá pra destravar o que já estava travado')
        finally:
            await browser.close()
asyncio.run(main())
