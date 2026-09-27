import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

# Apelido hostil: outro usuario grava isso em sala_presence/{uid dele}, que qualquer
# um pode escrever pra si mesmo e todo mundo le.
NICK_HOSTIL = "x');window.__INVADIDO=1;//"

async def main():
    async with async_playwright() as p:
        seed=make_seed({'studyNickname':'Leo','studyCharacter':'adam'})
        browser,page,errors=await setup_page(p,seed)
        try:
            await page.evaluate("()=>showScreen('sala')")
            await page.wait_for_timeout(1500)
            await page.evaluate("""(nick)=>window.__writeOtherPlayer('UID_ATACANTE',
                {nickname:nick,character:'adam',x:300,y:300,state:'idle',dir:1,fora:false,ts:Date.now()})""",NICK_HOSTIL)
            await page.wait_for_timeout(1200)
            # A vitima faz a acao mais normal do mundo: clica no nome pra mandar
            # mensagem privada pra pessoa que esta na sala.
            try:
                await page.locator('.sala-chat-pessoa').first.click(timeout=3000)
            except Exception as ex:
                print('(nao consegui clicar:',ex,')')
            await page.wait_for_timeout(600)
            r=await page.evaluate("""()=>({
              invadido: !!window.__INVADIDO,
              html: (document.getElementById('sala-chat-quem')||{}).innerHTML||''
            })""")
            print('apelido gravado pelo atacante:',repr(NICK_HOSTIL))
            print()
            print('HTML gerado na lista de quem está na sala:')
            print('   ',r['html'][:260])
            print()
            print('CÓDIGO DO ATACANTE EXECUTOU NO NAVEGADOR DA VÍTIMA?', 'SIM' if r['invadido'] else 'não')
            if errors: print('erros JS:',[e[:120] for e in real_errors(errors)][:3])
        finally:
            await browser.close()
asyncio.run(main())
