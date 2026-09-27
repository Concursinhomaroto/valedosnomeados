import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1';S='s1'
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'TAV',
  'kingdoms':[{'id':K,'name':'Enf','icon':'💉'}],
  'topics':{K:[{'id':T,'name':'U','subtopics':[{'id':S,'name':'Choque','priority':70,'studied':True}]}]}})
LISTA=json.dumps({'models':[
 {'name':'models/gemini-2.5-flash-tts','supportedGenerationMethods':['generateContent']},
 {'name':'models/gemini-pro-vision','supportedGenerationMethods':['generateContent']},
 {'name':'models/text-embedding-004','supportedGenerationMethods':['generateContent']},
 {'name':'models/gemini-4-flash','supportedGenerationMethods':['generateContent']},
]})
FLUXO=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"raizId":"a","nos":{"a":{"texto":"X","opcoes":[]}}}'}]},'finishReason':'STOP'}]})
ANTIGOS=('gemini-3.8-flash','gemini-3.7-flash','gemini-3.6-flash','gemini-flash-latest')

async def rodar(p,status,titulo):
    b,page,errs=await setup_page(p,seed)
    ch=[];nl={'i':0}
    async def gem(route,request):
        m=request.url.split('/models/')[1].split(':')[0]; ch.append(m)
        if m in ANTIGOS:
            await route.fulfill(status=status,content_type='application/json',
                                body=json.dumps({'error':{'code':status,'message':'x'}}))
        else:
            await route.fulfill(status=200,content_type='application/json',body=FLUXO)
    async def lst(route,request):
        nl['i']+=1
        await route.fulfill(status=200,content_type='application/json',body=LISTA)
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
    await page.route('**generativelanguage.googleapis.com/v1beta/models?**', lst)
    await page.route('**api.tavily.com/search**', lambda r: asyncio.ensure_future(r.fulfill(
      status=200,content_type='application/json',body=json.dumps({'results':[
        {'title':'D','url':'https://x.org/a','content':'MATERIAL. '*200}]}))))
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    await page.evaluate("(s)=>generateFluxograma(s,true)",S)
    await page.wait_for_timeout(13000)
    ok=await page.evaluate("(s)=>{const k=db.kingdoms[0],t=db.topics[k.id][0],x=t.subtopics.find(y=>y.id===s);return !!(x.fluxograma&&x.fluxograma.nos);}",S)
    desc=[m for m in ch if m not in ANTIGOS]
    print('%-46s %2d chamadas | lista consultada: %d | descobertos tentados: %s | gerou: %s'%(
        titulo,len(ch),nl['i'],desc or '—',ok))
    await b.close()
    return len(ch),nl['i'],desc,ok

async def main():
    async with async_playwright() as p:
        print('=== 1) modelos SOBRECARREGADOS (503): não faz sentido descobrir ===')
        n,l,d,ok=await rodar(p,503,'   503 em todos os candidatos')
        assert l==0, 'nao pode consultar a lista de modelos por causa de sobrecarga'
        assert not d, f'nao pode tentar modelos descobertos: {d}'
        assert n==4, f'esperava so os 4 candidatos, foram {n}'
        print('   OK — para nos 4 candidatos, sem multiplicar o gasto\n')

        print('=== 2) modelos SEM EXISTIR (404): aí sim a descoberta serve ===')
        n,l,d,ok=await rodar(p,404,'   404 em todos os candidatos')
        assert l>=1, 'com nome obsoleto, precisa consultar a lista'
        assert ok, 'devia achar um modelo novo e gerar'
        assert 'gemini-4-flash' in d, f'devia tentar o modelo novo: {d}'
        proibidos=[m for m in d if any(x in m for x in ('tts','vision','embedding'))]
        assert not proibidos, f'tentou modelo que nao serve: {proibidos}'
        print('   OK — descobre, ignora voz/imagem/embedding e gera\n')
        print('OK')
asyncio.run(main())
