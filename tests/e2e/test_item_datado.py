# -*- coding: utf-8 -*-
# Item datado nao parece errado, parece certo. O de consultas de pre-natal trazia o
# minimo de 6 (Caderno de Atencao Basica 32, de 2012) sem dizer de onde tirou, e quem
# estudou a atualizacao marcou pensando no numero vigente. Punir o aluno por saber a
# versao nova e o pior sinal que o app pode mandar.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed
from test_banco_provas import LOTE

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) o quarto botao aparece no erro E no acerto ===')
        r=await page.evaluate("""async(x)=>{
          (%s)(8);
          simColarIniciar(false);
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=i<5?q.correta:(q.correta==='C'?'E':'C');});
          simGeralActive.tempoGastoSec=600;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          const cx=[...document.querySelectorAll('.sim-motivo')];
          return {certo:cx[0].innerText.replace(/\\n/g,' ').trim(),
                  errado:cx[5].innerText.replace(/\\n/g,' ').trim()};}"""%LOTE,0)
        print('   no acerto: %r'%r['certo'])
        print('   no erro:   %r'%r['errado'])
        assert 'Item desatualizado' in r['certo'] and 'Item desatualizado' in r['errado']
        assert 'Não sabia' in r['errado'] and 'Acertei no chute' in r['certo']
        print('   OK\n')

        print('=== B) marcar como datado tira o item da estatistica do assunto ===')
        r=await page.evaluate("""()=>{
          const q=simGeralActive.questoes[5];
          const sub=simFindSub(q.subId);
          const antes={qt:sub.simStats.questoesTotal,ac:sub.simStats.acertosTotal,
                       flag:!!q.problematico};
          simMotivoSalvar(5,'datado');
          return {antes,motivo:q.motivo,flag:!!q.problematico,
                  qt:sub.simStats.questoesTotal,ac:sub.simStats.acertosTotal,
                  naProva:db.provas[0].questoes[5].motivo,
                  banner:/não conta nas suas estat/i.test(document.querySelectorAll('.sim-q')[5].innerText)};}""")
        print('   antes: %s questões na estatística · depois: %s'%(r['antes']['qt'],r['qt']))
        print('   motivo: %r · marcado como problemático: %s'%(r['motivo'],r['flag']))
        print('   aviso na questão: %s'%r['banner'])
        assert r['motivo']=='datado' and r['naProva']=='datado'
        assert r['flag'] and r['qt']==r['antes']['qt']-1
        print('   OK\n')

        print('=== C) desmarcar devolve o item pra estatistica ===')
        r=await page.evaluate("""()=>{
          const q=simGeralActive.questoes[5];
          const sub=simFindSub(q.subId);
          const antes=sub.simStats.questoesTotal;
          simMotivoSalvar(5,'datado');
          return {antes,motivo:q.motivo||'',flag:!!q.problematico,
                  qt:sub.simStats.questoesTotal};}""")
        print('   %s -> %s questões · motivo: %r · problemático: %s'
              %(r['antes'],r['qt'],r['motivo'],r['flag']))
        assert r['motivo']=='' and not r['flag'] and r['qt']==r['antes']+1
        print('   OK\n')

        print('=== D) trocar de datado para outro motivo devolve o item tambem ===')
        r=await page.evaluate("""()=>{
          const q=simGeralActive.questoes[6];
          const sub=simFindSub(q.subId);
          simMotivoSalvar(6,'datado');
          const meio={qt:sub.simStats.questoesTotal,flag:!!q.problematico};
          simMotivoSalvar(6,'conteudo');
          return {meio,motivo:q.motivo,flag:!!q.problematico,qt:sub.simStats.questoesTotal};}""")
        print('   datado: %s questões (problemático %s) -> conteúdo: %s questões (problemático %s)'
              %(r['meio']['qt'],r['meio']['flag'],r['qt'],r['flag']))
        assert r['motivo']=='conteudo' and not r['flag'] and r['qt']==r['meio']['qt']+1
        print('   OK\n')

        print('=== E) o painel conta datado separado dos tres baldes ===')
        r=await page.evaluate("""()=>{
          simMotivoSalvar(5,'datado');
          simMotivoSalvar(7,'atencao');
          const ag=motivosAgregado();
          simGeralActive=null; showScreen('dashboard');
          const txt=document.getElementById('controle-erros').innerText.replace(/\\n/g,' | ');
          return {tot:ag.tot,txt};}""")
        print('   baldes: %s'%r['tot'])
        print('   painel: %s'%r['txt'][:200])
        assert r['tot']['datado']==1
        assert 'desatualizado' in r['txt']
        # datado nao pode virar o veredito: ele nao e diagnostico do aluno
        assert 'Gargalo' in r['txt'] and 'desatualizad' not in r['txt'].split('Gargalo')[1][:90]
        print('   e não entra no veredito — o gargalo continua sendo sobre você')
        print('   OK\n')

        print('=== F) na revisao o rotulo fica, mesmo sem poder mexer na estatistica ===')
        r=await page.evaluate("""()=>{
          provaRevisar(db.provas[0].id);
          const antes=simFindSub('s1').simStats.questoesTotal
                     +simFindSub('s2').simStats.questoesTotal;
          simMotivoSalvar(3,'datado');
          const depois=simFindSub('s1').simStats.questoesTotal
                      +simFindSub('s2').simStats.questoesTotal;
          return {motivo:simGeralActive.questoes[3].motivo,
                  naProva:db.provas[0].questoes[3].motivo,
                  statsIntacto:antes===depois,
                  temHist:!!simGeralActive.questoes[3]._histId};}""")
        print('   motivo guardado: %r (na prova: %r)'%(r['motivo'],r['naProva']))
        print('   sem _histId na revisão: %s · estatística intacta: %s'
              %(not r['temHist'],r['statsIntacto']))
        assert r['motivo']=='datado' and r['naProva']=='datado'
        assert not r['temHist'] and r['statsIntacto']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
