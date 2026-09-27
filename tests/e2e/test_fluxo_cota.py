# Caso real: UMA tentativa de fluxograma queimou 8 requisicoes (2+3+3 no painel da Google)
# e nao entregou nada. Duas causas somadas:
#  1) teto de saida de 2048 no fluxograma. Os Gemini 3.x PENSAM antes de responder e os
#     tokens de raciocinio saem desse mesmo teto — a resposta vinha cortada SEMPRE.
#  2) 503 e falha DA GOOGLE mas conta na SUA cota. Insistir 3x no mesmo modelo
#     sobrecarregado queima 3 requisicoes pra saber o que a primeira ja disse.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1'
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'',
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💊'}],
  'topics':{K:[{'id':T,'name':'Urgencia','subtopics':[
    {'id':'s1','name':'Choque','priority':30,'studied':True,
     'resumo':{'texto':'Resumo do choque. '*200,'geradoEm':'2026-09-10T10:00:00Z','origem':'web'}}]}]}})
OK=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"texto":"Suspeita","tipo":"inicio","ramos":[]}'}]},'finishReason':'STOP'}]})
E503=json.dumps({'error':{'code':503,'status':'UNAVAILABLE','message':'This model is currently experiencing high demand.'}})

async def roda(p,modo):
    b,page,errs=await setup_page(p,seed)
    ch=[]
    async def g(route,request):
        body=json.loads(request.post_data or '{}')
        modelo=request.url.split('/models/')[1].split(':')[0]
        teto=(body.get('generationConfig') or {}).get('maxOutputTokens')
        ch.append({'m':modelo,'teto':teto})
        if modo=='tudo503':
            await route.fulfill(status=503,content_type='application/json',body=E503)
        elif modo=='primeiro503':     # 3.8 fora, 3.7 de pe
            if '3.8' in modelo: await route.fulfill(status=503,content_type='application/json',body=E503)
            else: await route.fulfill(status=200,content_type='application/json',body=OK)
        else:
            await route.fulfill(status=200,content_type='application/json',body=OK)
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
    await page.route('**api.tavily.com/**', lambda r: asyncio.ensure_future(
        r.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))))
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    await page.evaluate("()=>{openFluxo.add('s1');return generateFluxograma('s1');}")
    for _ in range(120):
        if await page.evaluate("()=>!fluxoGenerating.has('s1')"): break
        await page.wait_for_timeout(200)
    gerou=await page.evaluate("()=>{const x=simFindSub('s1');return !!(x&&x.fluxograma);}")
    await b.close()
    return ch,gerou

async def main():
    async with async_playwright() as p:
        print('=== A) o teto do fluxograma tem espaco pro raciocinio ===')
        ch,gerou=await roda(p,'ok')
        print('   chamadas: %d · teto pedido: %s · gerou: %s'
              %(len(ch),sorted(set(c['teto'] for c in ch)),gerou))
        assert gerou and all(c['teto']>=8192 for c in ch), ch
        assert len(ch)==1, ('sucesso tem que custar 1 chamada',ch)
        print('   OK — 2048 era o teto de antes, e o raciocinio sozinho ja o estourava\n')

        print('=== B) um modelo em 503 nao queima 3 requisicoes ===')
        ch2,gerou2=await roda(p,'primeiro503')
        print('   chamadas: %s'%[c['m'] for c in ch2])
        print('   gerou: %s'%gerou2)
        assert gerou2, ch2
        n38=len([c for c in ch2 if '3.8' in c['m']])
        print('   tentativas no modelo sobrecarregado: %d (antes eram 3)'%n38)
        assert n38==1, ch2
        assert len(ch2)==2, ch2
        print('   OK — passa pro vizinho na hora, em vez de insistir\n')

        print('=== C) com TODOS fora: uma tentativa por modelo + a reserva, e acabou ===')
        ch3,gerou3=await roda(p,'tudo503')
        modelos=[c['m'] for c in ch3]
        print('   total de chamadas: %d'%len(ch3))
        print('   sequencia: %s'%modelos)
        print('   gerou: %s (esperado False)'%gerou3)
        assert not gerou3
        # 3 Flash + o Lite. O Lite entra no 503 porque e outro pool de capacidade — era
        # o que faltava pro fluxograma sair quando os Flash enchem.
        assert len(set(modelos))==4, modelos
        assert modelos[-1]=='gemini-flash-lite-latest', modelos
        assert len(ch3)<=4, ('com tudo fora, uma tentativa por modelo e ponto',modelos)
        print('   cada modelo tentado UMA vez: sim · nenhuma repeticao')
        print('   (o caso real custou 8; a versao com repeticao chegava a 12)\n')

        print('OK')

asyncio.run(main())
