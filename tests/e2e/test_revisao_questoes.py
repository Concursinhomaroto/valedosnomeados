# -*- coding: utf-8 -*-
# Máquina de vencer v2: revisar por questões. O passo 1 do cartão pega os assuntos da fila
# oficial até a cota de hoje (só os que têm questão), monta até 4 de cada (erradas, depois
# nunca vistas, depois as mais antigas) e, no fim, mostra cada assunto com o acerto e uma
# nota sugerida. Nada é gravado na revisão até você clicar em "Registrar revisões" — e o
# registro é o mesmo revConcluirDaFila do "Revisei".
import asyncio, sys, datetime
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

hoje=(datetime.datetime.utcnow()-datetime.timedelta(hours=3)).date()
def d(n): return (hoje+datetime.timedelta(days=n)).isoformat()

def seed():
    subs=[{'id':'s%d'%i,'name':'Assunto %d'%i,'priority':70,'studied':True,'studiedAt':d(-60)} for i in range(4)]
    return make_seed({'studyNickname':'Leo','dailyGoalMinutes':240,
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]},
      # s0, s1, s2 vencidos; s3 com prazo futuro (fora da fila)
      'revisions':{'s0':[{'date':d(-10),'completed':False}],'s1':[{'date':d(-5),'completed':False}],
                   's2':[{'date':d(-3),'completed':False}],'s3':[{'date':d(20),'completed':False}]}})

# s0: 6 questões (2 erradas); s1: 3 questões; s2: 1 questão (pouco — fica de fora); s3: 5
ACERVO="""()=>{db.acervo=[];let n=0;
  const add=(sid,extra)=>{const q={questao:'Q'+(n++)+' '+sid+': julgue o item.',correta:'C',formato:'certoerrado',
    alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',subId:sid,subName:'Assunto '+sid.slice(1),
    topicName:'Urgência',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia'),...extra});};
  const dias=x=>new Date(Date.now()-x*86400000).toISOString();
  add('s0',{vezesRespondida:1,erros:1,ultimoResultado:'X',ultimaVezEm:dias(4),tag:'errada'});
  add('s0',{vezesRespondida:1,erros:1,ultimoResultado:'X',ultimaVezEm:dias(9),tag:'errada'});
  for(let i=0;i<4;i++)add('s0',{tag:'nova'});
  for(let i=0;i<3;i++)add('s1',{});
  add('s2',{});
  for(let i=0;i<5;i++)add('s3',{});
  return db.acervo.length;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)

        print('=== A) monta pela fila oficial: s0 (4: as 2 erradas primeiro) e s1 (3); s2 sem questão suficiente ===')
        r=await page.evaluate("""()=>{const m=trevMontar();
          return {assuntos:m.assuntos.map(a=>[a.subId,a.itens.length]),s0:m.assuntos[0].itens.map(q=>q.tag),
            semQ:m.semQuestao.map(c=>c.sub.id),total:m.itens.length,fila:numerosDoDia().fila.map(c=>c.sub.id)};}""")
        print('   %s'%r)
        assert r['assuntos']==[['s0',4],['s1',3]] and r['s0'][:2]==['errada','errada'] and r['semQ']==['s2']
        assert 's3' not in r['fila']
        print('   OK\n')

        print('=== B) cartão: passo 1 com contagem, metas de questões e revisões ===')
        r=await page.evaluate("""()=>{showScreen('simgeral');const c=document.querySelector('.treino-destaque');
          return {passo:c.querySelector('.ti-passo .treino-destaque-sub').textContent,semq:(c.querySelector('.ti-semq')||{}).textContent,
            metas:[...c.querySelectorAll('.ti-meta span')].map(x=>x.textContent),
            primeiro:document.querySelector('.treino-entrada').firstElementChild.contains(c)};}""")
        print('   %s'%r)
        assert r['passo'].startswith('2 assuntos da fila de hoje · 7 questões') and 'Assunto 2' in r['semq']
        assert r['metas'][0].endswith('0/30 questões') and '0/' in r['metas'][1] and r['primeiro']
        print('   OK\n')

        print('=== C) sessão: responder NÃO grava revisão sozinho; o fim sugere a nota pelo acerto ===')
        r=await page.evaluate("""()=>{const antes=JSON.stringify(db.revisions);
          trevComecar();const s=treinoSessao;
          for(let k=0;k<s.itens.length;k++){const it=s.itens[s.idx];
            // s0: acerta 3 de 4 (75%) · s1: erra 2 de 3 (33%)
            const acertar=it.subId==='s0'?(s.itens.filter((x,i)=>x.subId==='s0'&&s.respondidasSet.has(i)).length<3)
                                         :(s.itens.filter((x,i)=>x.subId==='s1'&&s.respondidasSet.has(i)).length<1);
            treinoSelecionar(acertar?'C':'E');treinoConfirmarResposta();if(k<s.itens.length-1)treinoProxima();}
          const mudouAntes=JSON.stringify(db.revisions)!==antes;
          treinoEncerrar();
          const linhas=[...document.querySelectorAll('.trev-linha')].map(l=>({nome:l.querySelector('.trev-nome').textContent,
            placar:l.querySelector('.trev-placar').textContent,nota:l.querySelector('.trev-nota').value}));
          return {titulo:treinoResumo.titulo,mudouAntes,linhas};}""")
        print('   %s'%r)
        assert r['titulo']=='🔁 Revisão por questões' and not r['mudouAntes']
        assert r['linhas']==[{'nome':'Assunto 0','placar':'3/4 · 75%','nota':'4'},{'nome':'Assunto 1','placar':'1/3 · 33%','nota':'1'}]
        print('   OK\n')

        print('=== D) "Registrar revisões" grava pelo mesmo caminho do "Revisei" (igual ao botão da fila) ===')
        r=await page.evaluate("""()=>{
          const espelho=JSON.parse(JSON.stringify(db.revisions));
          trevRegistrar();
          const via=JSON.stringify([db.revisions.s0,db.revisions.s1]);
          // o mesmo efeito pelo botão da fila, num banco espelho
          const real=db.revisions;db.revisions=espelho;
          revConcluirDaFila('s0',4);revConcluirDaFila('s1',1);
          const botao=JSON.stringify([db.revisions.s0,db.revisions.s1]);db.revisions=real;
          return {iguais:via===botao,ok:document.querySelector('.trev-ok')?.textContent||'',
            naFila:numerosDoDia().fila.map(c=>c.sub.id),feitas:trevFeitasHoje()};}""")
        print('   %s'%r)
        assert r['iguais'] and '2 revisões registradas' in r['ok'] and r['naFila']==['s2'] and r['feitas']==2
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
