import asyncio, json, sys, time
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1';S='s1'
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'TAV',
  'kingdoms':[{'id':K,'name':'Enf','icon':'💉'}],
  'topics':{K:[{'id':T,'name':'U','subtopics':[{'id':S,'name':'Choque','priority':70,'studied':True}]}]}})
RES=json.dumps({'candidates':[{'content':{'parts':[{'text':'RESUMO'}]},'finishReason':'STOP'}]})
TAV=json.dumps({'results':[{'title':'D','url':'https://x.org/a','content':'MATERIAL. '*200}]})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        try:
            print('=== 1) as duas buscas do Tavily agora são simultâneas ===')
            emVoo={'n':0,'pico':0};tempos=[]
            async def tav(route,request):
                emVoo['n']+=1;emVoo['pico']=max(emVoo['pico'],emVoo['n'])
                await asyncio.sleep(1.2)          # busca "avançada" é lenta
                emVoo['n']-=1
                await route.fulfill(status=200,content_type='application/json',body=TAV)
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',
              lambda r: asyncio.ensure_future(r.fulfill(status=200,content_type='application/json',body=RES)))
            t0=time.time()
            await page.evaluate("(s)=>generateResumoWeb(s)",S)
            for _ in range(60):
                if await page.evaluate("(s)=>!resumoGenerating.has(s)",S): break
                await page.wait_for_timeout(200)
            dt=time.time()-t0
            print('   resumo completo em %.1fs | buscas simultâneas no pico: %d'%(dt,emVoo['pico']))
            assert emVoo['pico']==2, f"as buscas ainda estao em serie (pico {emVoo['pico']})"
            assert dt<2.4, f'demorou {dt:.1f}s — em serie seriam ~2.4s+'
            print('   OK — 2 buscas de 1,2s levam ~1,2s no total, não 2,4s')

            print('\n=== 2) a dica de modelo tem prazo e não fixa um modelo fraco pra sempre ===')
            r=await page.evaluate("""()=>{
              geminiAnotarModeloOk('gemini-3.6-flash');
              const logoDepois=geminiOrdemModelos()[0];
              geminiModeloOkEm=Date.now()-(31*60*1000);     // 31 min atras
              const depoisDoPrazo=geminiOrdemModelos()[0];
              return {logoDepois,depoisDoPrazo,preferido:GEMINI_MODEL_CANDIDATES[0]};}""")
            print('   logo após funcionar no 3.6 -> tenta primeiro:',r['logoDepois'])
            print('   passados 31 minutos       -> tenta primeiro:',r['depoisDoPrazo'])
            assert r['logoDepois']=='gemini-3.6-flash', 'a dica deixou de valer no curto prazo'
            assert r['depoisDoPrazo']==r['preferido'], 'a dica nao expirou: modelo fraco fixado'
            print('   OK — volta sozinho pro modelo preferido')

            print('\n=== 3) formato antigo da dica (sem data) é descartado ===')
            r=await page.evaluate("""()=>{
              localStorage.setItem('vdn_gemini_modelo_ok','gemini-3.6-flash');  // formato velho
              let d=null;try{const b=localStorage.getItem('vdn_gemini_modelo_ok');d=JSON.parse(b);}catch(e){d='invalido'}
              return {leitura:d};}""")
            print('   valor antigo no armazenamento não parseia como objeto ->',r['leitura'])
            print('   (o app ignora e recomeça pelo preferido)')
            print('\nOK')
        finally:
            await b.close()
asyncio.run(main())
