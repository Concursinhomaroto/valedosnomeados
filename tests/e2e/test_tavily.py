import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-t1'; TOPIC='topic-t1'; KING='king-t1'

def seed(tavily=True, oficial=True):
    extra={'studyNickname':'Reitor','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Medicina'}],
        'topics':{KING:[{'id':TOPIC,'name':'Trauma','subtopics':[
            {'id':SUB,'name':'Paciente com queimadura','priority':80,'studied':False}]}]}}
    if tavily: extra['tavilyApiKey']='tvly-FAKE'
    extra['tavilySoOficial']=oficial
    return make_seed(extra)

async def main():
    async with async_playwright() as p:
        # ---------- 1) com Tavily: busca lá, escreve no Gemini SEM grounding ----------
        buscas=[]; geracoes=[]
        async def tav(route, request):
            buscas.append(json.loads(request.post_data or '{}'))
            await route.fulfill(status=200, content_type='application/json', body=json.dumps({'results':[
                {'url':'https://www.gov.br/saude/protocolo-queimados','title':'Ministério da Saúde',
                 'raw_content':'A reposicao inicial passou a 2 mL/kg/%SCQ nas primeiras 24h.'},
                {'url':'https://ameriburn.org/guideline','title':'ABA Guideline',
                 'raw_content':'Lower initial volume recommended.'}]}))
        async def gem(route, request):
            geracoes.append(request.post_data or '')
            await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                {'candidates':[{'content':{'parts':[{'text':'RESUMO: 2 mL/kg/%SCQ (FONTE 1).'}]},'finishReason':'STOP'}]}))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateResumoWeb(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.resumo&&s.resumo.texto);}", arg=SUB, timeout=20000)
            r=await page.evaluate("(id)=>{const s=simFindSub(id);return {via:s.resumo.via,g:s.resumo.grounded,f:s.resumo.fontes,c:s.resumo.consultas};}", SUB)
            print('--- com Tavily ---')
            print('  via:',r['via'],'| grounded:',r['g'],'| fontes:',len(r['f']))
            print('  consultas:', r['c'])
            assert r['via']=='tavily' and r['g'] is True, r
            assert len(r['f'])==2, r['f']
            assert len(buscas)==2, f'esperava 2 buscas, veio {len(buscas)}'
            # a 1a busca é restrita a fonte oficial e profunda; a 2a é ampla
            assert 'include_domains' in buscas[0] and 'gov.br' in buscas[0]['include_domains'], buscas[0]
            assert buscas[0]['search_depth']=='advanced', buscas[0]
            assert 'include_domains' not in buscas[1], buscas[1]
            assert str(__import__('datetime').date.today().year) in buscas[0]['query'], buscas[0]['query']
            print('  ✓ 1a busca só em fonte oficial, 2a ampla, ambas com o ano corrente')
            # o Gemini foi chamado SEM a ferramenta de busca, e recebeu o material
            assert len(geracoes)==1, f'esperava 1 chamada ao Gemini, veio {len(geracoes)}'
            corpo=geracoes[0]
            assert '"google_search"' not in corpo, 'não devia pedir grounding quando o Tavily já buscou'
            assert 'MATERIAL PESQUISADO NA INTERNET AGORA' in corpo
            assert '2 mL/kg/%SCQ' in corpo, 'o texto das páginas não chegou ao Gemini'
            assert 'o material ACIMA vence' in corpo
            print('  ✓ Gemini chamado sem grounding, com o material e a regra de precedência')
            assert not real_errors(errors)
        finally:
            await browser.close()

        # ---------- 2) Tavily falhando: cai pro Gemini e mostra o erro ----------
        async def tavErro(route, request):
            await route.fulfill(status=401, content_type='application/json',
                body=json.dumps({'detail':{'error':'Invalid API key'}}))
        async def gemSemBusca(route, request):
            await route.fulfill(status=200, content_type='application/json', body=json.dumps(
                {'candidates':[{'content':{'parts':[{'text':'resumo de memoria'}]},'finishReason':'STOP'}]}))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**api.tavily.com/search**', tavErro)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gemSemBusca)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateResumoWeb(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.resumo&&s.resumo.texto);}", arg=SUB, timeout=25000)
            r=await page.evaluate("(id)=>{const s=simFindSub(id);return {g:s.resumo.grounded,diag:s.resumo.diag};}", SUB)
            print('\\n--- Tavily com chave inválida ---')
            for d in r['diag'][:3]: print('   -',d['modelo'],'->',str(d['erro'])[:80])
            assert r['g'] is False
            assert any(d['modelo']=='tavily' and '401' in str(d['erro']) for d in r['diag']), r['diag']
            print('  ✓ erro do Tavily aparece no diagnóstico e o resumo ainda sai')
            assert not real_errors(errors)
        finally:
            await browser.close()

        # ---------- 3) sem chave do Tavily: nada muda ----------
        chamouTavily={'n':0}
        async def tavProibido(route, request):
            chamouTavily['n']+=1; await route.abort()
        browser,page,errors=await setup_page(p, seed(tavily=False))
        try:
            await page.route('**api.tavily.com/**', tavProibido)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gemSemBusca)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateResumoWeb(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.resumo&&s.resumo.texto);}", arg=SUB, timeout=25000)
            assert chamouTavily['n']==0, 'chamou o Tavily sem chave configurada'
            print('\\n--- sem chave do Tavily ---')
            print('  ✓ não chama o Tavily, comportamento antigo intacto')
            assert not real_errors(errors)
        finally:
            await browser.close()

        print('\\nOK — Tavily pesquisa, Gemini redige só do material, e tudo degrada sem quebrar')
asyncio.run(main())
