import asyncio, sys
sys.path.insert(0, '.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    seed = make_seed({'studyNickname': 'Keyboard Tester', 'studyCharacter': 'ash'})
    async with async_playwright() as p:
        browser, page, errors = await setup_page(p, seed)
        try:
            # entra na sala
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_function("""() => {
                const g = salaMapaGame;
                return !!(g && g.scene.keys['salaMapaScene'] && g.scene.keys['salaMapaScene'].player);
            }""", timeout=15000)
            await page.wait_for_timeout(200)

            # cria um input de teste fora da sala, pra medir se WASD/espaço chegam nele
            await page.evaluate("""() => {
                const inp = document.createElement('input');
                inp.type = 'text';
                inp.id = 'test-leak-input';
                inp.style.cssText = 'position:fixed;top:0;left:0;z-index:99999;width:200px;height:30px;';
                document.body.appendChild(inp);
            }""")

            # sai da sala pra outra tela qualquer (equivalente a ir pro painel de miniboss)
            await page.evaluate("() => showScreen('dashboard')")
            await page.wait_for_timeout(200)

            await page.click('#test-leak-input')
            await page.keyboard.type('wasd ')
            value = await page.evaluate("() => document.getElementById('test-leak-input').value")
            print('valor digitado depois de sair da sala:', repr(value))
            assert value == 'wasd ', f"teclado ainda travado fora da sala! digitou {value!r}, esperava 'wasd '"

            print('Erros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK: WASD e espaço voltam a funcionar fora da sala depois de sair (disableGlobalCapture)')
        finally:
            await browser.close()

asyncio.run(main())
