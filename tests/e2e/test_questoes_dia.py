# -*- coding: utf-8 -*-
# Questões de hoje: quantas questões você respondeu no dia. Cada questão conta uma vez;
# responder de novo a mesma (no mesmo dia ou dentro de 7 dias) não soma — só volta a
# contar depois de 7 dias. O número aparece num cartão da faixa do Painel, que abre o
# detalhe (por assunto, últimos 7 dias, certas/erradas).
import asyncio, sys, datetime
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

def seed():
    subs=[{'id':'s%d'%i,'name':'Assunto %d'%i,'priority':70,'studied':True,'studiedAt':'2026-01-01'} for i in range(2)]
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉'}],
      'topics':{'k1':[{'id':'t1','name':'Urgência','icon':'⚔️','subtopics':subs}]}})

ACERVO="""()=>{db.acervo=[];
  ['s0','s1'].forEach((sid,si)=>{for(let j=0;j<4;j++){
    const q={questao:'Questão '+j+' do assunto '+sid+': julgue o item.',correta:'C',formato:'certoerrado',
      alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],explicacao:'.',
      subId:sid,subName:'Assunto '+si,topicName:'Urgência',kingdomId:'k1',kingdomName:'Enfermagem',kingdomIcon:'💉'};
    db.acervo.push({...q,_chaveForte:acervoChave2(q),...acervoCamposNovos('ia')});}});
  return db.acervo.length;}"""

# Responde n questões do pool pelo caminho real do Treinar (selecionar + confirmar).
RESPONDE="""([ids,letra])=>{const pool=db.acervo.filter(q=>ids.includes(q._chaveForte));
  treinoIniciar(pool,{titulo:'teste'});
  for(let k=0;k<pool.length&&treinoSessao;k++){treinoSelecionar(letra||'C');treinoConfirmarResposta();if(k<pool.length-1)treinoProxima();}
  treinoSessao=null;treinoResumo=null;return questoesDiaResumo().n;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate(ACERVO)
        chaves=await page.evaluate("()=>db.acervo.map(q=>q._chaveForte)")

        print('=== A) responder 3 questões conta 3; o cartão do Painel mostra ===')
        n=await page.evaluate(RESPONDE,[chaves[:3],'C'])
        await page.evaluate("()=>showScreen('dashboard')")
        r=await page.evaluate("()=>({val:document.getElementById('dash-questoes-val').textContent,sub:document.getElementById('dash-questoes-sub').textContent})")
        print('   contagem=%s · cartão=%s'%(n,r))
        assert n==3 and r['val']=='3' and '3 certas' in r['sub']
        print('   OK\n')

        print('=== B) responder as mesmas de novo no mesmo dia não soma; uma nova soma ===')
        n=await page.evaluate(RESPONDE,[chaves[:4],'E'])
        print('   contagem=%s'%n)
        assert n==4, 'só a questão nova (a 4ª) entra'
        r=await page.evaluate("()=>db.acervo.filter(q=>q.contadaEm).map(q=>q.contadaResultado)")
        print('   resultados contados: %s'%r)
        assert sorted(r)==['C','C','C','X'], 'a contagem guarda o resultado da vez que contou'
        print('   OK\n')

        print('=== C) refazer dentro de 7 dias não conta; depois de 7 dias conta de novo ===')
        r=await page.evaluate("""(ids)=>{const hoje=todayStr();
          db.acervo.forEach(q=>{if(q.contadaEm){q.contadaEm=addDays(hoje,-6);}});
          const antes=questoesDiaResumo().n;
          const pool=db.acervo.filter(q=>ids.includes(q._chaveForte));
          treinoIniciar(pool,{titulo:'x'});treinoSelecionar('C');treinoConfirmarResposta();treinoSessao=null;
          const seis=questoesDiaResumo().n;
          db.acervo.forEach(q=>{if(q.contadaEm&&q.contadaEm!==hoje)q.contadaEm=addDays(hoje,-7);});
          treinoIniciar(pool,{titulo:'y'});treinoSelecionar('C');treinoConfirmarResposta();treinoSessao=null;
          const sete=questoesDiaResumo().n;
          return {antes,seis,sete};}""",chaves[:1])
        print('   %s'%r)
        # o registro do dia só soma quando a questão volta a contar (7 dias depois)
        assert r['seis']==r['antes'] and r['sete']==r['antes']+1
        print('   OK\n')

        print('=== D) questão antiga (sem contadaEm) respondida há 3 dias não conta de novo hoje ===')
        r=await page.evaluate("""(ids)=>{const q=db.acervo.find(x=>x._chaveForte===ids[0]);
          delete q.contadaEm;q.ultimaVezEm=new Date(Date.now()-3*86400000).toISOString();
          return questoesDiaDeveContar(q,todayStr());}""",chaves[5:6])
        assert r is False
        print('   OK\n')

        print('=== E) o painel abre com hoje, acumulado, 14 dias, tabela, assuntos e a regra ===')
        r=await page.evaluate("""()=>{document.getElementById('dash-questoes-card').click();
          const b=document.getElementById('modal-body');
          const out={dias:b.querySelectorAll('.qd-dia').length,linhas:b.querySelectorAll('.qd-linha').length,
            tabela:b.querySelectorAll('.qd-tr').length,regra:b.querySelector('.qd-regra').textContent};closeModal();return out;}""")
        print('   %s'%r)
        assert r['dias']==14 and r['linhas']>=1 and r['tabela']>=3 and '7 dias' in r['regra']
        print('   OK\n')

        print('=== G) registro por dia: feitas/certas/erradas vão acumulando, inclusive dias antigos ===')
        r=await page.evaluate("""()=>{const hoje=todayStr();const reg=db.questoesPorDia||{};
          const h=JSON.parse(JSON.stringify(reg[hoje]||{}));
          reg[addDays(hoje,-1)]={n:20,c:15,x:5};reg[addDays(hoje,-30)]={n:10,c:4,x:6};db.questoesPorDia=reg;
          const hist=questoesHistorico();
          questoesDiaAbrir();const b=document.getElementById('modal-body');
          const tot=b.querySelector('.qd-tr-tot').textContent.replace(/\\s+/g,' ').trim();closeModal();
          return {h,dias:hist.dias.map(x=>x.n),tot:hist.tot,media:hist.mediaDia,linhaTotal:tot};}""")
        print('   %s'%r)
        assert r['h']['n']==r['h']['c']+r['h']['x'] and r['h']['n']==5
        assert r['dias']==[5,20,10] and r['tot']=={'n':35,'c':15+4+r['h']['c'],'x':5+6+r['h']['x']}
        assert r['linhaTotal'].replace(' ','').startswith('Total35')
        print('   OK\n')

        print('=== F) abrir o Painel e o detalhe não grava nada ===')
        r=await page.evaluate("""()=>{window.__s=0;const o=window.saveDB,oa=window.acervoSalvar;
          window.saveDB=function(){window.__s++;return o.apply(this,arguments)};
          window.acervoSalvar=function(){window.__s++;return oa.apply(this,arguments)};
          showScreen('dashboard');questoesDiaAbrir();closeModal();return window.__s;}""")
        assert r==0, r
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
