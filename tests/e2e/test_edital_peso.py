import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors
K='k1';T='t1'

def ass(i,nome,subId=None):
    a={'id':i,'nome':nome}
    if subId:a['subId']=subId
    return a

# Cenario que expoe o problema: "Diluida" tem 30 questoes espalhadas em 10 assuntos
# (3 q cada). "Concentrada" tem 10 questoes em 2 assuntos (5 q cada). Contando
# ASSUNTO, Diluida parece dominar a prova. Por QUESTAO, cada assunto de
# Concentrada vale mais tempo. E "SemNumero" nao declara nada.
DIL=[ass('d%d'%i,'Diluida %d'%i) for i in range(1,11)]
CON=[ass('c1','Concentrada A'),ass('c2','Concentrada B')]
SEM=[ass('s1','Sem numero 1'),ass('s2','Sem numero 2')]
# subs no Vale: 5 da Diluida estudados, nenhum da Concentrada
SUBS=[{'id':'sub_d%d'%i,'name':'Diluida %d'%i,'priority':70,'studied':True} for i in range(1,6)]
for i in range(1,6): DIL[i-1]['subId']='sub_d%d'%i

EDITAL={'id':'e1','nome':'Concurso Teste','cargo':'Enfermeiro','banca':'FGV','orgao':'',
  'icon':'📋','color':'#6c47ff','status':'inscrito','data':'2026-11-01',
  'disciplinas':[
    {'id':'D1','nome':'Diluida','questoes':30,'assuntos':DIL},
    {'id':'D2','nome':'Concentrada','questoes':10,'assuntos':CON},
    {'id':'D3','nome':'SemNumero','questoes':0,'assuntos':SEM}]}

seed=make_seed({'studyNickname':'Leo','editais':[EDITAL],
  'kingdoms':[{'id':K,'name':'Enfermagem','icon':'💉'}],
  'topics':{K:[{'id':T,'name':'Geral','subtopics':SUBS}]}})

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p,seed)
        try:
            r=await page.evaluate("""()=>{
              const e=edFind('e1');
              const c=edCobertura(e);
              const dil=e.disciplinas[0],con=e.disciplinas[1],sem=e.disciplinas[2];
              return {c,
                qDil:edQuestoesPorAssunto(dil),qCon:edQuestoesPorAssunto(con),qSem:edQuestoesPorAssunto(sem),
                prioDil:edPrioridade(dil.assuntos[5],dil),  // nao estudado
                prioCon:edPrioridade(con.assuntos[0],con),
                prioEstudado:edPrioridade(dil.assuntos[0],dil),
                top:edTop(e,5).map(t=>({nome:t.a.nome,disc:t.d.nome,q:t.q}))};}""")
            c=r['c']
            print('1) peso por assunto -> Diluida %.1f q | Concentrada %.1f q | SemNumero %.1f'%(r['qDil'],r['qCon'],r['qSem']))
            assert r['qDil']==3.0 and r['qCon']==5.0 and r['qSem']==0

            print('2) prioridade: Concentrada(%d) > Diluida(%d) — a diluida nao domina mais'%(r['prioCon'],r['prioDil']))
            assert r['prioCon']>r['prioDil'], 'o assunto que rende mais questao tem que vir na frente'
            print('3) assunto ja estudado sai da conta ->',r['prioEstudado'])
            assert r['prioEstudado']==0

            print('4) cobertura por ASSUNTO: %d%% (%d/%d)'%(c['pct'],c['estudados'],c['total']))
            print('   cobertura por QUESTAO: %d%% (%d de %d)'%(c['qPct'],c['qEstudadas'],c['qTotal']))
            # 5 de 14 assuntos = 36%; por questao 15 de 40 = 38%
            assert c['total']==14 and c['estudados']==5 and c['pct']==36
            assert c['qTotal']==40 and c['qEstudadas']==15 and c['qPct']==38
            print('5) disciplinas sem nº de questões sinalizadas ->',c['discSemQ'])
            assert c['discSemQ']==1

            print('6) top 5 (edital inteiro, nao por disciplina):')
            for t in r['top']: print('     %-16s %-13s %.1f q'%(t['nome'],t['disc'],t['q']))
            assert r['top'][0]['disc']=='Concentrada' and r['top'][1]['disc']=='Concentrada', r['top'][:2]

            # a tela renderiza
            await page.evaluate("()=>{edAbertos.add('e1');showScreen('editais');}")
            await page.wait_for_timeout(400)
            html=await page.evaluate("()=>document.getElementById('editais-list').innerHTML")
            print('7) cabeçalho fala em questão ->', 'de 40 questões' in html)
            assert 'de 40 questões' in html and '38%' in html
            print('8) bloco "Onde investir agora" na tela ->', 'Onde investir agora' in html)
            assert 'Onde investir agora' in html
            print('9) aviso de disciplina sem nº ->', '1 disciplina sem nº de questões' in html)
            assert '1 disciplina sem nº de questões' in html
            print('10) peso por disciplina visível ->', '5 q/assunto' in html and '3 q/assunto' in html)
            assert '5 q/assunto' in html and '3 q/assunto' in html

            larg=await page.evaluate("""()=>[...document.querySelectorAll('.ed-cob-barra i')]
                 .map(i=>parseFloat(i.style.width)).reduce((a,b)=>a+b,0)""")
            print('11) barra soma %.2f%% (nao pode passar de 100)'%larg)
            assert larg<=100.01, larg

            assert not real_errors(errors), real_errors(errors)
            print('\nOK')
        finally:
            await browser.close()
asyncio.run(main())
