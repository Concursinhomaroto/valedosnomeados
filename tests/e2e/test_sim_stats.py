# Estatística de simulado separada por formato de prova.
import asyncio, json, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

SUB='sub-s1'; TOPIC='topic-s1'; KING='king-s1'

def seed():
    return make_seed({'studyNickname':'Reitor','studyCharacter':'ash','geminiApiKey':'FAKE',
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Urgência e Emergência','subtopics':[
            {'id':SUB,'name':'Choque Distributivo (Séptico)','priority':100,'studied':True}]}]}})

def resp_ce(n):
    itens=[{'afirmacao':f'Afirmação {i+1}.','gabarito':'C' if i%2 else 'E','explicacao':'x'} for i in range(n)]
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

def resp_mult(n):
    itens=[{'questao':f'Questão {i+1}?','alternativas':[{'letra':l,'texto':l} for l in 'ABCDE'],
            'correta':'ABCDE'[i%5],'explicacao':'x'} for i in range(n)]
    return json.dumps({'candidates':[{'content':{'parts':[{'text':json.dumps(itens)}]},'finishReason':'STOP'}]})

MONTA = '''([id,f])=>{
  db.simFormato=f; delete simActive[id]; openSim.add(id);
  let host=document.getElementById('sim-'+id);
  if(!host){host=document.createElement('div');host.id='sim-'+id;document.body.appendChild(host);}
  host.innerHTML=simPanelHTML(simFindSub(id));
  document.getElementById('sim-qtd-'+id).value='10';
}'''
RESPONDE = '''([id,n])=>{
  simActive[id].questoes.forEach((q,i)=>{
    const alts=q.alternativas.map(a=>a.letra);
    const errada=alts.find(l=>l!==q.correta);
    simSelectAnswer(id,i, i<n ? q.correta : errada);
  });
  simCorrigir(id);
}'''
LEITURA = '''(id)=>{
  const st=simFindSub(id).simStats;
  const g=computeSimuladoStats();
  return {pf:st.porFormato, total:{q:st.questoesTotal,a:st.acertosTotal},
          efetivo:simPctEfetivo(st),
          globais:g.formatos.map(f=>({f:f.formato,pct:f.pct,corr:f.corrigido,saldo:f.saldo,q:f.questoes}))};
}'''
LINHAS = '''()=>[...document.querySelectorAll('#sim-por-formato .sim-fmt-row')]
   .map(e=>e.textContent.replace(/\\s+/g,' ').trim())'''

async def main():
    async with async_playwright() as pw:
        estado={'fmt':'multipla'}
        async def gem(route, request):
            await route.fulfill(status=200, content_type='application/json',
                body=resp_ce(10) if estado['fmt']=='certoerrado' else resp_mult(10))
        browser,page,errors=await setup_page(pw, seed())
        try:
            await page.route('**generativelanguage.googleapis.com/v1beta/models/*:generateContent**', gem)
            await page.evaluate("([k])=>{currentKingdom=db.kingdoms.find(x=>x.id===k);}",[KING])

            async def rodar(fmt, acertar):
                estado['fmt']=fmt
                await page.evaluate(MONTA,[SUB,fmt])
                await page.evaluate("(id)=>generateSimulado(id)", SUB)
                await page.wait_for_function("(id)=>!!(simActive[id]&&simActive[id].questoes.length)",arg=SUB,timeout=20000)
                await page.evaluate(RESPONDE,[SUB,acertar])

            # 10 de múltipla com 8 acertos (80%); 10 de C/E com 6 (60% bruto -> 20% corrigido)
            await rodar('multipla', 8)
            await rodar('certoerrado', 6)

            r=await page.evaluate(LEITURA, SUB)
            print('  por formato:',r['pf'])
            print('  globais:',r['globais'])
            print('  efetivo do assunto:',r['efetivo'])
            assert r['pf']['multipla']=={'tentativas':1,'questoes':10,'acertos':8,'marcadas':10}, r['pf']
            assert r['pf']['certoerrado']=={'tentativas':1,'questoes':10,'acertos':6,'marcadas':10}, r['pf']
            assert r['total']=={'q':20,'a':14}, r['total']
            ce=[g for g in r['globais'] if g['f']=='certoerrado'][0]
            mu=[g for g in r['globais'] if g['f']=='multipla'][0]
            assert ce['pct']==60 and ce['corr']==20, ce    # 2*60-100
            assert ce['saldo']==2, ce                       # 6 acertos - 4 erros
            assert mu['pct']==80 and mu['corr']==80, mu     # múltipla não se corrige
            assert r['efetivo']['bruto']==70 and r['efetivo']['corrigido']==50, r['efetivo']
            print('  ✓ C/E 60% bruto vira 20% corrigido e saldo +2; múltipla fica em 80%')

            fila=await page.evaluate("()=>computeStudyRecommendations().map(i=>({n:i.subName,t:i.tipo,r:i.reason}))")
            alvo=[f for f in fila if 'Séptico' in f['n']]
            print('  fila de hoje:',alvo)
            assert alvo and alvo[0]['t']=='fraco' and '50%' in alvo[0]['r'], alvo
            print('  ✓ a fila usa o corrigido (50%), não o bruto (70%)')

            await page.evaluate("()=>showScreen('dashboard')")
            await page.wait_for_timeout(600)
            linhas=await page.evaluate(LINHAS)
            print('  linhas no painel:',linhas)
            assert len(linhas)==2, linhas
            assert any('Certo/Errado' in l and 'saldo +2' in l for l in linhas), linhas
            assert any('Múltipla escolha' in l for l in linhas), linhas
            print('  ✓ painel separa os dois formatos')

            # com um formato só, a linha extra não aparece (repetiria o número de cima)
            um=await page.evaluate('''()=>{
              const s=simFindSub('%s');
              delete s.simStats.porFormato.certoerrado;
              renderSimGlobalStats();
              return document.querySelectorAll('#sim-por-formato .sim-fmt-row').length;
            }''' % SUB)
            assert um==0, f'com um formato só ainda desenhou {um} linha(s)'
            print('  ✓ com um formato só, nada de linha redundante')
            assert not real_errors(errors), real_errors(errors)
        finally:
            await browser.close()
    print('\nOK — estatística de simulado separada por formato, com correção do chute')

asyncio.run(main())
