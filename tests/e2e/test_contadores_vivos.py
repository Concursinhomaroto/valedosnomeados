# -*- coding: utf-8 -*-
# Passo 7 (escopo reduzido, combinado com o usuario: so dados/backend, navegacao fica
# pro passo 8) do plano do Banco de Questoes.
#
# Ate aqui, vezesRespondida/acertos/erros/ultimaVezEm/dificuldadeAferida de um item so
# eram atualizados na EVICTION (acervoGuardarProva, chamado por provasAparar/provaApagar)
# — enquanto a prova (ja convertida por chave, passo 6) ficava guardada em db.provas, o
# que pode levar bastante tempo, esses numeros ficavam parados/errados. Este arquivo
# cobre a contraparte AO VIVO (provaRegistrarTentativaNoAcervo, chamada na correcao),
# o carimbo de "como era antes" pra tela de resultado comparar, a garantia de nao contar
# duas vezes quando a prova enfim for evictada, o botao manual de flashcard e a ponte
# entre "item desatualizado" e o status do Banco de Questoes.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) o contador do acervo atualiza NA CORRECAO, sem esperar eviction nenhuma ===')
        await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];db.flashcards={};
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'A');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          // 3 certas, a ultima errada — pra ter os dois lados carimbados.
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=i<3?q.correta:(q.correta==='C'?'E':'C');});
          simGeralActive.tempoGastoSec=60;
          simGeralCorrigir();
          return true;}""")
        await page.wait_for_timeout(400)
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const itens=prova.chaves2.map(k=>db.acervo.find(x=>x._chaveForte===k));
          return {vezes:itens.map(x=>x.vezesRespondida),acertos:itens.map(x=>x.acertos),
                  erros:itens.map(x=>x.erros),ultimo:itens.map(x=>x.ultimoResultado)};}""")
        print('   vezesRespondida (sem NENHUMA eviction ter rodado): %s'%r['vezes'])
        print('   acertos: %s · erros: %s · ultimoResultado: %s'%(r['acertos'],r['erros'],r['ultimo']))
        assert r['vezes']==[1,1,1,1]
        assert r['acertos']==[1,1,1,0]
        assert r['erros']==[0,0,0,1]
        assert r['ultimo']==['C','C','C','X']
        print('   OK\n')

        print('=== B) _historicoAntes carimba o estado de ANTES desta tentativa, nao o de depois ===')
        r=await page.evaluate("""()=>{
          const provaId=db.provas[0].id;
          provaRefazer(provaId);
          simGeralActive.questoes.forEach(q=>q.userAnswer=q.correta);   // 2a tentativa: tudo certo
          simGeralActive.tempoGastoSec=30;
          simGeralCorrigir();
          return {historico:simGeralActive.questoes.map(q=>q._historicoAntes)};}""")
        print('   _historicoAntes de cada questao: %s'%r['historico'])
        assert all(h and h['vezes']==1 for h in r['historico'])
        assert r['historico'][0]['acertos']==1   # tinha acertado na 1a
        assert r['historico'][3]['acertos']==0   # tinha errado na 1a
        print('   OK\n')

        print('=== C) depois da 2a tentativa os contadores SOMAM (nao substituem) ===')
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const itens=prova.chaves2.map(k=>db.acervo.find(x=>x._chaveForte===k));
          return {vezes:itens.map(x=>x.vezesRespondida),acertos:itens.map(x=>x.acertos)};}""")
        print('   vezesRespondida: %s · acertos: %s'%(r['vezes'],r['acertos']))
        assert r['vezes']==[2,2,2,2]
        assert r['acertos']==[2,2,2,1]   # o item 3 so acertou na 2a
        print('   OK\n')

        print('=== D) evictar a prova (acervoGuardarProva) NAO conta de novo — ja foi ao vivo ===')
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const antes=prova.chaves2.map(k=>db.acervo.find(x=>x._chaveForte===k).vezesRespondida);
          acervoGuardarProva(prova);
          const depois=prova.chaves2.map(k=>db.acervo.find(x=>x._chaveForte===k).vezesRespondida);
          return {antes,depois};}""")
        print('   vezesRespondida antes da eviction: %s · depois: %s'%(r['antes'],r['depois']))
        assert r['antes']==r['depois']==[2,2,2,2]
        print('   OK\n')

        print('=== E) botao manual de flashcard e seguro pra clicar duas vezes na mesma questao ===')
        r=await page.evaluate("""()=>{
          db.flashcards={};
          const antes=Object.keys(db.flashcards).length;
          simEnviarParaFlashcard(3);
          const depois1=Object.keys(db.flashcards).length;
          simEnviarParaFlashcard(3);
          const depois2=Object.keys(db.flashcards).length;
          return {antes,depois1,depois2};}""")
        print('   flashcards: %s → %s (1º clique) → %s (2º clique, dedup)'%(r['antes'],r['depois1'],r['depois2']))
        assert r['antes']==0 and r['depois1']==1 and r['depois2']==1
        print('   OK\n')

        print('=== F) marcar "item desatualizado" poe o item ATIVO como revisar no Banco ===')
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const item=db.acervo.find(x=>x._chaveForte===prova.chaves2[0]);
          item.status='ativa';
          simMotivoSalvar(0,'datado');
          return {status:item.status};}""")
        print('   status do item após marcar "item desatualizado": %s'%r['status'])
        assert r['status']=='revisar'
        print('   OK\n')

        print('=== G) a ponte NAO sobrescreve um status ja arquivado manualmente no Banco ===')
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const item=db.acervo.find(x=>x._chaveForte===prova.chaves2[1]);
          item.status='arquivada';
          simMotivoSalvar(1,'datado');
          return {status:item.status};}""")
        print('   status de um item já arquivado continua: %s'%r['status'])
        assert r['status']=='arquivada'
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
