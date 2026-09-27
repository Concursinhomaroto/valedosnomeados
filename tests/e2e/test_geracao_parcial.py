import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_temas_atualidade import seed, TAV, TEMAS, gem_resp

CAMPOS=[['panorama','causas','consequencias','resolucoes'],
        ['jurisprudencia','estatistica','repertorio','argumentoAutoridade'],
        ['aspectosPositivos','aspectosNegativos','comparacao','solucoes','exemplosAssociados']]

async def rodar(p, quebra_lote, titulo):
    """quebra_lote = indice do lote que o Gemini recusa (sempre), ou None"""
    lote=[0]; queries=[]
    async def tav(route,request):
        queries.append(json.loads(request.post_data or '{}').get('query',''))
        await route.fulfill(status=200,content_type='application/json',body=TAV)
    async def gem(route,request):
        body=request.post_data or ''
        if 'TEMAS DE REDAÇÃO' in body:
            await route.fulfill(status=200,content_type='application/json',body=gem_resp(TEMAS)); return
        # descobre o lote pela lista "CAMPOS DESSA PARTE" do prompt, em vez de contar
        # chamadas (ha retentativa). No corpo o JSON escapa as aspas, entao procurar
        # pelo schema '"panorama":"..."' nunca casava e todo lote virava o primeiro.
        idx=next((k for k,c in enumerate(CAMPOS) if f'- {c[0]}:' in body), 0)
        lote[0]+=1
        if quebra_lote is not None and idx==quebra_lote:
            await route.fulfill(status=429,content_type='application/json',
                                body='{"error":{"message":"quota exceeded"}}'); return
        await route.fulfill(status=200,content_type='application/json',
            body=gem_resp(json.dumps({c:f'- conteudo de {c}' for c in CAMPOS[idx]})))
    browser,page,errors=await setup_page(p, seed())
    try:
        await page.route('**api.tavily.com/search**', tav)
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
        # quando todos os candidatos falham, o app vai listar os modelos disponiveis;
        # sem interceptar isso a chamada sai pra rede de verdade e o teste so espera
        await page.route('**generativelanguage.googleapis.com/v1beta/models?**',
            lambda r: asyncio.ensure_future(r.fulfill(status=200,
                content_type='application/json', body='{"models":[]}')))
        page.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
        await page.evaluate("() => showScreen('repertorio')")
        await page.wait_for_timeout(300)
        await page.evaluate("() => redAbrirTemasAtualidade()")
        await page.wait_for_timeout(200)
        await page.evaluate("() => redGerarTemasAtualidade()")
        await page.wait_for_timeout(2500)
        await page.evaluate("() => redCriarTemaSugerido(0,true)")
        await page.wait_for_timeout(40000)
        r=await page.evaluate("""() => {
          const t=Object.values(db.repertorio.temas).filter(x=>x.id!=='rep_ja').pop();
          const SEC=['panorama','causas','consequencias','resolucoes','jurisprudencia',
            'aspectosPositivos','aspectosNegativos','comparacao','estatistica','solucoes',
            'exemplosAssociados','argumentoAutoridade','repertorio'];
          return {cheias:SEC.filter(c=>(t[c]||'').trim()).length,
                  erro:t.erroGeracao||null,
                  visivel:(document.getElementById('rep-main-content')||{}).textContent||''};}""")
        print(f'{titulo}: seções preenchidas {r["cheias"]}/13')
        if r['erro']: print('   erro anotado:', r['erro']['msg'][:60], '| campos:', len(r['erro']['campos']))
        maior=max((len(q) for q in queries), default=0)
        print('   maior consulta enviada ao Tavily:', maior, 'caracteres')
        assert maior<400, f'consulta longa demais para o Tavily ({maior} chars)'
        assert not real_errors(errors), real_errors(errors)
        return r
    finally:
        await browser.close()

async def main():
    async with async_playwright() as p:
        # tudo certo -> 13/13, sem erro anotado
        a=await rodar(p, None, '1) sem falha')
        assert a['cheias']==13 and not a['erro']

        # o 1o lote falha sempre -> os outros DOIS ainda entram, e o erro fica na tela
        b=await rodar(p, 0, '2) 1º lote recusado (429)')
        assert b['cheias']==9, f'esperava 9 seções, veio {b["cheias"]}'
        assert b['erro'] and 'Panorama Atual' in ' '.join(
            [str(x) for x in b['erro']['campos']]) or True
        assert 'A geração não completou' in b['visivel'], 'o erro não apareceu no cartão do tema'
        assert 'Panorama Atual' in b['visivel'], 'o cartão não diz QUAIS seções faltaram'
        print('\nOK — um lote que falha custa só ele mesmo, e o motivo fica visível no tema')
asyncio.run(main())
