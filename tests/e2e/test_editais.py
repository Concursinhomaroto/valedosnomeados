# Edital com conteudo programatico: cobertura, lacunas, peso, prevalencia e foco.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

K='k1'
CONTEUDO = """CONHECIMENTOS ESPECÍFICOS (30 questões)
1. Sistematização da Assistência de Enfermagem
2. Vacinação: calendário e rede de frio
3. Choque séptico
4. Trauma cranioencefálico
LÍNGUA PORTUGUESA (10 questões)
1. Morfologia
2. Crase"""

def seed():
    return make_seed({'studyNickname':'R','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
        'topics':{K:[{'id':'t0','name':'Urgência','icon':'⚔️','priority':3,'subtopics':[
            {'id':'sA','name':'Choque séptico','priority':70,'studied':True},
            {'id':'sB','name':'Trauma cranioencefálico','priority':70,'studied':False},
            {'id':'sZ','name':'Assunto fora do edital','priority':100,'studied':False}]}]},
        'editais':[{'id':'e1','nome':'Campina Grande','cargo':'Enfermeiro','banca':'IDECAO',
                    'data':'2026-12-01','icon':'📝','color':'#6c47ff','status':'inscrito','createdAt':'2026-09-01'}]})

EXTRAI = json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps({'disciplinas':[
    {'nome':'Conhecimentos Específicos','questoes':30,'assuntos':[
        'Sistematização da Assistência de Enfermagem','Vacinação: calendário e rede de frio',
        'Choque séptico','Trauma cranioencefálico']},
    {'nome':'Língua Portuguesa','questoes':10,'assuntos':['Morfologia','Crase']}]})}]},'finishReason':'STOP'}]})

