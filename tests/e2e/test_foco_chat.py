import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        seed=make_seed({'studyNickname':'Leo','studyCharacter':'adam'})
        browser,page,errors=await setup_page(p,seed)
        try:
            await page.evaluate("()=>showScreen('sala')")
            await page.wait_for_timeout(1800)

            await page.locator('#sala-chat-inp').click()
            await page.wait_for_timeout(300)
            r=await page.evaluate("()=>({foco:document.activeElement.id||document.activeElement.tagName,ocupado:salaTecladoOcupado()})")
            print('1) com o cursor no chat -> foco:',r['foco'],'| boneco parado:',r['ocupado'])
            assert r['ocupado'] is True, 'digitando no chat o boneco tem que ficar parado'

            box=await page.locator('#sala-mapa-viewport canvas').bounding_box()
            await page.mouse.click(box['x']+box['width']/2, box['y']+box['height']/2)
            await page.wait_for_timeout(400)
            r=await page.evaluate("()=>({foco:document.activeElement.id||document.activeElement.tagName,ocupado:salaTecladoOcupado()})")
            print('2) clicando de volta no mapa -> foco:',r['foco'],'| boneco parado:',r['ocupado'])
            assert r['ocupado'] is False, 'o clique no mapa tem que devolver o teclado ao boneco'

            antes=await page.evaluate("()=>({x:salaMapaSceneRef.player.x,y:salaMapaSceneRef.player.y})")
            await page.keyboard.down('ArrowRight'); await page.wait_for_timeout(700)
            await page.keyboard.up('ArrowRight'); await page.wait_for_timeout(200)
            depois=await page.evaluate("()=>({x:salaMapaSceneRef.player.x,y:salaMapaSceneRef.player.y})")
            andou=abs(depois['x']-antes['x'])+abs(depois['y']-antes['y'])
            print('3) andou',round(andou),'px depois de voltar pro mapa')
            assert andou>20, 'o boneco continua travado'

            print('4) volta pro chat e digita — nao pode andar enquanto digita')
            await page.locator('#sala-chat-inp').click()
            pos1=await page.evaluate("()=>salaMapaSceneRef.player.x")
            await page.keyboard.type('dddd'); await page.wait_for_timeout(500)
            pos2=await page.evaluate("()=>salaMapaSceneRef.player.x")
            texto=await page.evaluate("()=>document.getElementById('sala-chat-inp').value")
            print('   texto digitado:',repr(texto),'| moveu:',round(abs(pos2-pos1),1),'px')
            assert texto=='dddd', 'as letras tem que chegar no campo'
            assert abs(pos2-pos1)<1, 'o boneco andou enquanto digitava'

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
