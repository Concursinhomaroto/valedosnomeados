import asyncio, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    seed = make_seed({'studyNickname': 'Testa Portas', 'studyCharacter': 'ash'})
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {
                const g = salaMapaGame; return !!(g && g.scene.keys['salaMapaScene'] && g.scene.keys['salaMapaScene'].player);
            }""", timeout=20000)
            # posiciona logo ACIMA da porta norte_2 (x=28) e anda pra baixo, atravessando
            await page.evaluate("""() => {
                const s = salaMapaGame.scene.keys['salaMapaScene'];
                s.player.setPosition(29*32, 15*32);
            }""")
            for _ in range(30):
                await page.keyboard.down('s'); await page.wait_for_timeout(60)
            await page.keyboard.up('s')
            pos = await page.evaluate("() => { const p = salaMapaGame.scene.keys['salaMapaScene'].player; return {x:p.x,y:p.y}; }")
            print('posição depois de andar pra baixo pela porta:', pos)
            assert pos['y'] > 15*32 + 60, f"travou na porta, não atravessou: {pos}"

            # tenta atravessar a parede do lado (não pela porta) — não pode passar
            await page.evaluate("""() => {
                const s = salaMapaGame.scene.keys['salaMapaScene'];
                s.player.setPosition(15*32, 16*32);
            }""")
            for _ in range(25):
                await page.keyboard.down('s'); await page.wait_for_timeout(60)
            await page.keyboard.up('s')
            pos2 = await page.evaluate("() => { const p = salaMapaGame.scene.keys['salaMapaScene'].player; return {x:p.x,y:p.y}; }")
            print('posição empurrando contra parede (fora da porta):', pos2)
            assert pos2['y'] < 17*32, f"atravessou a parede fora da porta! {pos2}"

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: atravessa pela porta, não atravessa pela parede')
        finally:
            await browser.close()

asyncio.run(main())
