import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-s1'; SUB2='sub-s2'; TOPIC='topic-s1'; KING='king-s1'

def seed(tavily=True, muitos=0):
    subs=[{'id':SUB,'name':'Choque Distributivo (Séptico)','priority':100,'studied':True},
          {'id':SUB2,'name':'Trauma Cranioencefálico','priority':100,'studied':True}]
    # lista longa de verdade: e so com ela que o max-height da caixa aperta e o
    # botao de ampliar tem o que ampliar (foi o que o usuario mandou na captura)
    subs+=[{'id':f'sx{i}','name':f'Assunto longo de urgência e emergência número {i}',
            'priority':70,'studied':True} for i in range(muitos)]
    extra={'studyNickname':'Reitor','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Urgência e Emergência','subtopics':subs}]}}
    if tavily: extra['tavilyApiKey']='tvly-FAKE'
    return make_seed(extra)

def resp_ce(n):
    itens=[{'afirmacao':f'Afirmação {i+1} sobre choque séptico.',
            'gabarito':'C' if i%2 else 'E','explicacao':f'Porque {i+1}.'} for i in range(n)]
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

def resp_mult(n):
    itens=[{'questao':f'Questão {i+1}?','alternativas':[{'letra':l,'texto':l} for l in 'ABCDE'],
            'correta':'ABCDE'[i%5],'explicacao':'x'} for i in range(n)]
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

TAV=json.dumps({'results':[
    {'url':'https://www.gov.br/saude/sepse','title':'Ministério da Saúde',
     'raw_content':'Bundle de 1 hora: lactato, hemocultura, antibiótico e 30 mL/kg de cristaloide.'},
    {'url':'https://www.sbait.org.br/sepse','title':'SBAIT','raw_content':'Meta de PAM 65 mmHg.'}]})

