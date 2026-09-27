import asyncio, json, sys, time
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1';S='s1'
def seed(tav): return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':tav,
  'kingdoms':[{'id':K,'name':'Enf','icon':'💉'}],
  'topics':{K:[{'id':T,'name':'U','subtopics':[{'id':S,'name':'Choque','priority':70,'studied':True}]}]}})
FLUXO=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"raizId":"a","nos":{"a":{"texto":"X","opcoes":[]}}}'}]},'finishReason':'STOP'}]})
# Tavily VAZIO: e o caso em que o app cai na busca do Gemini — onde estava o estouro
TAV_VAZIO=json.dumps({'results':[]})

async def rodar(p,rpm_simulado,titulo):
    b,page,errs=await setup_page(p,seed('TAV'))
    ch=[];janela=[]
    async def gem(route,request):
        agora=time.time(); janela.append(agora)
        recentes=[t for t in janela if agora-t<60]
        ch.append(request.url.split('/models/')[1].split(':')[0])
        if len(recentes)>rpm_simulado:      # simula o RPM=5 da conta gratuita
            await route.fulfill(status=429,content_type='application/json',
              body=json.dumps({'error':{'code':429,'message':'rate limit'}}))
        else:
            await asyncio.sleep(0.3)
            await route.fulfill(status=200,content_type='application/json',body=FLUXO)
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
    await page.route('**api.tavily.com/search**', lambda r: asyncio.ensure_future(
        r.fulfill(status=200,content_type='application/json',body=TAV_VAZIO)))
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    t0=time.time()
    await page.evaluate("(s)=>generateFluxograma(s,true)",S)
    for _ in range(60):
        if await page.evaluate("(s)=>!fluxoGenerating.has(s)",S): break
        await page.wait_for_timeout(300)
    ok=await page.evaluate("(s)=>{const k=db.kingdoms[0],t=db.topics[k.id][0],x=t.subtopics.find(y=>y.id===s);return !!(x.fluxograma&&x.fluxograma.nos);}",S)
    print('%-52s %d chamada(s) em %.1fs  | GEROU: %s'%(titulo,len(ch),time.time()-t0,ok))
    await b.close()
    return len(ch),ok

async def main():
    async with async_playwright() as p:
        print('Tavily sem resultado -> cai na busca do Gemini (o caminho que estourava)\n')
        n,ok=await rodar(p,5,'   fluxograma, com a conta limitada a 5 por minuto')
        assert ok, 'o fluxograma nao foi gerado'
        assert n==1, f'esperava 1 chamada, foram {n}'
        print('\nOK — 1 chamada, dentro do limite de 5 por minuto, e o fluxograma sai')
asyncio.run(main())
