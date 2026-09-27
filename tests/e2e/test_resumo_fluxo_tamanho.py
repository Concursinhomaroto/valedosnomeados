import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
K='k1';T='t1';S='s1'
# texto no formato exato que a IA produz hoje (do print do usuario)
RESUMO=("CONCEITO, ETIOLOGIA E EPIDEMIOLOGIA:\n\n"
 "A esquizofrenia e um transtorno mental grave, cronico e de etiologia complexa e multifatorial,\n"
 "caracterizado por profundas perturbacoes no pensamento (fonte: Boston, 2024).\n\n"
 "Na prática: Um jovem de 19 anos, sem historico previo de internacoes, passa a apresentar queda subita.\n\n\n"
 "CURSO CLINICO, PRODROMOS E PRIMEIRO EPISODIO PSICOTICO:\n\n"
 "O curso da esquizofrenia e dividido em tres fases distintas.\n\n"
 "Na prática: A equipe de enfermagem identifica que um adolescente comecou a proferir frases desconexas.\n")
seed=make_seed({'studyNickname':'Leo','geminiApiKey':'FAKE','tavilyApiKey':'TAV',
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'ok'}],
  'topics':{K:[{'id':T,'name':'Saude Mental','subtopics':[
    {'id':S,'name':'Esquizofrenia','priority':30,'studied':True,
     'resumo':{'texto':RESUMO,'geradoEm':'2026-09-10T10:00:00Z','origem':'web','via':'tavily',
               'grounded':True,'fontes':[{'url':'https://x.gov.br/a','titulo':'A'}],'consultas':[],'diag':[]}},
    {'id':'s2','name':'Bipolar','priority':30}]}]}})
OK=json.dumps({'candidates':[{'content':{'parts':[{'text':'{"texto":"E","tipo":"inicio","ramos":[]}'}]},'finishReason':'STOP'}]})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed)
        cap={}
        async def g(route,request):
            body=json.loads(request.post_data or '{}')
            cap['maxOut']=body.get('generationConfig',{}).get('maxOutputTokens')
            t=body['contents'][0]['parts'][0]['text']
            cap['teto25']='MÁXIMO 25 nós' in t
            cap['semIlimitado']='Não existe limite fixo de nós' not in t
            await route.fulfill(status=200,content_type='application/json',body=OK)
        await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', g)
        await page.route('**api.tavily.com/search**', lambda r: asyncio.ensure_future(
            r.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[]}))))
        await page.evaluate("()=>{try{localStorage.removeItem('vdn_gemini_modelo_ok');}catch(e){}}")
        await page.evaluate("()=>{openFluxo.add('s1');return generateFluxograma('s1');}")
        await page.wait_for_timeout(4000)
        print('--- FLUXOGRAMA')
        print('   maxOutputTokens: %s (era 16384, antes 32768)'%cap.get('maxOut'))
        print('   prompt diz "MAXIMO 25 nos": %s | tirou o "sem limite fixo": %s'%(cap.get('teto25'),cap.get('semIlimitado')))
        cap2=int(cap.get('maxOut') or 0)
        print('   capacidade: ~%d caracteres de JSON (alvo do usuario: 2-3 mil)\n'%(cap2*3.3))

        # renderiza o painel do resumo e mede o espacamento real
        r=await page.evaluate("""(txt)=>{
            const mede=(html,pre)=>{
              const d=document.createElement('div');
              d.className='resumo-body';
              if(pre)d.style.whiteSpace='pre-line';
              d.innerHTML=html;
              d.style.width='900px';
              document.body.appendChild(d);
              const h=Math.round(d.getBoundingClientRect().height);
              const r={h, titulos:d.querySelectorAll('.resumo-h').length,
                       paragrafos:d.querySelectorAll('.resumo-p').length,
                       praticas:d.querySelectorAll('.resumo-pratica').length,
                       titulo1:(d.querySelector('.resumo-h')||{}).textContent||null};
              d.remove(); return r;
            };
            const antes=mede(escapeHtml(txt),true);      // como era: pre-line
            const agora=mede(resumoFormatar(txt),false); // como ficou
            return {antes,agora};
        }""", RESUMO)
        print('--- RESUMO (mesmo texto do print)')
        for k,v in r.items(): print('   %-16s %s'%(k+':',v))
        print('   erros: %s'%[e for e in errs if 'selectedPixTier' not in e])
        await page.screenshot(path='resumo_novo.png',full_page=False)
        await b.close()
asyncio.run(main())
