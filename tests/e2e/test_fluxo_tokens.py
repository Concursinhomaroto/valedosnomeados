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
OK=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"raizId":"a","nos":{"a":{"texto":"X","opcoes":[]}}}'}]},'finishReason':'STOP'}]})
CUT=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"texto":"inicio","tipo":"inicio","ramos":[{"rotulo":null,"no":{"tex'}]},'finishReason':'MAX_TOKENS'}]})

async def cenario(p, precisa):
    b,page,errs=await setup_page(p,seed)
    ch=[]
    async def gem(route,request):
        body=json.loads(request.post_data or '{}')
        mx=body.get('generationConfig',{}).get('maxOutputTokens')
        m=request.url.split('/models/')[1].split(':')[0]
        ch.append((m,mx))
        # o assunto so cabe se o teto pedido for >= `precisa`
        await route.fulfill(status=200,content_type='application/json',
                            body=(OK if mx>=precisa else CUT))
    async def tv(route,request):
        await route.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
    await page.route('**api.tavily.com/search**', tv)
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    await page.evaluate("(s)=>{openFluxo.add(s);}",S)
    await page.evaluate("(s)=>generateFluxograma(s)",S)
    await page.wait_for_timeout(8000)
    tem=await page.evaluate("(s)=>{const x=simFindSub(s);return !!(x&&x.fluxograma&&x.fluxograma.nos);}",S)
    await b.close()
    return ch,tem

async def main():
    async with async_playwright() as p:
        for nome,precisa in [('fluxograma normal (cabe no teto de 25 nos)',2048),
                             ('fluxograma GRANDE (so cabe no dobro)',4096)]:
            ch,tem=await cenario(p,precisa)
            print('%s' % nome)
            for i,(m,mx) in enumerate(ch,1):
                print('   %d. %-24s maxOutputTokens=%s'%(i,m,mx))
            reserva=sum(mx for _,mx in ch)
            print('   gerou: %s | chamadas: %d | tokens de saida RESERVADOS no total: %s\n'%(tem,len(ch),reserva))
asyncio.run(main())