async def main():
    async with async_playwright() as p:

        # ===== 1) certo/errado + muito difícil + Tavily =====
        print('=== 1) certo/errado, muito difícil, com pesquisa ===')
        buscas=[]; prompts=[]
        async def tav(route, request):
            buscas.append(json.loads(request.post_data or '{}'))
            await route.fulfill(status=200, content_type='application/json', body=TAV)
        async def gem(route, request):
            prompts.append(request.post_data or '')
            await route.fulfill(status=200, content_type='application/json', body=resp_ce(5))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**api.tavily.com/search**', tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""([id])=>{
              db.simFormato='certoerrado'; db.simNivel='muitodificil';
              openSim.add(id);
              const host=document.createElement('div'); host.id='sim-'+id;
              document.body.appendChild(host);
              host.innerHTML=simPanelHTML(simFindSub(id));
              document.getElementById('sim-qtd-'+id).value='5';
            }""",[SUB])
            fmt=await page.evaluate("(id)=>document.getElementById('sim-fmt-'+id).value",SUB)
            niv=await page.evaluate("(id)=>document.getElementById('sim-niv-'+id).value",SUB)
            print('  seletores lembraram a escolha:',fmt,'/',niv)
            assert fmt=='certoerrado' and niv=='muitodificil', (fmt,niv)

            await page.evaluate("(id)=>generateSimulado(id)", SUB)
            await page.wait_for_function("(id)=>!!(simActive[id]&&simActive[id].questoes.length)",arg=SUB,timeout=20000)
            print('  buscas no Tavily:',len(buscas))
            assert len(buscas)==2, f'esperava 2 buscas, veio {len(buscas)}'
            assert 'Choque Distributivo' in buscas[0]['query'], buscas[0]['query']
            corpo=prompts[0]
            assert 'MATERIAL PESQUISADO NA INTERNET AGORA' in corpo, 'material do Tavily não chegou ao prompt'
            assert 'Bundle de 1 hora' in corpo, 'texto da página não chegou'
            assert 'CERTO ou ERRADO' in corpo, 'prompt não pediu certo/errado'
            assert 'MUITO ALTA' in corpo, 'prompt não pediu o nível muito difícil'
            assert "afirmacao" in corpo, 'formato JSON do certo/errado não foi pedido'
            assert 'DATA DE HOJE' in corpo, 'faltou a âncora de data'
            print('  ✓ prompt com material do Tavily + certo/errado + nível muito difícil + data')

            q=await page.evaluate("(id)=>simActive[id].questoes.map(x=>({f:x.formato,n:(x.alternativas||[]).length,alts:(x.alternativas||[]).map(a=>a.letra+':'+a.texto),c:x.correta}))",SUB)
            print('  questões:',len(q),'| 1a:',q[0])
            assert all(x['f']=='certoerrado' and x['n']==2 for x in q), q
            assert q[0]['alts']==['C:Certo','E:Errado'], q[0]
            assert set(x['c'] for x in q)<= {'C','E'} and len(set(x['c'] for x in q))==2, 'gabarito não variou'

            html=await page.evaluate("(id)=>document.getElementById('sim-'+id).innerHTML",SUB)
            assert 'sim-alts-ce' in html, 'as duas alternativas não receberam o layout de certo/errado'
            lado=await page.evaluate("""(id)=>{
              const box=document.querySelector('#sim-'+id+' .sim-alts-ce');
              const a=box.children[0].getBoundingClientRect(),b=box.children[1].getBoundingClientRect();
              return {mesmaLinha:Math.abs(a.top-b.top)<2, cs:getComputedStyle(box).flexDirection};}""",SUB)
            assert lado['mesmaLinha'], f'Certo e Errado não ficaram lado a lado ({lado})'
            print('  ✓ renderiza como gabarito de duas colunas')

            # responder e corrigir pelo mesmo caminho de sempre
            r=await page.evaluate("""(id)=>{
              simActive[id].questoes.forEach((q,i)=>simSelectAnswer(id,i,q.correta));
              simCorrigir(id);
              const s=simFindSub(id);
              return {stats:s.simStats, cards:Object.values(db.flashcards||{}).length};
            }""",SUB)
            print('  corrigido:',r['stats'])
            assert r['stats']['acertosTotal']==5 and r['stats']['questoesTotal']==5, r['stats']
            assert not real_errors(errors), real_errors(errors)
            print('  ✓ correção, histórico e estatística funcionam sem caminho novo')
        finally:
            await browser.close()

        # ===== 2) múltipla escolha sem Tavily continua igual =====
        print('=== 2) múltipla escolha, sem chave do Tavily ===')
        buscas2=[]; prompts2=[]
        async def tav2(route, request):
            buscas2.append(1); await route.fulfill(status=200, content_type='application/json', body=TAV)
        async def gem2(route, request):
            prompts2.append(request.post_data or '')
            await route.fulfill(status=200, content_type='application/json', body=resp_mult(5))
        browser,page,errors=await setup_page(p, seed(tavily=False))
        try:
            await page.route('**api.tavily.com/search**', tav2)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem2)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""([id])=>{
              db.simFormato='multipla'; db.simNivel='dificil'; openSim.add(id);
              const host=document.createElement('div'); host.id='sim-'+id;
              document.body.appendChild(host); host.innerHTML=simPanelHTML(simFindSub(id));
              document.getElementById('sim-qtd-'+id).value='5';
            }""",[SUB])
            await page.evaluate("(id)=>generateSimulado(id)", SUB)
            await page.wait_for_function("(id)=>!!(simActive[id]&&simActive[id].questoes.length)",arg=SUB,timeout=20000)
            assert not buscas2, 'buscou no Tavily sem chave configurada'
            corpo=prompts2[0]
            assert 'MATERIAL PESQUISADO' not in corpo
            assert 'DIFICULDADE ALTA' in corpo, 'nível difícil não entrou no prompt'
            assert 'exatamente 5 alternativas' in corpo
            q=await page.evaluate("(id)=>simActive[id].questoes.map(x=>({f:x.formato,n:x.alternativas.length}))",SUB)
            assert all(x['f']=='multipla' and x['n']==5 for x in q), q
            print('  ✓ sem chave, nada de busca; múltipla escolha com 5 alternativas e nível difícil')
            assert not real_errors(errors), real_errors(errors)
        finally:
            await browser.close()

        # ===== 3) Simulado Geral: seletores e configuração =====
        print('=== 3) Simulado Geral: formato, nível e pesquisa ===')
        browser,page,errors=await setup_page(p, seed(muitos=30))
        try:
            await page.set_viewport_size({'width':1400,'height':900})
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(400)
            info=await page.evaluate("""()=>({
              temFormato:!!document.getElementById('sg-formato'),
              temNivel:!!document.getElementById('sg-nivel'),
              temPesquisa:!!document.getElementById('sg-pesquisar'),
              pesquisaMarcada:document.getElementById('sg-pesquisar').checked})""")
            print('  ',info)
            assert info['temFormato'] and info['temNivel'] and info['temPesquisa']
            assert info['pesquisaMarcada'], 'com chave do Tavily, a pesquisa devia vir ligada'
            await page.evaluate("()=>sgMarcarTodos(true)")
            n=await page.evaluate("()=>simGeralConfig.selectedSubIds.size")
            await page.evaluate("()=>sgMarcarTodos(false)")
            n0=await page.evaluate("()=>simGeralConfig.selectedSubIds.size")
            print('  marcar todos ->',n,'| limpar ->',n0)
            assert n==32 and n0==0, (n,n0)
            print('  ✓ seletores presentes e marcar/limpar funcionando')
            assert not real_errors(errors), real_errors(errors)
        finally:
            await browser.close()

        # ===== 4) Simulado Geral gera de fato, em certo/errado =====
        # os 2 assuntos do chefao sao TODOS os estudados dele: agora isso vira uma
        # prova do tema, numa chamada so (ver test_chamada_unica.py)
        print('=== 4) Simulado Geral em certo/errado, chefão inteiro numa chamada ===')
        buscas4=[]; prompts4=[]
        async def tav4(route, request):
            buscas4.append(json.loads(request.post_data or '{}'))
            await route.fulfill(status=200, content_type='application/json', body=TAV)
        async def gem4(route, request):
            prompts4.append(request.post_data or '')
            n=len(prompts4)
            itens=[{'assunto':(i%2)+1,'afirmacao':f'Afirmação {n}-{i}.','gabarito':'C' if i%2 else 'E','explicacao':'x'}
                   for i in range(10)]
            await route.fulfill(status=200, content_type='application/json',
                body=json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]}))
        browser,page,errors=await setup_page(p, seed())
        try:
            await page.route('**api.tavily.com/search**', tav4)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem4)
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(300)
            await page.evaluate("""([a,b])=>{
              simGeralConfig.selectedSubIds=new Set([a,b]);
              renderSimGeralScreen();
              document.getElementById('sg-formato').value='certoerrado';
              document.getElementById('sg-nivel').value='dificil';
              document.getElementById('sg-qtd').value='10';
              document.getElementById('sg-tempo').value='0';
            }""",[SUB,SUB2])
            await page.evaluate("()=>generateSimuladoGeral()")
            await page.wait_for_function("()=>!!(simGeralActive&&simGeralActive.questoes.length)",timeout=40000)
            r=await page.evaluate("""()=>({n:simGeralActive.questoes.length,
                fmt:simGeralActive.formato,niv:simGeralActive.nivel,
                todosCE:simGeralActive.questoes.every(q=>q.formato==='certoerrado'&&q.alternativas.length===2),
                assuntos:[...new Set(simGeralActive.questoes.map(q=>q.subName))]})""")
            print('  ',r,'| buscas:',len(buscas4))
            assert r['fmt']=='certoerrado' and r['todosCE'], r
            print('  chamadas ao modelo:',len(prompts4))
            assert len(r['assuntos'])==2, r['assuntos']
            assert len(prompts4)==1, f'chefão inteiro devia ser 1 chamada, veio {len(prompts4)}'
            assert len(buscas4)==2, f'1 pesquisa = 2 buscas, veio {len(buscas4)}'
            assert 'MATERIAL PESQUISADO NA INTERNET AGORA' in prompts4[0]
            assert 'TEMA CENTRAL' in prompts4[0], 'devia usar o prompt do tema'
            print('  ✓ prova do tema em 1 chamada, certo/errado, com as questões voltando aos 2 assuntos')
            assert not real_errors(errors), real_errors(errors)
        finally:
            await browser.close()

        print('\nOK — simulados com Tavily, formato certo/errado, nível de dificuldade e lista ampliável')

asyncio.run(main())
