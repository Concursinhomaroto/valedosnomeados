# -*- coding: utf-8 -*-
# O banco de provas so guardava o que ja tinha sido feito: prova entrava nele DEPOIS
# de respondida. Agora da pra montar hoje e engavetar, e fazer no sabado — a 1a vez
# conta em tudo, e so a partir da 2a e que vira refacao.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed

def seed():
    return make_seed({'studyNickname':'Leo',
      'kingdoms':[{'id':'k1','name':'Enfermagem','icon':'💉','color':'#22d3ee'}],
      'topics':{'k1':[{'id':'t1','name':'Urgencia','icon':'⚔️','subtopics':[
          {'id':'s1','name':'Choque septico','priority':70,'studied':True},
          {'id':'s2','name':'PCR','priority':70,'studied':True}]}]}})

LOTE = """(n)=>{
  simColarPromptTexto();               // monta simColarLista
  const achar=nome=>simColarLista.findIndex(c=>c.sub.name===nome)+1;
  const arr=[];
  for(let i=0;i<n;i++){
    const nome=i%2?'PCR':'Choque septico';
    arr.push({assunto:achar(nome),assuntoNome:nome,textoApoio:'',
      afirmacao:'Item '+(i+1)+' sobre '+nome+'.',gabarito:i%3?'C':'E',explicacao:'x'});
  }
  document.getElementById('sg-colar-txt').value=JSON.stringify(arr);
  simColarAdicionar();
  return simColarLote.length;}"""

