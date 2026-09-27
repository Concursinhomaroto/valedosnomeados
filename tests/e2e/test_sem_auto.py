import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1'
CARDS={('c%d'%i):{'id':'c%d'%i,'mbId':T,'pergunta':'P%d?'%i,'resposta':'R%d.'%i} for i in range(1,11)}
def seed(com_resumo):
    s1={'id':'s1','name':'Esquizofrenia','priority':30}
    if com_resumo:
        s1['studied']=True
        s1['resumo']={'texto':'Resumo especifico da esquizofrenia. '*200,'geradoEm':'2026-09-10T10:00:00Z',
                      'origem':'web','via':'tavily','grounded':True,
                      'fontes':[{'url':'https://x.gov.br/a','titulo':'A'}],'consultas':[],'diag':[]}
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'TAV','flashcards':CARDS,
      'kingdoms':[{'id':K,'name':'Enfermagem','icon':'ok'}],
      'topics':{K:[{'id':T,'name':'Saude Mental','subtopics':[s1,
        {'id':'s2','name':'Transtorno Bipolar','priority':30},
        {'id':'s3','name':'Depressao Maior','priority':30}]}]}})
OK=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"texto":"E","tipo":"inicio","ramos":[]}'}]},'finishReason':'STOP'}]})

async def roda(p,com_resumo,acao,espera=6000):
    b,page,errs=await setup_page(p,seed(com_resumo))
    gem=[];tav=[]
    async def g(route,request):
        body=json.loads(request.post_data or '{}')
        txt=body['contents'][0]['parts'][0]['text']
        gem.append({'irmaos':'CADA UM TEM O FLUXOGRAMA DELE' in txt,'cards':'FLASHCARDS QUE O ALUNO' in txt})
        await route.fulfill(status=200,content_type='application/json',body=OK)
    async def t(route,request):
        tav.append(1)
        await route.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
    await page.route('**api.tavily.com/search**', t)
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    await page.evaluate(acao)
    await page.wait_for_timeout(espera)
    est=await page.evaluate("()=>{const x=simFindSub('s1');return {studied:!!x.studied,fluxo:!!x.fluxograma,resumo:!!x.resumo};}")
    await b.close()
    return gem,len(tav),est,[e for e in errs if 'selectedPixTier' not in e]

async def main():
    async with async_playwright() as p:
        print('--- A) clicar "Estudar" num miniboss NOVO (nao pode gerar nada sozinho)')
        gem,tav,est,errs=await roda(p,False,"()=>{currentKingdom=db.kingdoms[0];return toggleTimer('s1','t1');}")
        print('   chamadas ao Gemini: %d   buscas no Tavily: %d'%(len(gem),tav))
        print('   marcou como estudado: %s | criou resumo: %s | criou fluxograma: %s'%(est['studied'],est['resumo'],est['fluxo']))
        print('   erros: %s\n'%errs)

        print('--- B) botao manual do FLUXOGRAMA (miniboss com resumo) continua funcionando')
        gem,tav,est,errs=await roda(p,True,"()=>{openFluxo.add('s1');return generateFluxograma('s1');}")
        print('   chamadas ao Gemini: %d   buscas no Tavily: %d'%(len(gem),tav))
        print('   gerou fluxograma: %s | flashcards no prompt: %s | trava de irmaos: %s'%(
            est['fluxo'],any(c['cards'] for c in gem),any(c['irmaos'] for c in gem)))
        print('   erros: %s\n'%errs)

        print('--- C) botao manual do RESUMO continua funcionando')
        gem,tav,est,errs=await roda(p,False,"()=>{openResumo.add('s1');return generateResumoWeb('s1');}")
        print('   chamadas ao Gemini: %d   buscas no Tavily: %d'%(len(gem),tav))
        print('   gerou resumo: %s | gerou fluxograma junto: %s (tem que ser False)'%(est['resumo'],est['fluxo']))
        print('   erros: %s'%errs)
asyncio.run(main())
