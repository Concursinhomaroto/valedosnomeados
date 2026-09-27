import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1';S='s1'
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'TAV',
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'ok'}],
  'topics':{K:[{'id':T,'name':'Urgência','subtopics':[
    {'id':S,'name':'Acidente por Cnidários','priority':70,'studied':True,
     'resumo':{'texto':'Cnidários: água-viva e caravela. '*300,'geradoEm':'2026-09-10T10:00:00Z',
               'origem':'web','via':'tavily','grounded':True,'fontes':[],'consultas':[],'diag':[]}},
    {'id':'s2','name':'Choque','priority':30}]}]}})
# exatamente o caso do console: JSON valido que para no meio de uma palavra,
# e finishReason NAO e MAX_TOKENS
CORTADO=json.dumps({'candidates':[{'content':{'parts':[{'text':
  '{"texto":"Acidente por Cnidários (água-viva e caravela)","tipo":"inicio","ramos":[{"rotulo":null,'
  '"no":{"texto":"Diferenciação: caravela é colônia flutuante","tipo":"acao","ramos":[{"rotulo":null,'
  '"no":{"texto":"Não há soro antiveneno no SUS; tratamen'}]},'finishReason':'STOP'}]})
OK=json.dumps({'candidates':[{'content':{'parts':[{'text':
  '{"texto":"Acidente por Cnidários","tipo":"inicio","ramos":[]}'}]},'finishReason':'STOP'}]})
PROSA=json.dumps({'candidates':[{'content':{'parts':[{'text':
  'Claro! O fluxograma para cnidários começa com a diferenciação entre caravela e água-viva...'}]},'finishReason':'STOP'}]})

async def cena(p,modo):
    b,page,errs=await setup_page(p,seed)
    ch=[]
    async def g(route,request):
        body=json.loads(request.post_data or '{}')
        mx=body.get('generationConfig',{}).get('maxOutputTokens')
        m=request.url.split('/models/')[1].split(':')[0]
        ch.append((m,mx))
        if modo=='corta-se-pequeno':
            await route.fulfill(status=200,content_type='application/json',body=(OK if mx>=4096 else CORTADO))
        elif modo=='corta-sempre':
            await route.fulfill(status=200,content_type='application/json',body=CORTADO)
        else:
            await route.fulfill(status=200,content_type='application/json',body=PROSA)
    await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
    await page.route('**api.tavily.com/search**', lambda r: asyncio.ensure_future(
        r.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))))
    await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
    await page.evaluate("()=>{openFluxo.add('s1');return generateFluxograma('s1');}")
    for _ in range(90):
        if await page.evaluate("()=>!fluxoGenerating.has('s1')"): break
        await page.wait_for_timeout(300)
    tem=await page.evaluate("()=>{const x=simFindSub('s1');return !!(x&&x.fluxograma&&x.fluxograma.nos);}")
    await b.close()
    return ch,tem,[e for e in errs if 'selectedPixTier' not in e]

async def main():
    async with async_playwright() as p:
        # o detector, isolado
        b,page,errs=await setup_page(p,seed)
        casos=[('{"a":1}',False,'JSON completo'),
               ('{"a":1,"b":{"c":',True,'cortado no meio'),
               ('{"a":"texto com } dentro"}',False,'chave dentro de string'),
               ('{"a":"aspas \\" escapada"}',False,'aspas escapada (uma barra)'),
               ('{"a":"barra no fim \\\\"}',False,'barra escapada no fim'),
               ('{"a":"sem fechar as aspas',True,'string aberta'),
               ('Claro! Segue o fluxograma...',False,'prosa, não é corte'),
               ('```json\n{"a":1,"b":',True,'com cerca markdown, cortado')]
        print('--- detector jsonPareceCortado')
        for txt,esp,nome in casos:
            got=await page.evaluate("(t)=>jsonPareceCortado(t)",txt)
            print('    %-28s esperado=%-5s obtido=%-5s %s'%(nome,esp,got,'OK' if got==esp else '<<< ERRO'))
        await b.close()

        print('\n--- caso do console: cortado em 2048, cabe em 4096')
        ch,tem,errs=await cena(p,'corta-se-pequeno')
        for i,(m,mx) in enumerate(ch,1): print('    %d. %-18s maxOutputTokens=%s'%(i,m,mx))
        print('    gerou: %s   (antes: erro)'%tem)

        print('\n--- corta em qualquer teto: não pode entrar em laço')
        ch2,tem2,_=await cena(p,'corta-sempre')
        print('    chamadas: %d -> %s'%(len(ch2),[mx for _,mx in ch2]))
        print('    gerou: %s (esperado False, com erro na tela)'%tem2)

        print('\n--- prosa de verdade: NÃO pode gastar chamada dobrando o teto')
        ch3,tem3,_=await cena(p,'prosa')
        print('    chamadas: %d -> %s'%(len(ch3),[mx for _,mx in ch3]))
        print('    erros JS: %s'%errs)
asyncio.run(main())
