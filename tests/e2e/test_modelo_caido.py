import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
K='k1';T='t1';S='s1'
def seed(tav=''):
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':tav,
      'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
      'topics':{K:[{'id':T,'name':'Urgência','subtopics':[
        {'id':S,'name':'Choque Séptico','priority':70,'studied':True}]}]}})
FLUXO=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"raizId":"a","nos":{"a":{"texto":"OK","opcoes":[]}}}'}]},'finishReason':'STOP'}]})
RESUMO=json.dumps({'candidates':[{'content':{'parts':[{'text':'RESUMO COM O MATERIAL'}]},'finishReason':'STOP'}]})
def erro(code,msg): return json.dumps({'error':{'code':code,'message':msg}})

async def cenario(p,titulo,caidos,status,tav='',qual='fluxo'):
    b,page,errs=await setup_page(p,seed(tav))
    vistos=[]
    async def gem(route,request):
        m=request.url.split('/models/')[1].split(':')[0]
        vistos.append(m)
        if m in caidos:
            await route.fulfill(status=status,content_type='application/json',body=erro(status,'indisponivel'))
        else:
            await route.fulfill(status=200,content_type='application/json',
                                body=FLUXO if qual=='fluxo' else RESUMO)
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
    await page.route('**generativelanguage.googleapis.com/v1beta/models?**', lambda r: asyncio.ensure_future(
        r.fulfill(status=200,content_type='application/json',body='{"models":[]}')))
    await page.route('**api.tavily.com/search**', lambda r: asyncio.ensure_future(r.fulfill(
        status=200,content_type='application/json',body=json.dumps({'results':[
          {'title':'D','url':'https://x.org/a','content':'MATERIAL PESQUISADO. '*80}]}))))
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    if qual=='fluxo':
        await page.evaluate("(s)=>generateFluxograma(s,true)",S); await page.wait_for_timeout(11000)
        ok=await page.evaluate("(s)=>{const k=db.kingdoms[0],t=db.topics[k.id][0],x=t.subtopics.find(y=>y.id===s);return !!(x.fluxograma&&x.fluxograma.nos);}",S)
    else:
        await page.evaluate("(s)=>generateResumoWeb(s)",S); await page.wait_for_timeout(11000)
        ok=await page.evaluate("(s)=>{const k=db.kingdoms[0],t=db.topics[k.id][0],x=t.subtopics.find(y=>y.id===s);return !!(x.resumo&&x.resumo.texto);}",S)
    alcancou=[m for m in ['gemini-3.8-flash','gemini-3.7-flash','gemini-3.6-flash','gemini-flash-latest'] if m in vistos]
    print('%-52s gerou: %-5s | modelos tentados: %s'%(titulo,ok,[m.replace('gemini-','') for m in alcancou]))
    await b.close()
    return ok

async def main():
    async with async_playwright() as p:
        print('Cenário da tela do usuário: modelos novos fora do ar, 3.6 de pé\n')
        r1=await cenario(p,'FLUXOGRAMA · 3.8 e 3.7 em 503',['gemini-3.8-flash','gemini-3.7-flash'],503)
        r2=await cenario(p,'RESUMO com Tavily · 3.8 e 3.7 em 503',['gemini-3.8-flash','gemini-3.7-flash'],503,'TAV','resumo')
        r3=await cenario(p,'FLUXOGRAMA · 3.8 e 3.7 em 429 (cota por modelo)',['gemini-3.8-flash','gemini-3.7-flash'],429)
        r4=await cenario(p,'FLUXOGRAMA · só a 3.8 caída',['gemini-3.8-flash'],503)
        assert r1 and r2 and r3 and r4, (r1,r2,r3,r4)
        print('\nOK — em todos, o app alcança o modelo que está de pé e a geração completa')
asyncio.run(main())
