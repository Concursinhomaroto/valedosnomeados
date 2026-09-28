# -*- coding: utf-8 -*-
# Modo Treino completo (redesenho pedido pelo usuário, prompt PROMPT-modo-treino.md) —
# Parte 1: abrir, escolher, responder e controlar tudo, sem nunca criar prova.
#
# Bug relatado: clicar num deck da tela Treinar gerava uma prova em db.provas ("Simulado
# 29 — Geral · 954 questões · treino"), Treinar e Acervo mostravam números diferentes
# (1.136 x 2.563 — o pool de treino era só db.acervo, sem as questões dentro de provas
# esperando/arquivadas), e nada do que era respondido no treino contava em lugar nenhum.
#
# treinarComDeck agora abre treinoSessao diretamente (sem montarProvaDeItens/provaRefazer).
# treinoPoolCompleto() reusa montarAcervo() (a mesma função que a tela Acervo já usa pro
# total dela) — Treinar e Acervo bater no mesmo número é garantido por construção, não por
# duas contas paralelas. Cada resposta escreve DIRETO no item do Acervo, na hora, fora do
# saveDB — fechar a aba no meio não perde nada.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

KING='king-mt1'; TOPIC='topic-mt1'; SUB='sub-mt1'; SUB2='sub-mt2'

def seed():
    return make_seed({
        'kingdoms':[{'id':KING,'name':'Enfermagem','icon':'💉'}],
        'topics':{KING:[{'id':TOPIC,'name':'Urgência','subtopics':[
            {'id':SUB,'name':'Choque Séptico','priority':100,'studied':True},
            {'id':SUB2,'name':'Trauma','priority':100,'studied':True}]}]}})