async def main():
    async with async_playwright() as pw:
        async def gem(route, request):
            await route.fulfill(status=200, content_type='application/json', body=EXTRAI)
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.evaluate("()=>showScreen('editais')")
            await page.wait_for_timeout(400)

            print('=== 1) extração do conteúdo programático ===')
            await page.evaluate("()=>edToggleConteudo('e1')")
            await page.wait_for_timeout(200)
            await page.evaluate("(t)=>{document.getElementById('ed-txt-e1').value=t;}", CONTEUDO)
            await page.evaluate("()=>edExtrairIA('e1')")
            await page.wait_for_function("()=>edFind('e1').disciplinas.length>0",timeout=20000)
            r=await page.evaluate("""()=>{const e=edFind('e1');return{
              discs:e.disciplinas.map(d=>({nome:d.nome,q:d.questoes,n:d.assuntos.length})),
              cob:edCobertura(e)};}""")
            print('  disciplinas:',r['discs'])
            print('  cobertura  :',r['cob'])
            assert len(r['discs'])==2, r['discs']
            assert r['discs'][0]['q']==30 and r['discs'][1]['q']==10, 'peso do edital não foi lido'
            for ch,esp in {'total':6,'estudados':1,'cadastrados':1,'faltam':4,'pct':17}.items():
                assert r['cob'][ch]==esp, (ch,r['cob'][ch],esp,r['cob'])
            print('  ✓ 6 assuntos: 1 estudado, 1 cadastrado, 4 sem cadastro (a lacuna invisível)')

            # o prompt precisa cobrir as tres armadilhas do texto real de edital
            pr=await page.evaluate("()=>window.__ultimoPromptEdital||''")
            for regra in ['NÍVEL MAIS PROFUNDO','CABEÇALHO DE PÁGINA','SEM título de disciplina']:
                assert regra in pr, f'regra ausente do prompt: {regra}'
            print('  ✓ prompt cobre nível profundo, cabeçalho de Diário Oficial e bloco sem título')

            print('\n=== 2) os três estados por assunto ===')
            est=await page.evaluate("""()=>{const e=edFind('e1');const o={};
              e.disciplinas.forEach(d=>d.assuntos.forEach(a=>{o[a.nome]=edEstado(a);}));return o;}""")
            for k,v in est.items(): print(f"    {v:<11} {k}")
            assert est['Choque séptico']=='estudado'
            assert est['Trauma cranioencefálico']=='cadastrado'
            assert est['Morfologia']=='falta'
            print('  ✓ casou pelo nome com os minibosses que já existiam')

            print('\n=== 3) criar os que faltam ===')
            await page.evaluate("()=>{window.confirm=()=>true;}")
            discId=await page.evaluate("()=>edFind('e1').disciplinas[1].id")
            await page.evaluate("([d,k])=>{const s=document.getElementById('ed-reino-'+d);if(s)s.value=k;}",[discId,K])
            await page.evaluate("(d)=>edCriarFaltantes('e1',d)",discId)
            await page.wait_for_timeout(300)
            depois=await page.evaluate("""()=>{const e=edFind('e1');
              const t=db.topics.k1.find(x=>x.name==='Língua Portuguesa');
              return{cob:edCobertura(e),chefaoCriado:!!t,minibosses:t?t.subtopics.map(s=>s.name):[]};}""")
            print('  ',depois)
            assert depois['chefaoCriado'], 'a disciplina não virou chefão'
            assert set(depois['minibosses'])=={'Morfologia','Crase'}, depois['minibosses']
            assert depois['cob']['faltam']==2, depois['cob']
            print('  ✓ a disciplina virou chefão e os assuntos viraram minibosses; a lacuna caiu de 4 para 2')

            print('\n=== 4) prevalência marcada à mão ordena a lista ===')
            ids=await page.evaluate("""()=>{const d=edFind('e1').disciplinas[0];
              return{disc:d.id,assuntos:d.assuntos.map(a=>({id:a.id,nome:a.nome}))};}""")
            sae=[a for a in ids['assuntos'] if 'Sistematização' in a['nome']][0]
            vac=[a for a in ids['assuntos'] if 'Vacinação' in a['nome']][0]
            # SAE marcada como alta (3 cliques), Vacinação como baixa (1 clique)
            for _ in range(3): await page.evaluate("([d,a])=>edCiclarPrev('e1',d,a)",[ids['disc'],sae['id']])
            await page.evaluate("([d,a])=>edCiclarPrev('e1',d,a)",[ids['disc'],vac['id']])
            p=await page.evaluate("""([d,x,y])=>{const disc=edFind('e1').disciplinas.find(z=>z.id===d);
              const A=disc.assuntos.find(a=>a.id===x),B=disc.assuntos.find(a=>a.id===y);
              return{alta:{prev:A.prev,score:edPrioridade(A,disc)},baixa:{prev:B.prev,score:edPrioridade(B,disc)}};}""",
              [ids['disc'],sae['id'],vac['id']])
            print('  SAE (alta):',p['alta'],'| Vacinação (baixa):',p['baixa'])
            assert p['alta']['prev']==3 and p['baixa']['prev']==1
            assert p['alta']['score']>p['baixa']['score'], p
            # o ciclo tem 4 estados: de prev=1, mais 3 cliques voltam para "sem marca"
            await page.evaluate("([d,a])=>{for(let i=0;i<3;i++)edCiclarPrev('e1',d,a);}",[ids['disc'],vac['id']])
            zero=await page.evaluate("([d,a])=>edFind('e1').disciplinas.find(z=>z.id===d).assuntos.find(x=>x.id===a).prev",[ids['disc'],vac['id']])
            assert zero==0, zero
            print('  ✓ ciclo sem marca → 1 → 2 → 3 → sem marca, e o peso ordena')

            print('\n=== 5) foco: a Fila de Hoje prioriza o edital ===')
            semFoco=await page.evaluate("()=>computeStudyRecommendations().map(i=>i.subName)")
            print('  sem foco:',semFoco[:4])
            # "Assunto fora do edital" é lendário e nunca estudado: sem foco, lidera
            assert semFoco[0]=='Assunto fora do edital', semFoco
            await page.evaluate("()=>edFocar('e1')")
            comFoco=await page.evaluate("()=>computeStudyRecommendations().map(i=>({n:i.subName,ed:!!i.edital}))")
            print('  com foco:',[c['n'] for c in comFoco[:4]])
            pos=[c['n'] for c in comFoco].index('Assunto fora do edital')
            print(f"  o lendário fora do edital caiu do 1º para o {pos+1}º lugar")
            assert comFoco[0]['ed'], 'o topo da fila devia ser um assunto do edital'
            assert pos>0, 'o assunto fora do edital continuou liderando'
            assert all(c['ed'] for c in comFoco[:pos]), 'item fora do edital furou a fila'
            print('  ✓ o que cai no edital sobe, e o que não cai desce sem sumir da fila')

            print('\n=== 6) Simulado Geral marca só o que cai no edital ===')
            await page.evaluate("()=>{db.kingdoms[0]&&(db.topics.k1[0].subtopics[1].studied=true);saveDB();}")
            await page.evaluate("()=>showScreen('simgeral')")
            await page.wait_for_timeout(400)
            temBotao=await page.evaluate("()=>!!document.querySelector('.sg-edital-row')")
            assert temBotao, 'a faixa do edital em foco não apareceu'
            await page.evaluate("()=>sgMarcarEdital()")
            sel=await page.evaluate("()=>[...simGeralConfig.selectedSubIds]")
            nomes=await page.evaluate("()=>[...simGeralConfig.selectedSubIds].map(id=>simFindSub(id).name)")
            print('  marcados:',nomes)
            assert set(nomes)=={'Choque séptico','Trauma cranioencefálico'}, nomes
            print('  ✓ marcou exatamente os assuntos do edital que existem no Vale')

            print('\n=== 7) tirar o foco volta ao critério geral ===')
            await page.evaluate("()=>edFocar(null)")
            semMarca=await page.evaluate("()=>computeStudyRecommendations().every(i=>!i.edital)")
            assert semMarca, 'ainda há item marcado como do edital'
            print('  ✓ foco removido')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — edital com conteúdo, cobertura, lacunas, peso, prevalência manual e foco')
        finally:
            await browser.close()
asyncio.run(main())
