import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
K='k1';T='t1';S='s1'
def seed(tav):
    return make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':tav,
      'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
      'topics':{K:[{'id':T,'name':'Urgência','subtopics':[{'id':S,'name':'Choque Séptico','priority':70,'studied':True}]}]}})
GEM=json.dumps({'candidates':[{'content':{'parts':[{'text':'RESUMO ESCRITO'}]},'finishReason':'STOP'}]})
TAV=json.dumps({'results':[{'title':'Diretriz','url':'https://exemplo.org/a','content':'Conteúdo pesquisado sobre choque séptico.'*20}]})

async def rodar(p,tavKey,titulo):
    b,page,errs=await setup_page(p,seed(tavKey))
    gem=[];tav=[]
    async def hg(route,request):
        gem.append(json.loads(request.post_data or '{}').get('tools') and 'COM-BUSCA' or 'sem-busca')
        await route.fulfill(status=200,content_type='application/json',body=GEM)
    async def ht(route,request):
        tav.append(1); await route.fulfill(status=200,content_type='application/json',body=TAV)
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', hg)
    await page.route('**api.tavily.com/search**', ht)
    await page.route('**generativelanguage.googleapis.com/v1beta/models?**', lambda r: asyncio.ensure_future(
        r.fulfill(status=200,content_type='application/json',body='{"models":[]}')))
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    await page.evaluate("(s)=>generateResumoWeb(s)",S)
    await page.wait_for_timeout(5000)
    via=await page.evaluate("(s)=>{const k=db.kingdoms[0];const t=db.topics[k.id][0];const x=t.subtopics.find(y=>y.id===s);return x.resumo?x.resumo.via:null;}",S)
    print('%-30s Tavily: %d busca(s) | Gemini: %d chamada(s) %s | via=%s'%(titulo,len(tav),len(gem),gem,via))
    await b.close()
    return len(tav),len(gem),via

async def main():
    async with async_playwright() as p:
        t1,g1,v1=await rodar(p,'FAKE_TAVILY','COM chave do Tavily')
        t2,g2,v2=await rodar(p,'','SEM chave do Tavily')
        print()
        assert t1>=1 and v1=='tavily', 'com Tavily, a busca tem que sair dele'
        assert g1<g2, 'com Tavily tem que gastar MENOS chamadas do Gemini'
        assert v2=='gemini'
        print('CONFIRMADO: com Tavily -> %d chamada(s) ao Gemini | sem Tavily -> %d'%(g1,g2))
        print('O combinado está implementado: com a chave, o Tavily pesquisa e o Gemini só redige.')
asyncio.run(main())