QS_JS = """(subId,subName,n,tag)=>{
  const arr=[];
  for(let i=0;i<n;i++)arr.push({questao:tag+' item '+i+' sobre '+subName,correta:i%2?'C':'E',
    formato:'certoerrado',alternativas:[{letra:'C',texto:'Certo'},{letra:'E',texto:'Errado'}],
    explicacao:'x',subId,subName,topicName:'Urgência',
    kingdomId:'king-mt1',kingdomName:'Enfermagem',kingdomIcon:'💉'});
  return arr;}"""

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS_JS)
        await page.evaluate("()=>{showScreen('simgeral');return true;}")

        print('=== A) clicar num deck NAO cria prova — abre a sessão direto ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          QS('sub-mt1','Choque Séptico',6,'A').forEach(q=>{
            db.acervo.push({...q,_chaveForte:acervoChave2(q),tags:[],favorita:false,status:'ativa',
              vezesRespondida:0,acertos:0,erros:0,ultimaVezEm:null,dificuldadeAferida:null,
              certezaAcertos:0,certezaErros:0,duvidaAcertos:0,duvidaErros:0,chuteAcertos:0,chuteErros:0,
              criacao:new Date().toISOString(),origem:'ia'});});
          const provasAntes=db.provas.length;
          treinarComDeck('nuncavistas');
          return {provasAntes,provasDepois:db.provas.length,
                  sessaoAberta:!!treinoSessao,itens:treinoSessao?treinoSessao.itens.length:0};}""")
        print('   %s'%r)
        assert r['provasAntes']==0 and r['provasDepois']==0
        assert r['sessaoAberta'] and r['itens']==6
        print('   OK\n')

        print('=== B) responder atualiza o Acervo NA HORA, direto, sem repetir na sessão ===')
        r=await page.evaluate("""()=>{
          const item0=treinoSessao.itens[0];
          treinoResponder(item0.correta);
          const depois=db.acervo.find(x=>x._chaveForte===item0._chaveForte);
          return {vezes:depois.vezesRespondida,acertos:depois.acertos,ultimoResultado:depois.ultimoResultado,
                  respondidasSet:[...treinoSessao.respondidasSet]};}""")
        print('   %s'%r)
        assert r['vezes']==1 and r['acertos']==1 and r['ultimoResultado']=='C'
        assert r['respondidasSet']==[0]
        print('   OK\n')

        print('=== C) errar marca motivo, favorita, nota e cria flashcard sozinho ===')
        r=await page.evaluate("""()=>{
          treinoProxima();
          const item1=treinoSessao.itens[1];
          const errada=item1.correta==='C'?'E':'C';
          treinoResponder(errada);
          treinoMotivoSalvar('conteudo');
          treinoFavoritar();
          document.getElementById('treino-nota').value='minha nota';
          treinoNotaSalvar();
          treinoEnviarFlashcard();
          const depois=db.acervo.find(x=>x._chaveForte===item1._chaveForte);
          return {erros:depois.erros,motivo:depois.motivo,favorita:depois.favorita,
                  nota:depois.minhaNota,cards:Object.values(db.flashcards||{}).length};}""")
        print('   %s'%r)
        assert r['erros']==1 and r['motivo']=='conteudo' and r['favorita'] and r['nota']=='minha nota'
        assert r['cards']==1
        print('   OK\n')

        print('=== D) pular não conta nem como acerto nem como erro, e dá pra voltar ===')
        r=await page.evaluate("""()=>{
          treinoProxima();
          const item2=treinoSessao.itens[2];
          treinoPular();
          const depois=db.acervo.find(x=>x._chaveForte===item2._chaveForte);
          const idxDepoisPular=treinoSessao.idx;
          treinoAnterior();
          return {vezes:depois.vezesRespondida,idxDepoisPular,idxDepoisVoltar:treinoSessao.idx};}""")
        print('   %s'%r)
        assert r['vezes']==0
        assert r['idxDepoisPular']==3 and r['idxDepoisVoltar']==2
        print('   OK\n')

        print('=== E) fechar a sessão ("fechar a aba") não perde nada — nada some, nada fica pendente ===')
        r=await page.evaluate("""()=>{
          const antes={acervo:db.acervo.length,provas:db.provas.length};
          treinoSessao=null;
          showScreen('simgeral');renderSimGeralScreen();
          return {igual:db.acervo.length===antes.acervo&&db.provas.length===antes.provas,
                  contam:db.acervo.filter(x=>x.vezesRespondida>0).length};}""")
        print('   %s'%r)
        assert r['igual'] and r['contam']==2
        print('   OK\n')

        print('=== F) prova ESPERANDO (colada, nunca feita) entra no pool — responder não a marca como feita ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          const qs=QS('sub-mt2','Trauma',4,'Esperando');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const noPool=treinoPoolCompleto().filter(q=>q.questao.includes('Esperando')).length;
          treinarComDeck('nuncavistas');
          const idx=treinoSessao.itens.findIndex(it=>it.questao.includes('Esperando'));
          if(idx>=0){treinoSessao.idx=idx;treinoResponder(treinoSessao.itens[idx].correta);}
          const prova=provaAchar(id);
          return {noPool,respondeuAlgumaEsperando:idx>=0,
                  continuaEsperando:prova&&!(prova.tentativas||[]).length,
                  continuaExistindo:!!prova};}""")
        print('   %s'%r)
        assert r['noPool']==4, 'as 4 questões da prova esperando tinham que entrar no pool de treino'
        assert r['respondeuAlgumaEsperando']
        assert r['continuaEsperando'], 'responder no treino NAO pode marcar a prova esperando como feita'
        assert r['continuaExistindo'], 'a prova esperando continua intacta em Minhas Provas'
        print('   OK\n')

        print('=== G) Treinar e Acervo usam o MESMO pool (treinoPoolCompleto reusa montarAcervo) ===')
        r=await page.evaluate("""()=>{
          return {treinar:treinoPoolCompleto().length,acervo:montarAcervo().length};}""")
        print('   %s'%r)
        assert r['treinar']==r['acervo'], 'sem item em quarentena no cenário, os dois têm que bater'
        print('   OK\n')

        print('=== H) encerrar registra no histórico de treinos, mostra resumo, "só as que errei" reabre sessão ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];db.treinoHistorico=[];
          const qs=QS('sub-mt1','Choque Séptico',2,'Resumo');
          treinoIniciar(qs,{titulo:'Teste resumo'});
          treinoResponder(treinoSessao.itens[0].correta);
          treinoProxima();
          const errada=treinoSessao.itens[1].correta==='C'?'E':'C';
          treinoResponder(errada);
          treinoEncerrar();
          const resumo1={certas:treinoResumo.certas,erradas:treinoResumo.erradas,
                          historico:db.treinoHistorico.length,itensErrados:treinoResumo.itensErrados.length};
          treinoTreinarErradas();
          return {...resumo1,sessaoReaberta:!!treinoSessao,
                  itensNaSessaoNova:treinoSessao?treinoSessao.itens.length:0,resumoLimpo:!treinoResumo};}""")
        print('   %s'%r)
        assert r['certas']==1 and r['erradas']==1 and r['historico']==1 and r['itensErrados']==1
        assert r['sessaoReaberta'] and r['itensNaSessaoNova']==1 and r['resumoLimpo']
        print('   OK\n')

        print('=== I) "Fazer simulado" é o único caminho que cria prova — abre a montagem avançada ===')
        r=await page.evaluate("""()=>{
          treinoSessao=null;treinoResumo=null;
          showScreen('simgeral');renderSimGeralScreen();
          return {temBotao:!!document.querySelector('.treino-topo-entrada button')};}""")
        assert r['temBotao']
        await page.click(".treino-topo-entrada button")
        aberto=await page.evaluate("()=>document.getElementById('treinar-avancado').style.display!=='none'")
        print('   montagem avançada abriu ao clicar Fazer simulado:',aberto)
        assert aberto
        print('   OK\n')

        print('=== J) a tela Treinar NÃO tem mais o histórico de Simulado Geral — ele foi pra Minhas Provas ===')
        r=await page.evaluate("""()=>{
          db.simGeral={historico:[{id:'h1',data:new Date().toISOString(),quantidade:10,acertos:8,
            tempoGastoSec:600,formato:'certoerrado',nivel:'dificil',assuntos:[]}]};
          renderSimGeralScreen();
          const naTreinar=document.getElementById('simgeral-content').innerHTML.includes('Histórico de Simulados Gerais');
          const naMinhasProvas=document.getElementById('provas-content').innerHTML.includes('Histórico de Simulados Gerais');
          return {naTreinar,naMinhasProvas};}""")
        print('   %s'%r)
        assert not r['naTreinar'], 'histórico de simulados não pode mais aparecer na tela Treinar'
        assert r['naMinhasProvas'], 'histórico de simulados tem que aparecer em Minhas Provas'
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
