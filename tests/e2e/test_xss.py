import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

PAYLOAD = "x');window.__INVADIDO=1;//"

async def main():
    async with async_playwright() as p:
        seed=make_seed({'studyNickname':'Leo','studyCharacter':'adam','geminiApiKey':'FAKE'})
        browser,page,errors=await setup_page(p,seed)
        try:
            print('=== 1) apelido hostil de outro aluno na Sala ===')
            await page.evaluate("()=>showScreen('sala')")
            await page.wait_for_timeout(1600)
            await page.evaluate("""(nick)=>window.__writeOtherPlayer('UID_ATACANTE',
              {nickname:nick,character:'adam',x:300,y:300,state:'idle',dir:1,fora:false,ts:Date.now()})""",PAYLOAD)
            await page.wait_for_timeout(1000)
            await page.locator('.sala-chat-pessoa').first.click()
            await page.wait_for_timeout(500)
            r=await page.evaluate("()=>({invadido:!!window.__INVADIDO,abaAberta:salaChatAba})")
            print('   clicou no nome -> executou codigo?',r['invadido'],'| abriu a conversa:',r['abaAberta'])
            assert r['invadido'] is False, 'XSS pelo apelido ainda executa'
            assert r['abaAberta']=='UID_ATACANTE', 'a conversa privada parou de abrir'
            print('   OK — nao executa, e a conversa privada continua abrindo')

            print('\n=== 2) o mesmo payload como nome na aba do chat ===')
            r=await page.evaluate("""()=>{
              const t=document.getElementById('sala-chat-tabs');
              const btn=t&&t.querySelector('.sala-chat-tab.ativa');
              return {texto:btn?btn.textContent.trim():'', temScript:!!(t&&t.querySelector('script'))};
            }""")
            print('   texto da aba:',repr(r['texto'][:40]),'| virou tag/script:',r['temScript'])
            assert not r['temScript']
            assert "x');" in r['texto'], 'o apelido devia aparecer como texto literal'
            await page.evaluate("()=>{window.__INVADIDO=false;}")
            await page.locator('.sala-chat-tab.ativa').click()
            await page.wait_for_timeout(300)
            assert not await page.evaluate("()=>!!window.__INVADIDO"), 'clicar na aba executou o payload'
            print('   OK — texto inerte, clique na aba nao executa')

            print('\n=== 3) e-mail hostil no Painel Admin ===')
            r=await page.evaluate("""(payload)=>{
              window.__INVADIDO2=false;
              const html=renderAdminResults?null:null;
              // monta a linha do admin com o e-mail que o proprio usuario escreveu
              document.body.insertAdjacentHTML('beforeend',
                `<div id="probe"><button onclick="adminToggleOne('${escapeAttrJs(payload)}',true)">x</button></div>`);
              document.querySelector('#probe button').click();
              const ok=!window.__INVADIDO2;
              document.getElementById('probe').remove();
              return {seguro:ok, html:document.getElementById('probe')?'':'removido'};
            }""",PAYLOAD.replace('__INVADIDO','__INVADIDO2'))
            print('   e-mail com payload nao executou:',r['seguro'])
            assert r['seguro']

            print('\n=== 4) letra de alternativa vinda da IA ===')
            r=await page.evaluate("""(payload)=>{
              const attr=`onclick="sgSelectAnswer(0,'${escapeAttrJs(payload)}')"`;
              return {attr, temAspaSolta: /'\\)"$/.test(attr) && attr.indexOf("\\\\&#39;")<0};
            }""","A');window.__INVADIDO3=1;//")
            print('   atributo gerado:',r['attr'][:80])
            assert not r['temAspaSolta']
            print('   OK')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
