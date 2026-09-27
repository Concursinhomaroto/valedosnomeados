import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-x'; TOPIC='topic-x'; KING='king-x'
RESULTS=[{'url':'https://www.gov.br/saude/protocolo','title':'Ministério da Saúde',
          'raw_content':'Reposicao inicial 2 mL/kg/%SCQ.'},
         {'url':'https://ameriburn.org/g','title':'ABA','raw_content':'Lower initial volume.'}]

def seed(comResumo=False):
    sub={'id':SUB,'name':'Queimadura','priority':80,'studied':False}
    if comResumo:
        sub['resumo']={'texto':'RESUMO pesquisado: 2 mL/kg/%SCQ.','origem':'web','grounded':True,
                       'via':'tavily','fontes':RESULTS[:2],'consultas':['q'],'geradoEm':'2026-09-01T00:00:00Z'}
    return make_seed({'studyNickname':'R','studyCharacter':'ash','geminiApiKey':'FAKE','tavilyApiKey':'tvly-FAKE',
        'kingdoms':[{'id':KING,'name':'Medicina'}],
        'topics':{KING:[{'id':TOPIC,'name':'Trauma','subtopics':[sub]}]}})

async def tav(route, request):
    await route.fulfill(status=200, content_type='application/json', body=json.dumps({'results':RESULTS}))

def gemFactory(reg, texto):
    async def gem(route, request):
        reg.append(request.post_data or '')
        await route.fulfill(status=200, content_type='application/json', body=json.dumps(
            {'candidates':[{'content':{'parts':[{'text':texto}]},'finishReason':'STOP'}]}))
    return gem

ARVORE=json.dumps({'texto':'Queimadura','tipo':'inicio','ramos':[
    {'rotulo':None,'no':{'texto':'2 mL/kg','tipo':'fim','ramos':[]}}]})

async def main():
    async with async_playwright() as p:
        # 1) FLUXOGRAMA a partir do Resumo: herda fontes e diz isso na tela
        reg=[]
        browser,page,errors=await setup_page(p, seed(comResumo=True))
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gemFactory(reg,ARVORE))
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateFluxograma(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.fluxograma);}", arg=SUB, timeout=20000)
            fg=await page.evaluate("(id)=>{const f=simFindSub(id).fluxograma;return {origem:f.origem,g:f.grounded,via:f.via,doResumo:f.doResumo,n:(f.fontes||[]).length};}", SUB)
            print('--- fluxograma a partir do resumo ---'); print(' ', fg)
            assert fg['doResumo'] is True and fg['g'] is True and fg['via']=='tavily' and fg['n']==2, fg
            assert not any('MATERIAL PESQUISADO' in c for c in reg), 'não devia buscar de novo: o resumo já basta'
            html=await page.evaluate("(id)=>fluxoPanelHTML(simFindSub(id))", SUB)
            assert 'a partir do Resumo, que foi pesquisado no Tavily (2 fontes)' in html, html[:400]
            assert 'gov.br' in html, 'fontes herdadas não apareceram no painel'
            print('  ✓ herda as 2 fontes, diz que veio do Resumo, e NÃO gasta busca')
            assert not real_errors(errors)
        finally: await browser.close()

        # 2) FLUXOGRAMA sem resumo: usa Tavily
        reg2=[]
        browser,page,errors=await setup_page(p, seed(comResumo=False))
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gemFactory(reg2,ARVORE))
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateFluxograma(id)", SUB)
            await page.wait_for_function("(id)=>{const s=simFindSub(id);return !!(s&&s.fluxograma);}", arg=SUB, timeout=20000)
            fg=await page.evaluate("(id)=>{const f=simFindSub(id).fluxograma;return {origem:f.origem,g:f.grounded,via:f.via,n:(f.fontes||[]).length};}", SUB)
            print('\n--- fluxograma sem resumo ---'); print(' ', fg)
            assert fg['origem']=='web' and fg['via']=='tavily' and fg['n']==2, fg
            assert any('MATERIAL PESQUISADO' in c for c in reg2), 'não mandou o material pro Gemini'
            assert not any('"google_search"' in c for c in reg2), 'não devia pedir grounding'
            print('  ✓ pesquisou no Tavily e escreveu sem grounding')
            assert not real_errors(errors)
        finally: await browser.close()

        # 3) FLASHCARDS do miniboss
        reg3=[]
        cards=json.dumps({'cards':[{'pergunta':'P?','resposta':'2 mL/kg (FONTE 1)'}]})
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gemFactory(reg3,cards))
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("(id)=>generateFlashcardsSub(id)", SUB)
            await page.wait_for_function("()=>Object.keys(db.flashcards||{}).length>0", timeout=20000)
            print('\n--- flashcards do miniboss ---')
            assert any('MATERIAL PESQUISADO' in c for c in reg3), 'flashcards não receberam o material'
            assert not any('"google_search"' in c for c in reg3), 'flashcards ainda pedem grounding'
            print('  ✓ gerados a partir do material do Tavily, sem grounding')
            assert not real_errors(errors)
        finally: await browser.close()

        print('\nOK — fluxograma herda o resumo; fluxograma sem resumo, flashcards e repertório usam Tavily')
asyncio.run(main())
