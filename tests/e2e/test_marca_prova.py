# -*- coding: utf-8 -*-
# Grifar e o que se faz no papel ENQUANTO se le o item, nao depois de corrigir. O
# marca-texto so existia na tela de resultado. Durante a prova ainda nao ha prova
# guardada pra pendurar a marca, entao a chave aponta pro item vivo.
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

        print('=== A) a prova em andamento tem paleta e zona marcavel ===')
        r=await page.evaluate("""async(x)=>{
          (%s)(6);
          simColarIniciar(false);
          await new Promise(r=>setTimeout(r,200));
          const zonas=document.querySelectorAll('#simgeral-content .marca-zona[data-sub]');
          return {paleta:!!document.querySelector('#simgeral-content .sim-ferramentas .marca-pen'),
                  zonas:zonas.length,
                  chave:zonas[0]?zonas[0].getAttribute('data-sub'):null,
                  corrigido:!!simGeralActive.corrected};}"""%LOTE,0)
        print('   paleta: %s · zonas: %s · chave: %r · prova ainda em andamento: %s'
              %(r['paleta'],r['zonas'],r['chave'],not r['corrigido']))
        assert r['paleta'] and r['zonas']==6 and r['chave']=='a:0' and not r['corrigido']
        print('   OK\n')

        print('=== B) as alternativas ficam FORA da zona, pra selecionar nao brigar com responder ===')
        r=await page.evaluate("""()=>{
          const q=document.querySelectorAll('#simgeral-content .sg-q')[0];
          const zona=q.querySelector('.marca-zona');
          return {enunciadoDentro:!!zona.querySelector('.sim-q-text'),
                  altsDentro:!!zona.querySelector('.sim-alt'),
                  altsNoCartao:q.querySelectorAll('.sim-alt').length};}""")
        print('   enunciado dentro da zona: %s · alternativas dentro: %s (o cartão tem %s)'
              %(r['enunciadoDentro'],r['altsDentro'],r['altsNoCartao']))
        assert r['enunciadoDentro'] and not r['altsDentro'] and r['altsNoCartao']==2
        print('   OK\n')

        print('=== C) grifar durante a prova guarda no item vivo ===')
        r=await page.evaluate("""()=>{
          marcaAlvo('a:0').set([{t:'Item 1',n:0,c:'v'}]);
          marcaInvalidar('a:0'); marcaAplicarTodas(true);
          const zona=document.querySelectorAll('#simgeral-content .marca-zona')[0];
          const mk=zona.querySelector('mark.resumo-marca');
          return {naQuestao:(simGeralActive.questoes[0].marcas||[]).length,
                  texto:mk?mk.textContent:null,cor:mk?mk.getAttribute('data-cor'):null};}""")
        print('   marcas no item: %s · grifado: %r (cor %s)'
              %(r['naQuestao'],r['texto'],r['cor']))
        assert r['naQuestao']==1 and r['texto']=='Item 1' and r['cor']=='v'
        print('   OK\n')

        print('=== D) responder nao apaga o grifo ===')
        r=await page.evaluate("""()=>{
          sgSelectAnswer(0,'C'); sgSelectAnswer(1,'E');
          const zona=document.querySelectorAll('#simgeral-content .marca-zona')[0];
          return {grifo:!!zona.querySelector('mark.resumo-marca'),
                  respondeu:simGeralActive.questoes[0].userAnswer,
                  progresso:document.querySelector('.sg-progress').textContent};}""")
        print('   grifo continua: %s · resposta: %r · %s'
              %(r['grifo'],r['respondeu'],r['progresso']))
        assert r['grifo'] and r['respondeu']=='C'
        print('   OK\n')

        print('=== E) finalizar leva o grifo pro resultado ===')
        r=await page.evaluate("""async()=>{
          simGeralActive.questoes.forEach((q,i)=>{if(!q.userAnswer)q.userAnswer=q.correta;});
          simGeralActive.tempoGastoSec=300;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          marcaAplicarTodas(true);
          const zona=document.querySelectorAll('#simgeral-content .marca-zona[data-sub]')[0];
          const mk=zona?zona.querySelector('mark.resumo-marca'):null;
          return {chave:zona?zona.getAttribute('data-sub'):null,
                  grifo:mk?mk.textContent:null,
                  naProva:(provaQuestoes(db.provas[0])[0].marcas||[]).length};}""")
        print('   chave no resultado: %r · grifo: %r · guardado na prova: %s'
              %(r['chave'],r['grifo'],r['naProva']))
        assert r['chave'].startswith('q:') and r['grifo']=='Item 1' and r['naProva']==1
        print('   o grifo feito durante a prova sobreviveu à correção')
        print('   OK\n')

        print('=== F) refazer: o grifo volta ja na tela da prova ===')
        r=await page.evaluate("""()=>{
          window.confirm=()=>true;
          provaRefazer(db.provas[0].id);
          marcaAplicarTodas(true);
          const zona=document.querySelectorAll('#simgeral-content .marca-zona[data-sub]')[0];
          const mk=zona?zona.querySelector('mark.resumo-marca'):null;
          return {emAndamento:!simGeralActive.corrected,
                  chave:zona?zona.getAttribute('data-sub'):null,
                  grifo:mk?mk.textContent:null};}""")
        print('   prova em andamento: %s · chave: %r · grifo: %r'
              %(r['emAndamento'],r['chave'],r['grifo']))
        assert r['emAndamento'] and r['chave']=='a:0' and r['grifo']=='Item 1'
        print('   OK\n')

        print('=== G) grifar na refacao escreve na prova tambem ===')
        r=await page.evaluate("""()=>{
          marcaAlvo('a:1').set([{t:'Item 2',n:0,c:'r'}]);
          return {noVivo:(simGeralActive.questoes[1].marcas||[]).length,
                  naProva:(provaQuestoes(db.provas[0])[1].marcas||[]).length};}""")
        print('   no item vivo: %s · na prova guardada: %s'%(r['noVivo'],r['naProva']))
        assert r['noVivo']==1 and r['naProva']==1
        print('   OK\n')

        print('=== H) clicar no grifo tira ele durante a prova ===')
        r=await page.evaluate("""()=>{
          marcaRemover('a:1',0);
          marcaAplicarTodas(true);
          const zona=document.querySelectorAll('#simgeral-content .marca-zona[data-sub]')[1];
          return {vivo:(simGeralActive.questoes[1].marcas||[]).length,
                  prova:(provaQuestoes(db.provas[0])[1].marcas||[]).length,
                  naTela:!!(zona&&zona.querySelector('mark.resumo-marca'))};}""")
        print('   vivo: %s · prova: %s · na tela: %s'%(r['vivo'],r['prova'],r['naTela']))
        assert r['vivo']==0 and r['prova']==0 and not r['naTela']
        print('   OK\n')

        print('=== I) o resumo continua grifavel, sem confusao de chave ===')
        r=await page.evaluate("""()=>{
          const sub=simFindSub('s1');
          sub.resumo={texto:'A reposicao inicial e de 30 mL/kg.',marcas:[]};
          const d=document.createElement('div');
          d.className='resumo-body'; d.setAttribute('data-sub','s1');
          d.textContent='A reposicao inicial e de 30 mL/kg.';
          document.body.appendChild(d);
          marcaAlvo('s1').set([{t:'30 mL/kg',n:0,c:'a'}]);
          marcaInvalidar('s1'); marcaAplicarTodas(true);
          const ok=!!d.querySelector('mark.resumo-marca');
          d.remove();
          return {ok,guardado:(sub.resumo.marcas||[]).length,
                  provaIntacta:(simGeralActive.questoes[0].marcas||[]).length};}""")
        print('   grifo no resumo: %s · guardado: %s · o da prova não foi afetado: %s'
              %(r['ok'],r['guardado'],r['provaIntacta']==1))
        assert r['ok'] and r['guardado']==1 and r['provaIntacta']==1
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