RESPONDER = """(certos)=>{
  simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=i<certos?q.correta:(q.correta==='C'?'E':'C');});
  simGeralActive.tempoGastoSec=600;
  simGeralCorrigir();
  return true;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) guardar pra depois nao comeca a prova ===')
        r=await page.evaluate("""async(lote)=>{
          (%s)(12);
          simColarGuardar(false);
          await new Promise(r=>setTimeout(r,300));
          const pr=(db.provas||[])[0];
          return {provas:(db.provas||[]).length,questoes:pr?pr.questoes.length:0,
                  tentativas:pr?pr.tentativas.length:null,origem:pr?pr.origem:null,
                  loteZerado:simColarLote.length===0,
                  naoComecou:!simGeralActive||!simGeralActive.questoes};}"""%LOTE,0)
        print('   provas no banco: %s · questões: %s · tentativas: %s'
              %(r['provas'],r['questoes'],r['tentativas']))
        print('   lote esvaziado: %s · a prova NÃO começou: %s'%(r['loteZerado'],r['naoComecou']))
        assert r['provas']==1 and r['questoes']==12 and r['tentativas']==0
        assert r['loteZerado'] and r['naoComecou']
        print('   OK\n')

        print('=== B) a lista mostra que ela esta esperando ===')
        r=await page.evaluate("""()=>{
          const h=provasGuardadasHTML();
          // "Refazer" tambem aparece no texto explicativo do topo: o que distingue o
          // botao e o icone (fa-play na nova, fa-rotate-left na ja feita).
          return {selo:h.includes('prova-selo-nova'),fazer:h.includes('fa-play'),
                  nunca:h.includes('Nunca feita'),
                  refazer:h.includes('fa-rotate-left')};}""")
        print('   selo "esperando": %s · botão Fazer (fa-play): %s · "Nunca feita": %s'
              %(r['selo'],r['fazer'],r['nunca']))
        assert r['selo'] and r['fazer'] and r['nunca'] and not r['refazer']
        print('   OK\n')

        print('=== C) a 1a vez NAO e refacao ===')
        r=await page.evaluate("""()=>{window.confirm=()=>true;
          provaRefazer(db.provas[0].id);
          return {refazendo:!!simGeralActive.refazendo,num:simGeralActive.tentativaNum,
                  n:simGeralActive.questoes.length,provaId:!!simGeralActive.provaId};}""")
        print('   refazendo: %s · tentativa nº %s · %s questões'%(r['refazendo'],r['num'],r['n']))
        assert r['refazendo']==False and r['num']==1 and r['n']==12 and r['provaId']
        print('   OK\n')

        print('=== D) respondida a 1a vez: conta nas estatisticas, sem duplicar a prova ===')
        r=await page.evaluate("""async(certos)=>{
          (%s)(certos);
          await new Promise(r=>setTimeout(r,400));
          const st=simFindSub('s1').simStats;
          return {provas:db.provas.length,tentativas:db.provas[0].tentativas.length,
                  acertos:db.provas[0].tentativas[0].acertos,
                  questoesGuardadas:db.provas[0].questoes.length,
                  semRespostaNaQuestao:db.provas[0].questoes.every(q=>q.userAnswer===undefined),
                  statsTentativas:st?st.tentativas:0,statsQuestoes:st?st.questoesTotal:0};}"""%RESPONDER,8)
        print('   provas no banco: %s (não duplicou) · tentativas nela: %s · acertos: %s'
              %(r['provas'],r['tentativas'],r['acertos']))
        print('   simStats do assunto: %s tentativa(s), %s questões'
              %(r['statsTentativas'],r['statsQuestoes']))
        assert r['provas']==1, 'a tentativa tem que entrar na prova que ja existe'
        assert r['tentativas']==1 and r['acertos']==8
        assert r['semRespostaNaQuestao'], 'a resposta pertence a tentativa, nao a questao'
        assert r['statsTentativas']>=1 and r['statsQuestoes']>0, 'a 1a vez tem que contar'
        print('   OK\n')

        print('=== E) a 2a vez e refacao: nao mexe mais nas estatisticas ===')
        r=await page.evaluate("""async(certos)=>{
          const antes=JSON.stringify(simFindSub('s1').simStats);
          window.confirm=()=>true;
          provaRefazer(db.provas[0].id);
          const meta={refazendo:!!simGeralActive.refazendo,num:simGeralActive.tentativaNum};
          (%s)(certos);
          await new Promise(r=>setTimeout(r,400));
          return {...meta,provas:db.provas.length,
                  tentativas:db.provas[0].tentativas.length,
                  acertosT2:db.provas[0].tentativas[1].acertos,
                  statsIgual:JSON.stringify(simFindSub('s1').simStats)===antes};}"""%RESPONDER,11)
        print('   refazendo: %s · tentativa nº %s · tentativas guardadas: %s (%s acertos)'
              %(r['refazendo'],r['num'],r['tentativas'],r['acertosT2']))
        print('   simStats intacto: %s'%r['statsIgual'])
        assert r['refazendo']==True and r['num']==2
        assert r['provas']==1 and r['tentativas']==2 and r['acertosT2']==11
        assert r['statsIgual']
        print('   OK\n')

        print('=== F) a lista deixa de dizer "esperando" depois de feita ===')
        r=await page.evaluate("""()=>{const h=provasGuardadasHTML();
          return {esperando:h.includes('prova-selo-nova'),refazer:h.includes('fa-rotate-left'),
                  duas:/2ª:/.test(h)};}""")
        print('   selo "esperando": %s · botão Refazer (fa-rotate-left): %s · mostra a 2ª tentativa: %s'
              %(r['esperando'],r['refazer'],r['duas']))
        assert not r['esperando'] and r['refazer'] and r['duas']
        print('   OK\n')

        print('=== G) o caminho antigo (fazer direto) continua guardando ===')
        r=await page.evaluate("""async(lote)=>{
          simGeralReset();                 // sai da tela de resultado
          (%s)(6);
          simColarIniciar(false);
          const comecou=simGeralActive.questoes.length;
          simGeralActive.questoes.forEach(q=>{q.userAnswer=q.correta;});
          simGeralActive.tempoGastoSec=60;
          simGeralCorrigir();
          await new Promise(r=>setTimeout(r,400));
          return {comecou,provas:db.provas.length,
                  tentativasDaNova:db.provas[0].tentativas.length};}"""%LOTE,0)
        print('   começou com %s questões · provas no banco: %s · tentativas: %s'
              %(r['comecou'],r['provas'],r['tentativasDaNova']))
        assert r['comecou']==6 and r['provas']==2 and r['tentativasDaNova']==1
        print('   OK\n')

        print('=== H) prova ESPERANDO nao sai; a ja feita sai e deixa as questoes ===')
        r=await page.evaluate("""async(lote)=>{
          simGeralReset();
          db.provas=[]; db.acervo=[]; db.provasArquivo=[];
          // engaveta PROVAS_MAX+4, nenhuma feita
          for(let i=0;i<PROVAS_MAX+4;i++){
            (%s)(4);
            simColarGuardar(false);
          }
          await new Promise(r=>setTimeout(r,300));
          const soEsperando={n:db.provas.length,arq:db.provasArquivo.length};
          // agora marca todas como feitas e guarda mais uma
          db.provas.forEach(p=>{p.tentativas=[{data:new Date().toISOString(),
            respostas:p.questoes.map(q=>q.correta),acertos:p.questoes.length,tempoGastoSec:60}];});
          (%s)(4);
          simColarGuardar(false);
          await new Promise(r=>setTimeout(r,300));
          return {soEsperando, teto:PROVAS_MAX,
                  depois:db.provas.length, arq:db.provasArquivo.length,
                  banco:(db.acervo||[]).length,
                  aEsperandoFicou:db.provas.filter(p=>!provaFoiFeita(p)).length};}"""%(LOTE,LOTE),0)
        print('   %s provas esperando com teto %s → arquivadas: %s'
              %(r['soEsperando']['n'],r['teto'],r['soEsperando']['arq']))
        assert r['soEsperando']['n']==r['teto']+4 and r['soEsperando']['arq']==0
        print('   nenhuma saiu: prova esperando é trabalho marcado, não histórico')
        print('   depois de marcá-las como feitas e guardar mais uma: %s na lista, %s arquivadas'
              %(r['depois'],r['arq']))
        print('   a nova (esperando) ficou: %s · questões no banco: %s'
              %(r['aEsperandoFicou'],r['banco']))
        assert r['arq']>0 and r['banco']>0, 'a prova já feita devia ter saído'
        assert r['aEsperandoFicou']==1
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
