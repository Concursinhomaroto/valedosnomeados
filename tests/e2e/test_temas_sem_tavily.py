import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_temas_atualidade import seed, TEMAS, gem_resp

async def main():
    async with async_playwright() as p:
        tav=[]
        async def t(route,request): tav.append(1); await route.fulfill(status=200,content_type='application/json',body='{"results":[]}')
        async def g(route,request): await route.fulfill(status=200,content_type='application/json',body=gem_resp(TEMAS))
        browser,page,errors=await setup_page(p, seed(tavily=False))
        try:
            await page.route('**api.tavily.com/search**', t)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
            await page.evaluate("() => showScreen('repertorio')")
            await page.wait_for_timeout(300)
            await page.evaluate("() => redAbrirTemasAtualidade()")
            await page.wait_for_timeout(200)
            aviso=await page.evaluate("() => (document.getElementById('modal-body')||{}).textContent||''")
            print('1) o formulário avisa que sem Tavily a busca não roda:',
                  'Sem chave do Tavily' in aviso)
            assert 'Sem chave do Tavily' in aviso
            await page.evaluate("() => redGerarTemasAtualidade()")
            await page.wait_for_timeout(2500)
            r=await page.evaluate("""() => ({tav:0, texto:(document.getElementById('modal-body')||{}).textContent||'',
                grounded:(db.temasAtualidade||{}).grounded, n:((db.temasAtualidade||{}).itens||[]).length})""")
            print('2) chamadas ao Tavily sem chave:', len(tav), '(esperado 0)')
            print('3) grounded:', r['grounded'], '| temas:', r['n'])
            assert len(tav)==0, 'chamou o Tavily sem chave'
            assert r['grounded'] is False
            assert 'saíram do conhecimento treinado' in r['texto'], 'não avisou que não houve pesquisa'
            errs=real_errors(errors); assert not errs, errs
            print('\nOK — sem Tavily o app gera mesmo assim, mas avisa em vez de fingir pesquisa')
        finally:
            await browser.close()
asyncio.run(main())
