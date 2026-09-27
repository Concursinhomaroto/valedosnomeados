# O casamento ignora a numeracao do edital, e o vinculo manual manda mais que ele.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

K='k1'
def seed():
    return make_seed({'studyNickname':'R','studyCharacter':'ash',
        'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
        'topics':{K:[{'id':'t0','name':'Legislação','icon':'⚔️','priority':3,'subtopics':[
            {'id':'sA','name':'Lei do exercício profissional','priority':70,'studied':True},
            {'id':'sB','name':'Código de Ética','priority':70,'studied':False},
            {'id':'sC','name':'Ética profissional do enfermeiro','priority':70,'studied':True}]}]},
        'editais':[{'id':'e1','nome':'SESAU AL','cargo':'Enfermeiro','banca':'CEBRASPE',
            'data':'2026-11-01','icon':'📝','color':'#6c47ff','status':'inscrito','createdAt':'2026-09-01',
            'disciplinas':[{'id':'d1','nome':'Conhecimentos Específicos','questoes':70,'assuntos':[
                {'id':'a1','nome':'1 Lei do exercício profissional','subId':None,'prev':0},
                {'id':'a2','nome':'2 Código de Ética','subId':None,'prev':0},
                {'id':'a3','nome':'5.1 Emprego das classes de palavras','subId':None,'prev':0},
                {'id':'a4','nome':'3 Epidemiologia e enfermagem','subId':None,'prev':0}]}]}]})

ADD_A9 = '''()=>{ const e=edFind('e1'); e.disciplinas[0].assuntos.push({id:'a9',nome:'9 Legislação',subId:null,topicId:null,prev:0}); renderEditais(); }'''
LE_A9 = '''()=>{ const a=edFind('e1').disciplinas[0].assuntos.find(x=>x.id==='a9'); return {estado:edEstado(a),topicId:a.topicId,prog:edProgresso(a)}; }'''

