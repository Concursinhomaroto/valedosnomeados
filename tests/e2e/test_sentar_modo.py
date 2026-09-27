import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

async def abrir(page):
    await page.evaluate("() => showScreen('mapaeditor')")
    await page.wait_for_timeout(1000)
    await page.evaluate("""() => {
        mapedCarregar(mapedMapaVazio(30,20));
        mapedTS=SALA_TS_BY_NAME.chair; mapedModo='objeto'; mapedSel={r:5,c:0,w:1,h:1};
        for(let i=0;i<4;i++) mapedAplicar(2+i*2, 6);
        mapedSetMode('sentar');
        document.getElementById('maped-collide').checked=true;
        document.getElementById('maped-sitdir').value='1';
        mapedZoomN=1; mapedDraw();
    }""")

async def clique(page, tx, ty):
    cv=await page.query_selector('#maped-canvas')
    box=await cv.bounding_box()
    z=await page.evaluate("() => mapedZoomN*32")
    await page.mouse.move(box['x']+tx*z+z/2, box['y']+ty*z+z/2)
    await page.mouse.down(); await page.wait_for_timeout(60); await page.mouse.up()
    await page.wait_for_timeout(120)

async def sit_count(page):
    return await page.evaluate("""() => {const s=mapedMapa.layers.find(l=>l.name==='Sit');
        return s?s.data.filter(Boolean).length:0;}""")

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, make_seed({'studyNickname':'Leo'}))
        try:
            await abrir(page)
            print('assentos antes:', await sit_count(page))
            errors.clear()
            await clique(page, 5, 5)
            n=await sit_count(page)
            print('assentos depois de um clique no modo Sentar:', n)
            print('erros JS durante o clique:', errors)
            assert n==1, f'o clique no modo Sentar não marcou nada (erros: {errors})'

            # arrastar deve pintar uma fileira inteira
            cv=await page.query_selector('#maped-canvas'); box=await cv.bounding_box()
            z=await page.evaluate("() => mapedZoomN*32")
            await page.mouse.move(box['x']+2*z+z/2, box['y']+10*z+z/2)
            await page.mouse.down()
            for tx in range(2,12):
                await page.mouse.move(box['x']+tx*z+z/2, box['y']+10*z+z/2)
                await page.wait_for_timeout(25)
            await page.mouse.up(); await page.wait_for_timeout(200)
            n2=await sit_count(page)
            print('assentos depois de arrastar 10 tiles:', n2)
            assert n2>=11, f'arrastar no modo Sentar marcou só {n2-1} tiles'
            print('erros JS:', errors)
            assert not errors, errors
            print('\nMODO SENTAR OK (clique + arrasto)')
        finally:
            await browser.close()
asyncio.run(main())
