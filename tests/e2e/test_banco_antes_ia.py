# -*- coding: utf-8 -*-
# Passo 5 do plano: antes de gastar quota da IA (e credito do Tavily, se for pesquisar),
# o banco pode ja ter questao boa sobre o mesmo assunto. "Boa" = nunca respondida, ou
# respondida ha mais de BANCO_REAPROVEITAR_DIAS_MIN dias, ativa (nao arquivada pelo
# usuario) e sem problema (questaoForaDaConta). So o que faltar vai pra IA.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-s1'; SUB2='sub-s2'; TOPIC='topic-s1'; KING='king-s1'

def seed():
    subs=[{'id':SUB,'name':'Choque Séptico','priority':100,'studied':True},
          {'id':SUB2,'name':'Trauma Cranioencefálico','priority':100,'studied':True}]
    return make_seed({'studyNickname':'Reitor','studyCharacter':'ash','geminiApiKey':'FAKE',
        'tavilyApiKey':'tvly-FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Urgência e Emergência','subtopics':subs}]}})

def resp_ce(n,tag='IA'):
    itens=[{'afirmacao':f'{tag} afirmação {i+1} sobre choque séptico.',
            'gabarito':'C' if i%2 else 'E','explicacao':f'Porque {i+1}.'} for i in range(n)]
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

TAV=json.dumps({'results':[{'url':'https://www.gov.br/x','title':'MS','raw_content':'conteúdo oficial'}]})

# monta um item de acervo direto (sem passar por acervoGuardarProva) — so os campos que
# bancoReaproveitar de fato le
MK_ITEM = """(txt,extra)=>({
  questao:txt, formato:'certoerrado', correta:'C',
  alternativas:SIM_ALTS_CE.map(a=>({...a})),
  explicacao:'x', subId:extra.subId, subName:extra.subName||'Choque Séptico',
  topicName:'Urgência e Emergência', kingdomId:extra.kingdomId||'king-s1',
  kingdomName:'Enfermagem', kingdomIcon:'💉',
  tags:[], favorita:false, status:extra.status||'ativa', vezesRespondida:extra.vezesRespondida||0,
  acertos:0, erros:0, ultimaVezEm:extra.ultimaVezEm||null, dificuldadeAferida:null,
  criadaEm:new Date().toISOString(), origem:'ia',
  _chaveForte:'', ...(extra.problematico?{problematico:true}:{})
})"""

async def gerar_sim(page,sub_id,qtd,formato='certoerrado'):
    await page.evaluate("""([id,qtd,formato])=>{
      db.simFormato=formato; db.simNivel='dificil';
      openSim.add(id);
      const host=document.createElement('div'); host.id='sim-'+id;
      document.body.appendChild(host);
      host.innerHTML=simPanelHTML(simFindSub(id));
      document.getElementById('sim-qtd-'+id).value=String(qtd);
      document.getElementById('sim-fmt-'+id).value=formato;
    }""",[sub_id,qtd,formato])
    await page.evaluate("(id)=>generateSimulado(id)",sub_id)
    await page.wait_for_function("(id)=>!!(simActive[id]&&simActive[id].questoes.length)",arg=sub_id,timeout=20000)

