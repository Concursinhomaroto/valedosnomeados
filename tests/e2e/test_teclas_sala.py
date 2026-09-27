# As teclas do jogo nao podem sumir dos campos de texto da plataforma,
# nem mover o boneco enquanto voce digita.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

TXT='Wanda Sawyer descreve algo'   # tem W, A, S, D, E e espaço

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, make_seed({'studyNickname':'R','studyCharacter':'ash'}))
        try:
            await page.click('#nav-sala')
            await page.wait_for_function("()=>{const g=salaMapaGame;return !!(g&&g.scene.keys['salaMapaScene']&&g.scene.keys['salaMapaScene'].player);}",timeout=25000)
            await page.wait_for_timeout(700)

            print('=== 1) digitar num modal aberto por cima da Sala ===')
            await page.evaluate("()=>openAISettingsModal()")
            await page.wait_for_timeout(400)
            xAntes=await page.evaluate("()=>Math.round(salaMapaGame.scene.keys['salaMapaScene'].player.x)")
            await page.click('#gemini-key-input')
            await page.evaluate("()=>{document.getElementById('gemini-key-input').value='';}")
            await page.type('#gemini-key-input',TXT,delay=20)
            v=await page.input_value('#gemini-key-input')
            xDepois=await page.evaluate("()=>Math.round(salaMapaGame.scene.keys['salaMapaScene'].player.x)")
            print('  digitado:',v)
            print(f'  jogador: {xAntes} -> {xDepois}')
            assert v==TXT, f'perdeu letras: {v!r}'
            assert xAntes==xDepois, 'o boneco andou enquanto eu digitava'
            print('  ✓ texto inteiro e boneco parado')

            print('\n=== 2) fechado o modal, o jogo volta a responder ===')
            await page.evaluate("()=>closeModal()")
            await page.evaluate("()=>document.activeElement&&document.activeElement.blur()")
            await page.wait_for_timeout(300)
            x1=await page.evaluate("()=>Math.round(salaMapaGame.scene.keys['salaMapaScene'].player.x)")
            await page.keyboard.down('d'); await page.wait_for_timeout(450); await page.keyboard.up('d')
            x2=await page.evaluate("()=>Math.round(salaMapaGame.scene.keys['salaMapaScene'].player.x)")
            print(f'  andou com D: {x1} -> {x2}')
            assert x2>x1, 'o jogo não voltou a responder'
            print('  ✓ anda normalmente')

            print('\n=== 3) o Phaser não captura tecla nenhuma da página ===')
            cap=await page.evaluate('''()=>{
              const km=salaMapaGame.input.keyboard;
              const m=km.manager||{};
              return {captures:(m.captures||[]).length, preventDefault:!!m.preventDefault};}''')
            print(' ',cap)
            assert cap['captures']==0, cap
            print('  ✓ nenhuma tecla presa pelo jogo')

            print('\n=== 4) digitar num campo comum, fora de modal ===')
            await page.evaluate("()=>showScreen('editais')")
            await page.wait_for_timeout(400)
            await page.click('#ed-nome')
            await page.fill('#ed-nome','')
            await page.type('#ed-nome',TXT,delay=20)
            v2=await page.input_value('#ed-nome')
            print('  digitado:',v2)
            assert v2==TXT, f'perdeu letras fora da sala: {v2!r}'
            print('  ✓ texto inteiro')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — as teclas do jogo não roubam mais as letras da plataforma')
        finally:
            await browser.close()
asyncio.run(main())
