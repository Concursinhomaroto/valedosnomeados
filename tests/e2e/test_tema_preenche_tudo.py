import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_temas_atualidade import seed, TAV, TEMAS, gem_resp

CAMPOS=[['panorama','causas','consequencias','resolucoes'],
        ['jurisprudencia','estatistica','repertorio','argumentoAutoridade'],
        ['aspectosPositivos','aspectosNegativos','comparacao','solucoes','exemplosAssociados']]

async def main():
    async with async_playwright() as p:
        prompts=[]; chamada=[0]
        async def tav(route,request): await route.fulfill(status=200,content_type='application/json',body=TAV)
        async def gem(route,request):
            body=request.post_data or ''
            prompts.append(body)
            # 1a chamada = a lista de temas; as seguintes = os lotes de secoes
            if 'TEMAS DE REDAÇÃO' in body:
                await route.fulfill(status=200,content_type='application/json',body=gem_resp(TEMAS)); return
            i=chamada[0]; chamada[0]+=1
            campos=CAMPOS[i] if i<len(CAMPOS) else CAMPOS[-1]
            await route.fulfill(status=200,content_type='application/json',
                body=gem_resp(json.dumps({c:f'- conteudo de {c}' for c in campos})))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            # o confirm() do "ja tem conteudo" foi o que travava tudo: se ele aparecer,
            # o teste recusa, que e o que o navegador faz quando ninguem responde
            page.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
            dialogos=[]
            page.on('dialog', lambda d: dialogos.append(d.message))

            await page.evaluate("() => showScreen('repertorio')")
            await page.wait_for_timeout(300)
            await page.evaluate("() => redAbrirTemasAtualidade()")
            await page.wait_for_timeout(200)
            await page.evaluate("() => redGerarTemasAtualidade()")
            await page.wait_for_timeout(2500)

            await page.evaluate("() => redCriarTemaSugerido(0,true)")
            await page.wait_for_timeout(6000)

            r=await page.evaluate("""() => {
              const t=Object.values(db.repertorio.temas).filter(x=>x.id!=='rep_ja').pop();
              const SEC=['panorama','causas','consequencias','resolucoes','jurisprudencia',
                'aspectosPositivos','aspectosNegativos','comparacao','estatistica','solucoes',
                'exemplosAssociados','argumentoAutoridade','repertorio'];
              return {vazias:SEC.filter(c=>!(t[c]||'').trim()),
                      cheias:SEC.filter(c=>(t[c]||'').trim()).length,
                      ctx:!!t.contextoAtualidade,
                      recorte:(t.contextoAtualidade||{}).recorte||'',
                      iaGerado:!!t.iaGerado};}""")
            print('diálogos de confirmação que apareceram:', dialogos, '(esperado: nenhum)')
            print('seções preenchidas:', r['cheias'], 'de 13 | vazias:', r['vazias'])
            print('contexto da atualidade guardado?', r['ctx'], '| recorte:', repr(r['recorte'][:45]))
            assert not dialogos, f'a geração parou pra perguntar: {dialogos}'
            assert r['cheias']==13, f'só {r["cheias"]} de 13 seções preencheram — faltou {r["vazias"]}'
            assert r['ctx'] and r['recorte']
            assert r['iaGerado']

            # o recorte precisa ter chegado nos TRES lotes, senao a IA escreve sobre
            # o tema em geral e o recorte pesquisado vira enfeite
            lotes=[b for b in prompts if 'RECORTE OBRIGATÓRIO' in b]
            print('lotes que receberam o recorte:', len(lotes), 'de 3')
            assert len(lotes)==3, f'o recorte só chegou em {len(lotes)} dos 3 lotes'
            assert 'Financiamento municipal' in lotes[0]

            # e o recorte fica visivel no cabecalho do tema
            vis=await page.evaluate("""() => (document.getElementById('rep-main-content')||{}).textContent||''""")
            print('cabeçalho mostra "Em pauta porque"?', 'Em pauta porque' in vis)
            assert 'Em pauta porque' in vis and 'Financiamento municipal' in vis

            errs=real_errors(errors); assert not errs, errs
            print('\nOK — tema em pauta nasce com as 13 seções preenchidas e guiadas pelo recorte')
        finally:
            await browser.close()
asyncio.run(main())