async def main():
    async with async_playwright() as p:

        print('=== A) banco ja tem o suficiente — zero chamada de IA, zero busca ===')
        chamadas=[]; buscas=[]
        async def tav(route,request):
            buscas.append(1); await route.fulfill(status=200,content_type='application/json',body=TAV)
        async def gem(route,request):
            chamadas.append(1); await route.fulfill(status=200,content_type='application/json',body=resp_ce(5))
        browser,page,errors=await setup_page(p,seed())
        try:
            await page.route('**api.tavily.com/search**',tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""(mk)=>{window.MK=eval('('+mk+')');}""",MK_ITEM)
            await page.evaluate("""([id])=>{
              db.acervo=[0,1,2,3,4].map(i=>MK('Já existe no banco '+i,{subId:id}));
            }""",[SUB])
            await gerar_sim(page,SUB,5)
            r=await page.evaluate("""(id)=>({n:simActive[id].questoes.length,
              textos:simActive[id].questoes.map(q=>q.questao)})""",SUB)
            print('   %s questões, todas do banco: %s'%(r['n'],all('Já existe no banco' in t for t in r['textos'])))
            assert r['n']==5 and all('Já existe no banco' in t for t in r['textos'])
            assert not chamadas and not buscas
            print('   nenhuma chamada de IA nem busca — o banco já tinha tudo')
            assert not real_errors(errors), real_errors(errors)
            print('   OK\n')
        finally:
            await browser.close()

        print('=== B) banco tem so parte — o resto vem da IA, so pro que falta ===')
        chamadas=[]; buscas=[]
        async def gem_parcial(route,request):
            corpo=json.loads(request.post_data or '{}')
            texto=json.dumps(corpo)
            chamadas.append(texto)
            await route.fulfill(status=200,content_type='application/json',body=resp_ce(5,'IA'))
        browser,page,errors=await setup_page(p,seed())
        try:
            await page.route('**api.tavily.com/search**',tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem_parcial)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""(mk)=>{window.MK=eval('('+mk+')');}""",MK_ITEM)
            await page.evaluate("""([id])=>{db.acervo=[MK('Já existe no banco única',{subId:id})];}""",[SUB])
            await gerar_sim(page,SUB,5)
            r=await page.evaluate("""(id)=>({n:simActive[id].questoes.length,
              doBanco:simActive[id].questoes.filter(q=>q.questao.includes('Já existe')).length,
              daIA:simActive[id].questoes.filter(q=>q.questao.includes('IA afirmação')).length})""",SUB)
            print('   total %s: %s do banco + %s da IA'%(r['n'],r['doBanco'],r['daIA']))
            assert r['n']==5 and r['doBanco']==1 and r['daIA']==4
            assert len(chamadas)==1   # pediu so as 2 que faltavam, numa chamada so
            print('   a IA foi chamada pedindo só o que faltava (1 chamada, não 3)')
            assert not real_errors(errors), real_errors(errors)
            print('   OK\n')
        finally:
            await browser.close()

        print('=== C) respondida ha pouco tempo nao e reaproveitada ===')
        chamadas=[]
        browser,page,errors=await setup_page(p,seed())
        try:
            await page.route('**api.tavily.com/search**',tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""(mk)=>{window.MK=eval('('+mk+')');}""",MK_ITEM)
            await page.evaluate("""([id])=>{
              db.acervo=[MK('Respondida ontem',{subId:id,vezesRespondida:1,ultimaVezEm:new Date().toISOString()})];
            }""",[SUB])
            await gerar_sim(page,SUB,5)
            r=await page.evaluate("(id)=>simActive[id].questoes.map(q=>q.questao)",SUB)
            print('   nenhuma questão do banco entrou: %s'%all('Respondida ontem' not in t for t in r))
            assert all('Respondida ontem' not in t for t in r)
            assert chamadas   # teve que chamar a IA pra tudo
            assert not real_errors(errors), real_errors(errors)
            print('   OK\n')
        finally:
            await browser.close()

        print('=== D) marcada como arquivada pelo usuário fica de fora ===')
        chamadas=[]
        browser,page,errors=await setup_page(p,seed())
        try:
            await page.route('**api.tavily.com/search**',tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""(mk)=>{window.MK=eval('('+mk+')');}""",MK_ITEM)
            await page.evaluate("""([id])=>{
              db.acervo=[MK('Arquivada pelo usuário',{subId:id,status:'arquivada'})];
            }""",[SUB])
            await gerar_sim(page,SUB,5)
            r=await page.evaluate("(id)=>simActive[id].questoes.map(q=>q.questao)",SUB)
            assert all('Arquivada pelo usuário' not in t for t in r)
            assert not real_errors(errors), real_errors(errors)
            print('   OK\n')
        finally:
            await browser.close()

        print('=== E) item com problema (fora da conta) fica de fora ===')
        chamadas=[]
        browser,page,errors=await setup_page(p,seed())
        try:
            await page.route('**api.tavily.com/search**',tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""(mk)=>{window.MK=eval('('+mk+')');}""",MK_ITEM)
            await page.evaluate("""([id])=>{
              db.acervo=[MK('Item quebrado',{subId:id,problematico:true})];
            }""",[SUB])
            await gerar_sim(page,SUB,5)
            r=await page.evaluate("(id)=>simActive[id].questoes.map(q=>q.questao)",SUB)
            assert all('Item quebrado' not in t for t in r)
            assert not real_errors(errors), real_errors(errors)
            print('   OK\n')
        finally:
            await browser.close()

        print('=== F) formato diferente do pedido fica de fora ===')
        chamadas=[]
        async def gem_mult(route,request):
            chamadas.append(1)
            itens=[{'questao':f'Múltipla {i}?','alternativas':[{'letra':l,'texto':l} for l in 'ABCDE'],
                    'correta':'ABCDE'[i%5],'explicacao':'x'} for i in range(5)]
            await route.fulfill(status=200,content_type='application/json',
                body=json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]}))
        browser,page,errors=await setup_page(p,seed())
        try:
            await page.route('**api.tavily.com/search**',tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem_mult)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])
            await page.evaluate("""(mk)=>{window.MK=eval('('+mk+')');}""",MK_ITEM)
            await page.evaluate("""([id])=>{
              db.acervo=[MK('Certo/errado no banco',{subId:id})];   // banco só tem certo/errado
            }""",[SUB])
            await gerar_sim(page,SUB,5,'multipla')   # pede múltipla
            r=await page.evaluate("(id)=>simActive[id].questoes.map(q=>q.questao)",SUB)
            assert all('Certo/errado no banco' not in t for t in r)
            assert chamadas
            print('   a questão certo/errado não "virou" múltipla escolha — foi ignorada, a IA gerou tudo')
            assert not real_errors(errors), real_errors(errors)
            print('   OK\n')
        finally:
            await browser.close()

        print('=== G) chefão inteiro: cada reaproveitada volta pro PRÓPRIO assunto ===')
        chamadas=[]
        async def gem_topico(route,request):
            chamadas.append(1)
            await route.fulfill(status=200,content_type='application/json',body=resp_ce(1,'IA'))
        browser,page,errors=await setup_page(p,seed())
        try:
            await page.route('**api.tavily.com/search**',tav)
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**',gem_topico)
            await page.evaluate("""(mk)=>{window.MK=eval('('+mk+')');}""",MK_ITEM)
            await page.evaluate("""([s1,s2])=>{
              db.acervo=[MK('Do banco — assunto 1',{subId:s1}),MK('Do banco — assunto 2',{subId:s2})];
            }""",[SUB,SUB2])
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(300)
            # os dois unicos assuntos do chefao, ambos estudados -> vira UMA unidade
            # "chefao inteiro" (generateQuestionsForTopic), que e o caminho deste teste.
            await page.evaluate("""([s1,s2])=>{simGeralConfig.selectedSubIds=new Set([s1,s2]);}""",[SUB,SUB2])
            await page.evaluate("""()=>{
              document.getElementById('sg-qtd').value='10';
              document.getElementById('sg-tempo').value='0';
              document.getElementById('sg-formato').value='certoerrado';
            }""")
            await page.evaluate("()=>generateSimuladoGeral()")
            await page.wait_for_function("()=>!!(simGeralActive&&simGeralActive.questoes.length)",timeout=20000)
            r=await page.evaluate("""()=>simGeralActive.questoes.map(q=>({texto:q.questao,subId:q.subId}))""")
            do1=[x for x in r if x['texto']=='Do banco — assunto 1']
            do2=[x for x in r if x['texto']=='Do banco — assunto 2']
            print('   %s questões no total; "assunto 1" foi pro subId certo: %s · "assunto 2": %s'
                  %(len(r), do1 and do1[0]['subId']==SUB, do2 and do2[0]['subId']==SUB2))
            assert do1 and do1[0]['subId']==SUB
            assert do2 and do2[0]['subId']==SUB2
            assert not real_errors(errors), real_errors(errors)
            print('   OK\n')
        finally:
            await browser.close()

        print('OK')

asyncio.run(main())