async def main():
    async with async_playwright() as pw:
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.evaluate("()=>showScreen('editais')")
            await page.wait_for_timeout(400)

            print('=== 1) numeração deixa de atrapalhar o casamento ===')
            r=await page.evaluate("""()=>{const e=edFind('e1');const o={};
              e.disciplinas[0].assuntos.forEach(a=>{o[a.nome]=edEstado(a);});
              return{estados:o,cob:edCobertura(e)};}""")
            for k,v in r['estados'].items(): print(f"    {v:<11} {k}")
            assert r['estados']['1 Lei do exercício profissional']=='estudado', r['estados']
            assert r['estados']['2 Código de Ética']=='cadastrado', r['estados']
            assert r['estados']['3 Epidemiologia e enfermagem']=='falta', r['estados']
            print('  ✓ "1 Lei do exercício profissional" casou com "Lei do exercício profissional"')

            print('\n=== 2) sugestões para o que não casou ===')
            sug=await page.evaluate("()=>edSugestoes('5.1 Emprego das classes de palavras').slice(0,3).map(x=>({n:x.nome,t:x.tipo,s:x.score}))")
            print('  ',sug)
            sug2=await page.evaluate("()=>edSugestoes('2 Código de Ética profissional').slice(0,2).map(x=>({n:x.nome,t:x.tipo,s:x.score}))")
            print('  para "Código de Ética profissional":',sug2)
            assert sug2[0]['s']>0, 'nenhuma sugestão pontuou'
            print('  ✓ ordena por palavras em comum, sem vincular nada sozinho')

            print('\n=== 3) vínculo manual manda mais que o automático ===')
            await page.evaluate("()=>edAbrirVinculo('e1','d1','a4')")
            await page.wait_for_timeout(200)
            temModal=await page.evaluate("()=>document.getElementById('modal').classList.contains('open')")
            assert temModal, 'o modal não abriu'
            # vincula "3 Epidemiologia e enfermagem" a um miniboss de nome bem diferente
            await page.evaluate("()=>edVincularEm('sC')")
            await page.wait_for_timeout(200)
            r3=await page.evaluate("""()=>{const a=edFind('e1').disciplinas[0].assuntos[3];
              return{estado:edEstado(a),subId:a.subId,manual:!!a.manual,sub:edSubDe(a).name};}""")
            print('  ',r3)
            assert r3['estado']=='estudado' and r3['manual'] and r3['subId']=='sC', r3
            # e o recasamento automático (que roda a cada render) não desfaz
            await page.evaluate("()=>renderEditais()")
            await page.wait_for_timeout(200)
            depois=await page.evaluate("()=>edFind('e1').disciplinas[0].assuntos[3].subId")
            assert depois=='sC', f'o automático desfez o vínculo manual: {depois}'
            print('  ✓ vinculado à mão e o automático não desfaz ao redesenhar')

            print('\n=== 4) desvincular volta ao automático ===')
            await page.evaluate("()=>{edAbrirVinculo('e1','d1','a4');edDesvincular();}")
            await page.wait_for_timeout(200)
            r4=await page.evaluate("""()=>{const a=edFind('e1').disciplinas[0].assuntos[3];
              return{estado:edEstado(a),manual:!!a.manual};}""")
            print('  ',r4)
            assert r4['estado']=='falta' and not r4['manual'], r4
            print('  ✓ voltou a ser lacuna')

            print('\n=== 5) criar um miniboss avulso, sem a numeração no nome ===')
            await page.evaluate("()=>{window.confirm=()=>true;edAbrirVinculo('e1','d1','a4');}")
            await page.wait_for_timeout(200)
            await page.evaluate("([k])=>{document.getElementById('ed-vinc-reino').value=k;}",[K])
            await page.evaluate("()=>edCriarUm()")
            await page.wait_for_timeout(300)
            r5=await page.evaluate("""()=>{const a=edFind('e1').disciplinas[0].assuntos[3];
              const t=db.topics.k1.find(x=>x.name==='Conhecimentos Específicos');
              return{estado:edEstado(a),nome:edSubDe(a).name,chefao:t?t.name:null,manual:!!a.manual};}""")
            print('  ',r5)
            assert r5['nome']=='Epidemiologia e enfermagem', f'a numeração ficou no nome: {r5["nome"]}'
            assert r5['estado']=='cadastrado' and r5['manual'], r5
            assert r5['chefao']=='Conhecimentos Específicos'
            print('  ✓ criado como "Epidemiologia e enfermagem" (sem o "3") e já vinculado')

            print('\n=== 6) cobertura final ===')
            c=await page.evaluate("()=>edCobertura(edFind('e1'))")
            print('  ',c)
            assert c=={'total':4,'estudados':1,'cadastrados':2,'faltam':1,'pct':25}, c
            print('  ✓ 1 estudado, 2 cadastrados, 1 lacuna')

            print('\n=== 7) vincular a um CHEFÃO inteiro ===')
            # o edital diz "Legislação"; o usuário tem isso como chefão, não miniboss
            await page.evaluate(ADD_A9)
            auto=await page.evaluate(LE_A9)
            print('  casamento automático pelo nome do chefão:',auto)
            assert auto['topicId']=='t0', 'não casou com o chefão de mesmo nome'
            assert auto['estado']=='cadastrado', auto
            assert auto['prog']['total']>=3, auto
            print(f"  ✓ casou com o chefão e mostra {auto['prog']['feitos']}/{auto['prog']['total']} estudados")

            # chefão só vira "estudado" quando TODOS os minibosses estão
            await page.evaluate("()=>{db.topics.k1[0].subtopics.forEach(s=>s.studied=true);saveDB();renderEditais();}")
            todos=await page.evaluate(LE_A9)
            print('  com todos estudados:',todos)
            assert todos['estado']=='estudado', todos
            print('  ✓ só conta como estudado quando o chefão inteiro está')

            print('\n=== 8) o foco cobre todos os minibosses do chefão ===')
            await page.evaluate("()=>edFocar('e1')")
            n=await page.evaluate("()=>Object.keys(edFocoIndice().idx).length")
            print('  minibosses no índice do foco:',n)
            assert n>=3, f'o chefão não trouxe seus minibosses para o foco ({n})'
            print('  ✓ um assunto ligado a chefão traz os minibosses dele junto')

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — casa com miniboss E com chefão, e você manda no vínculo')
        finally:
            await browser.close()
asyncio.run(main())
