import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-d1'; TOPIC='topic-d1'; KING='king-d1'

def seed():
    return make_seed({'studyNickname':'Reitor','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Medicina'}],
        'topics':{KING:[{'id':TOPIC,'name':'Trauma','subtopics':[
            {'id':SUB,'name':'Queimadura','priority':80,'studied':False}]}]}})

async def roda(p, responder, rotulo):
    browser,page,errors=await setup_page(p, seed())
    try:
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', responder)
        await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
        await page.evaluate("(id)=>generateResumoWeb(id)", SUB)
        await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.resumo&&s.resumo.texto);}", arg=SUB, timeout=20000)
        r=await page.evaluate("""(id)=>{const s=simFindSub(id);return {
            grounded:s.resumo.grounded, diag:s.resumo.diag,
            html:fontesHTML(s.resumo.fontes,s.resumo.consultas,s.resumo.diag)};}""", SUB)
        print(f'--- {rotulo} ---')
        print('  grounded:', r['grounded'])
        for d in (r['diag'] or []): print('   -', d['modelo'], '->', d['erro'])
        assert r['grounded'] is False
        assert r['diag'], 'não guardou o motivo'
        assert 'Por que não pesquisou' in r['html'], r['html'][:200]
        return r
    finally:
        await browser.close()

async def main():
    async with async_playwright() as p:
        # (a) o caso real: nomes novos dão 404 e o que sobra responde SEM busca.
        #     É o que acontece com lista de modelos desatualizada.
        async def misto(route, request):
            url=request.url
            if 'gemini-3.8' in url or 'gemini-3.7' in url:
                await route.fulfill(status=404, content_type='application/json',
                    body=json.dumps({'error':{'message':'models/x is not found for API version v1beta'}}))
            else:
                await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                    {'candidates':[{'content':{'parts':[{'text':'resumo de memoria'}]},'finishReason':'STOP'}]}))
        r=await roda(p, misto, 'uns 404, o resto responde sem busca')
        assert any('404' in d['erro'] for d in r['diag']), r['diag']
        assert any('não usou a busca' in d['erro'] for d in r['diag']), r['diag']

        # (b) chave sem a busca liberada: 403 só quando a chamada leva a
        #     ferramenta de busca; sem ela, a mesma chave responde normalmente.
        async def r403(route, request):
            corpo=request.post_data or ''
            if 'google_search' in corpo:
                await route.fulfill(status=403, content_type='application/json',
                    body=json.dumps({'error':{'message':'Search Grounding is not supported for this API key'}}))
            else:
                await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                    {'candidates':[{'content':{'parts':[{'text':'resumo sem busca'}]},'finishReason':'STOP'}]}))
        r=await roda(p, r403, 'busca bloqueada na chave (403)')
        assert any('403' in d['erro'] or 'Grounding' in d['erro'] for d in r['diag']), r['diag']

        # (c) responde bem, mas sem groundingMetadata (o modelo optou por não buscar)
        async def semBusca(route, request):
            await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                {'candidates':[{'content':{'parts':[{'text':'resumo de memória'}]},'finishReason':'STOP'}]}))
        r=await roda(p, semBusca, 'modelo respondeu sem usar a busca')
        assert any('não usou a busca' in d['erro'] for d in r['diag']), r['diag']

        # (c2) 429 só nas chamadas com busca: para na primeira, não queima as outras
        chamadas={'busca':0,'sem':0}
        async def r429(route, request):
            corpo=request.post_data or ''
            if 'google_search' in corpo:
                chamadas['busca']+=1
                await route.fulfill(status=429, content_type='application/json',
                    body=json.dumps({'error':{'message':'You exceeded your current quota'}}))
            else:
                chamadas['sem']+=1
                await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                    {'candidates':[{'content':{'parts':[{'text':'resumo sem busca'}]},'finishReason':'STOP'}]}))
        r=await roda(p, r429, 'quota estourada só na busca (429)')
        print('  chamadas COM busca:', chamadas['busca'], '| SEM busca:', chamadas['sem'])
        assert chamadas['busca']==1, f"devia parar na 1a chamada com busca, fez {chamadas['busca']}"
        assert any('quota é da chave' in d['erro'] for d in r['diag']), r['diag']

        # (d) 400 no google_search e OK no google_search_retrieval -> tem que virar grounded
        estado={'n':0}
        async def alterna(route, request):
            corpo=request.post_data or ''
            if '"google_search"' in corpo:
                await route.fulfill(status=400, content_type='application/json',
                    body=json.dumps({'error':{'message':'Unknown name "google_search"'}}))
            else:
                await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                    {'candidates':[{'content':{'parts':[{'text':'resumo com busca'}]},'finishReason':'STOP',
                      'groundingMetadata':{'webSearchQueries':['q'],
                        'groundingChunks':[{'web':{'uri':'https://gov.br/x','title':'Oficial'}}]}}]}))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', alterna)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateResumoWeb(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.resumo&&s.resumo.texto);}", arg=SUB, timeout=20000)
            r=await page.evaluate("(id)=>{const s=simFindSub(id);return {g:s.resumo.grounded,f:s.resumo.fontes};}", SUB)
            print('--- nome antigo da ferramenta (google_search_retrieval) ---')
            print('  grounded:', r['g'], '| fontes:', len(r['f']))
            assert r['g'] is True and len(r['f'])==1, r
            print('  ✓ caiu no nome alternativo e a busca funcionou')
            assert not real_errors(errors)
        finally:
            await browser.close()

        print('\nOK — todo caminho de falha da busca agora tem motivo visível')
asyncio.run(main())
