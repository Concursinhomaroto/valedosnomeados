# Chefao inteiro marcado = UMA chamada ao modelo e UMA pesquisa, no lugar de uma por assunto.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

K='k1'

def chefao(i,nome,n):
    return {'id':f't{i}','name':nome,'icon':'⚔️','priority':3,
            'subtopics':[{'id':f's{i}_{j}','name':f'{nome} — assunto {j}','priority':70,'studied':True} for j in range(n)]}

def seed():
    return make_seed({'studyNickname':'R','studyCharacter':'ash','geminiApiKey':'FAKE','tavilyApiKey':'tvly-FAKE',
        'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
        'topics':{K:[chefao(0,'Urgência e Emergência',24),chefao(1,'Vacinação',6)]}})

TAV=json.dumps({'results':[{'url':'https://www.gov.br/x','title':'MS','raw_content':'conteúdo oficial'}]})

def resp(n, com_assunto, lote=0):
    itens=[]
    for i in range(n):
        q={'questao':f'Questão {lote}-{i} sobre o tema?','alternativas':[{'letra':l,'texto':l} for l in 'ABCDE'],
           'correta':'ABCDE'[i%5],'explicacao':'x'}
        if com_assunto: q['assunto']=(i%24)+1
        itens.append(q)
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

async def main():
    async with async_playwright() as pw:
        # ---------- A) chefão inteiro ----------
        print('=== A) chefão inteiro marcado (24 assuntos, 20 questões) ===')
        chamadas=[]; buscas=[]
        async def tav(route, request):
            buscas.append(json.loads(request.post_data or '{}')); 
            await route.fulfill(status=200, content_type='application/json', body=TAV)
        async def gem(route, request):
            corpo=request.post_data or ''
            chamadas.append(corpo)
            n=20 if len(chamadas)==1 else 5
            await route.fulfill(status=200, content_type='application/json', body=resp(n, True, len(chamadas)))
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(400)
            await page.evaluate('''()=>{
              sgToggleChefao('t0',true);
              document.getElementById('sg-qtd').value='20';
              document.getElementById('sg-tempo').value='0';
            }''')
            u=await page.evaluate("()=>({unidades:sgUnidades(),chamadas:document.getElementById('sg-chamadas').textContent,custo:document.getElementById('sg-custo').textContent})")
            print('  previsão na tela:',json.dumps(u,ensure_ascii=False))
            assert u['unidades']==1, u
            assert '1 chamada' in u['chamadas'], u

            await page.evaluate("()=>generateSimuladoGeral()")
            await page.wait_for_function("()=>!!(simGeralActive&&simGeralActive.questoes.length)",timeout=60000)
            r=await page.evaluate('''()=>({n:simGeralActive.questoes.length,
              assuntos:[...new Set(simGeralActive.questoes.map(q=>q.subName))].length,
              todasComSub:simGeralActive.questoes.every(q=>!!q.subId&&!!q.subName),
              sobrou:simGeralActive.questoes.some(q=>'_sub' in q || 'assunto' in q)})''')
            print(f"  chamadas ao modelo: {len(chamadas)} | buscas no Tavily: {len(buscas)}")
            print(f"  questões: {r['n']} | assuntos distintos atribuídos: {r['assuntos']}")
            assert len(chamadas)==1, f'esperava 1 chamada, veio {len(chamadas)}'
            assert len(buscas)==2, f'esperava 2 buscas (uma pesquisa), veio {len(buscas)}'
            assert r['n']==20, r
            assert r['todasComSub'], 'questão sem assunto atribuído'
            assert not r['sobrou'], 'campo interno vazou para a questão salva'
            assert r['assuntos']>=5, f'a distribuição concentrou tudo em {r["assuntos"]} assunto(s)'
            corpo=chamadas[0]
            assert 'TEMA CENTRAL' in corpo and 'ASSUNTOS QUE COMP' in corpo, 'prompt não é do tema'
            assert 'assunto 23' in corpo, 'a lista de assuntos não foi para o prompt'
            print('  ✓ 1 chamada + 1 pesquisa cobriram o chefão, com atribuição por assunto')

            # comparação com o custo do jeito antigo
            print(f"  antes seriam 24 chamadas e 48 buscas — economia de {24-len(chamadas)} chamadas e {48-len(buscas)} buscas")
            assert not real_errors(errors), real_errors(errors)
        finally:
            await browser.close()

        # ---------- B) assuntos soltos ----------
        print('\n=== B) 3 assuntos soltos do mesmo chefão ===')
        chamadas2=[]; buscas2=[]
        async def tav2(route, request):
            buscas2.append(1); await route.fulfill(status=200, content_type='application/json', body=TAV)
        async def gem2(route, request):
            chamadas2.append(request.post_data or '')
            await route.fulfill(status=200, content_type='application/json', body=resp(4, False, len(chamadas2)))
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.route('**api.tavily.com/search**', tav2)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem2)
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(400)
            await page.evaluate('''()=>{
              ['s0_0','s0_1','s0_2'].forEach(id=>simGeralConfig.selectedSubIds.add(id));
              renderSimGeralScreen();
              document.getElementById('sg-qtd').value='10';
              document.getElementById('sg-tempo').value='0';
            }''')
            u=await page.evaluate("()=>sgUnidades()")
            print('  unidades previstas:',u)
            assert u==3, u
            await page.evaluate("()=>generateSimuladoGeral()")
            await page.wait_for_function("()=>!!(simGeralActive&&simGeralActive.questoes.length)",timeout=60000)
            print(f"  chamadas: {len(chamadas2)} | buscas: {len(buscas2)}")
            print('  (10 questões em 3 unidades: 4+3+3)')
            assert len(chamadas2)==3, len(chamadas2)
            assert 'MINIBOSS/ASSUNTO ESPECÍFICO' in chamadas2[0], 'devia ser o prompt por assunto'
            assert 'TEMA CENTRAL' not in chamadas2[0]
            print('  ✓ seleção parcial continua assunto a assunto, com o prompt específico')
            assert not real_errors(errors), real_errors(errors)
        finally:
            await browser.close()

        # ---------- C) mais unidades que questões ----------
        print('\n=== C) 30 assuntos soltos, 10 questões pedidas ===')
        chamadas3=[]
        async def gem3(route, request):
            chamadas3.append(1)
            await route.fulfill(status=200, content_type='application/json', body=resp(1, False, len(chamadas3)))
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.route('**api.tavily.com/search**', lambda r,q: asyncio.ensure_future(r.fulfill(status=200,content_type='application/json',body=TAV)))
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem3)
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(400)
            # 23 dos 24 assuntos do t0 (parcial, pra nao agrupar) + os 6 do t1
            await page.evaluate('''()=>{
              for(let j=0;j<23;j++)simGeralConfig.selectedSubIds.add('s0_'+j);
              for(let j=0;j<6;j++)simGeralConfig.selectedSubIds.add('s1_'+j);
              renderSimGeralScreen();
              document.getElementById('sg-qtd').value='10';
              document.getElementById('sg-tempo').value='0';
              document.getElementById('sg-pesquisar').checked=false;
            }''')
            await page.evaluate("()=>generateSimuladoGeral()")
            await page.wait_for_function("()=>!!(simGeralActive&&simGeralActive.questoes.length)",timeout=90000)
            n=await page.evaluate("()=>simGeralActive.questoes.length")
            print(f"  chamadas: {len(chamadas3)} | questões entregues: {n} (pedidas: 10)")
            assert n==10, f'pediu 10 e veio {n}'
            assert len(chamadas3)==10, f'esperava 10 chamadas, veio {len(chamadas3)}'
            print('  ✓ pediu 10, veio 10 — antes vinham 29, uma por assunto')
            assert not real_errors(errors), real_errors(errors)
        finally:
            await browser.close()

        print('\nOK — chefão inteiro em uma chamada, assunto solto direcionado, e a quantidade pedida respeitada')
asyncio.run(main())
