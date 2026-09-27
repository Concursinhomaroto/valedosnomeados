import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1';S='s1'
RESUMO_TXT='Esquizofrenia: transtorno psicotico cronico. '*400
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'TAV',
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'ok'}],
  'topics':{K:[{'id':T,'name':'Saude Mental','subtopics':[
    {'id':S,'name':'Esquizofrenia','priority':30,'studied':True,
     'resumo':{'texto':RESUMO_TXT,'geradoEm':'2026-09-10T10:00:00Z','origem':'web',
               'via':'tavily','fontes':[],'consultas':[],'diag':[]}}]}]}})
FLUXO=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"raizId":"a","nos":{"a":{"texto":"X","opcoes":[]}}}'}]},'finishReason':'STOP'}]})
def err429(model):
    return json.dumps({'error':{'code':429,'status':'RESOURCE_EXHAUSTED',
      'message':'You exceeded your current quota.','details':[
        {'@type':'type.googleapis.com/google.rpc.QuotaFailure','violations':[
          {'quotaMetric':'generativelanguage.googleapis.com/generate_content_free_tier_requests',
           'quotaId':'GenerateRequestsPerDayPerProjectPerModel-FreeTier',
           'quotaDimensions':{'model':model,'location':'global'},'quotaValue':'20'}]},
        {'@type':'type.googleapis.com/google.rpc.RetryInfo','retryDelay':'12s'}]}})

async def cenario(p, tudo_esgotado):
    b,page,errs=await setup_page(p,make_seed(json.loads(json.dumps(json.loads(seed)))) if False else seed)
    ch=[]
    async def gem(route,request):
        m=request.url.split('/models/')[1].split(':')[0]
        ch.append(m)
        if 'lite' in m and not tudo_esgotado:
            await route.fulfill(status=200,content_type='application/json',body=FLUXO)
        else:
            await route.fulfill(status=429,content_type='application/json',body=err429(m))
    async def tv(route,request):
        await route.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
    await page.route('**api.tavily.com/search**', tv)
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    await page.evaluate("()=>{window.__toasts=[];const o=window.toast;window.toast=function(m,c){window.__toasts.push(m);return o&&o(m,c);};}")
    await page.evaluate("(s)=>{openFluxo.add(s);}",S)
    await page.evaluate("(s)=>generateFluxograma(s)",S)
    await page.wait_for_timeout(9000)
    toasts=await page.evaluate("()=>window.__toasts||[]")
    tem=await page.evaluate("(s)=>{const x=simFindSub(s);return !!(x&&x.fluxograma&&x.fluxograma.nos);}",S)
    await b.close()
    return ch,toasts,tem,errs

async def main():
    async with async_playwright() as p:
        print('=== A) quatro Flash com cota DIARIA estourada, reserva de pe ===')
        ch,toasts,tem,errs=await cenario(p,False)
        for i,m in enumerate(ch,1): print('   %d. %s'%(i,m))
        print('   fluxograma gerado: %s'%tem)
        print('   toasts: %s'%toasts)
        print('   erros de JS: %s'%errs)
        print()
        print('=== B) TUDO esgotado, inclusive a reserva (mensagem ao usuario) ===')
        ch2,toasts2,tem2,errs2=await cenario(p,True)
        print('   chamadas: %d -> %s'%(len(ch2),ch2))
        print('   fluxograma gerado: %s'%tem2)
        for t in toasts2: print('   toast: %s'%t)
        print('   erros de JS: %s'%errs2)
asyncio.run(main())
