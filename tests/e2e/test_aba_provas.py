# -*- coding: utf-8 -*-
# Colar prova e o banco viviam como preambulo do Simulado Geral — voce rolava pra
# passar por eles. E depois de fechar uma prova nao havia como voltar nela: "Refazer"
# era a unica porta, e refazer apaga justamente o que voce quer ver, as suas respostas.
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

        print('=== A) a terceira aba existe nas tres telas ===')
        r=await page.evaluate("""()=>{
          const out={};
          ['simgeral','provas','caderno','banco'].forEach(t=>{
            const el=document.getElementById('screen-'+t);
            const bs=[...el.querySelectorAll('.rd-conectivos-tabs button')];
            out[t]={n:bs.length,labels:bs.map(x=>x.innerText.trim()),
                    ativa:(bs.find(x=>x.classList.contains('active'))||{}).innerText};
          });
          return out;}""")
        for k,v in r.items():
            print('   %-9s %s abas · ativa: %r'%(k,v['n'],(v['ativa'] or '').strip()))
            assert v['n']==4, v   # entraram "Caderno da Banca" e "Banco de Questões"; Banco de Erros virou secao em Treinar
            assert any('Minhas Provas' in l for l in v['labels']), v['labels']
        assert 'Minhas Provas' in (r['provas']['ativa'] or '')
        print('   OK\n')

        print('=== B) colar prova e o banco agora moram na aba nova ===')
        r=await page.evaluate("""()=>{showScreen('provas');
          const pv=document.getElementById('provas-content').innerText.toUpperCase();
          showScreen('simgeral');
          const sg=document.getElementById('simgeral-content').innerText.toUpperCase();
          return {provasTemColar:pv.includes('COLAR PROVA PRONTA'),
                  simgeralTemColar:sg.includes('COLAR PROVA PRONTA'),
                  simgeralTemConfig:sg.length>50,
                  navAceso:(document.querySelector('.nav-btn.active')||{}).id};}""")
        print('   aba Minhas Provas tem "Colar prova pronta": %s'%r['provasTemColar'])
        print('   Simulado Geral deixou de ter: %s'%(not r['simgeralTemColar']))
        print('   menu lateral aceso em: %s'%r['navAceso'])
        assert r['provasTemColar'] and not r['simgeralTemColar'] and r['simgeralTemConfig']
        print('   OK\n')

        print('=== C) o menu lateral continua apontando pro Simulado Geral ===')
        r=await page.evaluate("()=>{showScreen('provas');return (document.querySelector('.nav-btn.active')||{}).id;}")
        print('   nav aceso na aba provas: %s'%r)
        assert r=='nav-simgeral'
        print('   OK\n')

        print('=== D) fazer uma prova, fechar, e VOLTAR nela pra ver os erros ===')
        r=await page.evaluate("""async(x)=>{
          showScreen('provas');
          (%s)(8);
          simColarIniciar(false);
          // acerta 5, erra 2, deixa 1 em branco
          simGeralActive.questoes.forEach((q,i)=>{
            if(i<5)q.userAnswer=q.correta;
            else if(i<7)q.userAnswer=(q.correta==='C'?'E':'C');});
          simGeralActive.tempoGastoSec=900;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          simGeralReset();
          showScreen('provas');
          const temBotao=!!document.querySelector('button[onclick*="provaRevisar"]');
          provaRevisar(db.provas[0].id);
          const cont=document.getElementById('simgeral-content').innerText;
          const marcadas=simGeralActive.questoes.filter(q=>q.userAnswer).length;
          const acertos=simGeralActive.questoes.filter(q=>q.userAnswer===q.correta).length;
          return {temBotao,revisando:!!simGeralActive.revisando,
                  telaAtiva:document.querySelector('.screen.active').id,
                  marcadas,acertos,
                  titulo:/Revis/i.test(cont),soLeitura:/Só leitura/i.test(cont),
                  semReportar:!/Reportar quest/i.test(cont),
                  temVoltar:/Voltar pras provas/i.test(cont)};}"""%LOTE,0)
        print('   botão "Ver erros" na lista: %s'%r['temBotao'])
        print('   abriu em: %s · modo revisão: %s'%(r['telaAtiva'],r['revisando']))
        print('   respostas remontadas: %s marcadas, %s acertos (1 em branco)'
              %(r['marcadas'],r['acertos']))
        print('   título de revisão: %s · aviso "só leitura": %s'%(r['titulo'],r['soLeitura']))
        assert r['temBotao'] and r['revisando'] and r['telaAtiva']=='screen-simgeral'
        assert r['marcadas']==7 and r['acertos']==5
        assert r['titulo'] and r['soLeitura'] and r['semReportar'] and r['temVoltar']
        print('   sem botão de reportar (não há histórico pra apontar) e com volta pras provas')
        print('   OK\n')

        print('=== E) rever nao mexe em nada: nem prova, nem estatistica, nem XP ===')
        r=await page.evaluate("""()=>{
          const antes={provas:db.provas.length,
                       tent:db.provas[0].tentativas.length,
                       st:JSON.stringify(simFindSub('s1').simStats),
                       xp:db.xp};
          provaRevisar(db.provas[0].id);
          provaRevisar(db.provas[0].id,0);
          return {antes,provas:db.provas.length,tent:db.provas[0].tentativas.length,
                  st:JSON.stringify(simFindSub('s1').simStats),xp:db.xp};}""")
        print('   provas: %s → %s · tentativas: %s → %s'
              %(r['antes']['provas'],r['provas'],r['antes']['tent'],r['tent']))
        print('   simStats intacto: %s · XP intacto: %s'
              %(r['st']==r['antes']['st'],r['xp']==r['antes']['xp']))
        assert r['provas']==r['antes']['provas'] and r['tent']==r['antes']['tent']
        assert r['st']==r['antes']['st'] and r['xp']==r['antes']['xp']
        print('   OK\n')

        print('=== F) a nota escrita e o grifo aparecem na revisao ===')
        r=await page.evaluate("""()=>{
          const id=db.provas[0].id;
          provaEscreverCampo(db.provas[0],0,'minhaNota','Errei porque troquei com o pediatrico.');
          marcaAlvo('q:'+id+':0').set([{t:'Item 1',n:0,c:'v'}]);
          provaRevisar(id);
          marcaAplicarTodas(true);
          const zona=document.querySelector('.marca-zona[data-sub]');
          return {caixa:(document.getElementById('sim-nota-0')||{}).value||'',
                  grifo:!!(zona&&zona.querySelector('mark.resumo-marca')),
                  chave:zona?zona.getAttribute('data-sub'):null};}""")
        print('   nota na caixa: %r'%r['caixa'][:40])
        print('   grifo redesenhado: %s · zona: %r'%(r['grifo'],r['chave']))
        assert r['caixa'].startswith('Errei porque') and r['grifo']
        print('   OK\n')

        print('=== G) tentativa que nao existe nao abre ===')
        r=await page.evaluate("""async(x)=>{
          simGeralReset(); showScreen('provas');
          (%s)(4); simColarGuardar(false);
          await new Promise(r=>setTimeout(r,300));
          const nova=db.provas[0];
          const antes=simGeralActive;
          provaRevisar(nova.id);
          return {tentativas:(nova.tentativas||[]).length,
                  naoAbriu:simGeralActive===antes,
                  semBotaoVer:!document.querySelector('[onclick*="provaRevisar(\\''+nova.id+'\\')"]')};}"""%LOTE,0)
        print('   prova nunca feita: %s tentativas · a revisão não abriu: %s'
              %(r['tentativas'],r['naoAbriu']))
        print('   e ela não mostra botão "Ver erros": %s'%r['semBotaoVer'])
        assert r['tentativas']==0 and r['naoAbriu'] and r['semBotaoVer']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
