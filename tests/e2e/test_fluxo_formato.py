import asyncio, json, sys, time
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1'
CARDS={('c%d'%i):{'id':'c%d'%i,'mbId':T,'pergunta':'Pergunta %d?'%i,'resposta':'Resposta %d.'%i} for i in range(1,121)}
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'TAV','flashcards':CARDS,
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'ok'}],
  'topics':{K:[{'id':T,'name':'Saude Mental','subtopics':[
    {'id':'s1','name':'Esquizofrenia','priority':30,'studied':True,
     'resumo':{'texto':'Resumo da esquizofrenia. '*1200,'geradoEm':'2026-09-10T10:00:00Z',
               'origem':'web','via':'tavily','grounded':True,
               'fontes':[{'url':'https://x.gov.br/a','titulo':'A'}],'consultas':[],'diag':[]}},
    {'id':'s2','name':'Transtorno Bipolar','priority':30},
    {'id':'s3','name':'Depressao Maior','priority':30}]}]}})
OK=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"texto":"E","tipo":"inicio","ramos":[]}'}]},'finishReason':'STOP'}]})
E503=json.dumps({'error':{'code':503,'status':'UNAVAILABLE','message':'This model is currently experiencing high demand.'}})

async def roda(p,modo):
    b,page,errs=await setup_page(p,seed)
    ch=[];logs=[]
    page.on('console', lambda m: logs.append(m.text) if m.type=='error' else None)
    estado={'n':0}
    async def g(route,request):
        body=json.loads(request.post_data or '{}')
        txt=body['contents'][0]['parts'][0]['text']
        estado['n']+=1
        ch.append(request.url.split('/models/')[1].split(':')[0])
        if modo=='ok':
            # so devolve JSON se o LEMBRETE FINAL estiver nos ultimos 1500 caracteres
            perto = 'LEMBRETE FINAL DE FORMATO' in txt[-1500:]
            await route.fulfill(status=200,content_type='application/json',
              body=OK if perto else json.dumps({'candidates':[{'content':{'parts':[
                {'text':'P: Qual a definicao?\nR: E um transtorno.'}]},'finishReason':'STOP'}]}))
        elif modo=='503-2':   # 503 nas duas primeiras, ok na terceira
            if estado['n']<3: await route.fulfill(status=503,content_type='application/json',body=E503)
            else: await route.fulfill(status=200,content_type='application/json',body=OK)
        else:                 # sempre responde fora do formato
            await route.fulfill(status=200,content_type='application/json',
              body=json.dumps({'candidates':[{'content':{'parts':[{'text':'Claro! Aqui vai o fluxograma em texto: primeiro...'}]},'finishReason':'STOP'}]}))
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
    await page.route('**api.tavily.com/search**', lambda r: asyncio.ensure_future(
        r.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))))
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    t0=time.time()
    await page.evaluate("()=>{openFluxo.add('s1');return generateFluxograma('s1');}")
    for _ in range(100):
        if await page.evaluate("()=>!fluxoGenerating.has('s1')"): break
        await page.wait_for_timeout(300)
    dt=time.time()-t0
    tem=await page.evaluate("()=>{const x=simFindSub('s1');return !!(x&&x.fluxograma);}")
    await b.close()
    return ch,tem,dt,logs

async def main():
    async with async_playwright() as p:
        print('--- A) o lembrete de formato chega no FIM do prompt (com 120 flashcards + irmaos)')
        ch,tem,dt,_=await roda(p,'ok')
        print('   chamadas: %d %s | gerou: %s'%(len(ch),ch,tem))
        print('   (a IA so devolvia JSON se o lembrete estivesse nos ultimos 1500 chars)\n')

        print('--- B) 503 nas duas primeiras tentativas: tem que repetir, nao desistir')
        ch,tem,dt,_=await roda(p,'503-2')
        print('   chamadas: %d %s | gerou: %s | tempo: %.1fs\n'%(len(ch),ch,tem,dt))

        print('--- C) IA responde fora do formato: o console tem que mostrar o que veio')
        ch,tem,dt,logs=await roda(p,'ruim')
        achou=[l for l in logs if 'fora do formato JSON pedido' in l]
        print('   chamadas: %d | gerou: %s'%(len(ch),tem))
        print('   log com a resposta crua: %s'%(achou[0][:150] if achou else 'NAO REGISTROU'))
asyncio.run(main())
