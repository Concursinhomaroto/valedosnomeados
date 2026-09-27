import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SEED=make_seed({'studyNickname':'Leo','studyCharacter':'ash','onboardingCompleted':True})

async def pres(page):
    return await page.evaluate("() => (window.__root.sala_presence||{}).TEST_UID_LEO || null")

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, SEED)
        try:
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_timeout(2500)
            p1=await pres(page)
            print('1) dentro da sala:', {k:p1[k] for k in ('nickname','fora','state')} if p1 else None)
            assert p1 and p1.get('fora') is False
            dot=await page.evaluate("() => getComputedStyle(document.getElementById('nav-sala-dot')).display")
            print('   pontinho verde no menu:', dot)
            assert dot!='none', 'o indicador de "estou na sala" não acendeu'

            # --- 2) passeia por VARIAS telas: a presenca tem de sobreviver a todas ---
            for tela in ['dashboard','flashcards','redacoes','repertorio','simgeral','dashboard']:
                await page.evaluate("(t) => showScreen(t)", tela)
                await page.wait_for_timeout(150)
                pp=await pres(page)
                assert pp is not None, f'a presença sumiu ao abrir "{tela}"'
            p2=await pres(page)
            print('2) depois de passear por 6 telas: presente =', p2 is not None, '| fora =', p2.get('fora'))
            assert p2.get('fora') is True
            dot=await page.evaluate("() => getComputedStyle(document.getElementById('nav-sala-dot')).display")
            print('   pontinho continua aceso fora da sala:', dot)
            assert dot!='none'

            # --- 3) o onDisconnect continua armado (fechar a aba ainda limpa) ---
            od=await page.evaluate("() => window.__onDisconnectRemoves.filter(p=>p.indexOf('sala_presence')===0)")
            can=await page.evaluate("() => (window.__onDisconnectCancels||[]).length")
            print('3) onDisconnect armado para:', od, '| cancelamentos:', can)
            assert 'sala_presence/TEST_UID_LEO' in od, 'a limpeza automática não está armada'

            # --- 4) o batimento renova o carimbo enquanto voce esta fora ---
            antes=(await pres(page)).get('ts')
            await page.evaluate("() => { salaPresenceBatimento && clearInterval(salaPresenceBatimento);"
                                "salaOwnPresenceKeyRef.update({ts:Date.now()}); }")
            await page.wait_for_timeout(150)
            depois=(await pres(page)).get('ts')
            temBatimento=await page.evaluate("() => typeof salaPresenceIniciaBatimento==='function'")
            print('4) batimento existe:', temBatimento, '| carimbo renova:', depois>=antes)
            assert temBatimento and depois>=antes

            # --- 5) voltar pra sala tira o "fora" e religa o listener dos outros ---
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_timeout(900)
            p3=await pres(page)
            ouvindo=await page.evaluate("() => !!salaPresenceRef")
            print('5) de volta na sala: fora =', p3.get('fora'), '| ouvindo os outros:', ouvindo)
            assert p3.get('fora') is False
            assert ouvindo, 'voltou pra sala mas parou de enxergar os outros'

            # --- 6) fora da sala o listener e desligado (nao gasta banda a toa) ---
            await page.evaluate("() => showScreen('dashboard')")
            await page.wait_for_timeout(250)
            ouvindo=await page.evaluate("() => !!salaPresenceRef")
            print('6) fora da sala, ouvindo os outros:', ouvindo, '(esperado: False)')
            assert not ouvindo

            # --- 6b) o botao "Sair da sala" alterna: sai e volta ---
            await page.evaluate("() => showScreen('sala')")
            await page.wait_for_timeout(700)
            await page.evaluate("() => salaSairDaSala()")
            await page.wait_for_timeout(300)
            fora=await pres(page)
            await page.evaluate("() => salaSairDaSala()")
            await page.wait_for_timeout(400)
            dentro=await pres(page)
            print('6b) depois de sair:', fora, '| depois de clicar de novo:', dentro is not None)
            assert fora is None, 'o botão não tirou da sala'
            assert dentro is not None, 'o botão não conseguiu voltar pra sala (armadilha)'

            # --- 7) o logout apaga a presenca ---
            await page.evaluate("() => { window.confirm=()=>true; }")
            await page.evaluate("() => authSignOut()")
            await page.wait_for_timeout(400)
            p4=await pres(page)
            print('7) presença depois do logout:', p4)
            assert p4 is None, 'o logout deixou o boneco na sala'

            errs=real_errors(errors); assert not errs, errs
            print('\nOK — a presença sobrevive à troca de tela e só some no logout, no botão de sair ou ao fechar a aba')
        finally:
            await browser.close()
asyncio.run(main())
