# -*- coding: utf-8 -*-
# Passo 8.2 do redesenho de Simulados: os contadores ao vivo do passo 7
# (acervoAtualizarContadores/provaRegistrarTentativaNoAcervo) ganham buckets cruzados
# acerto x confianca declarada (certeza/duvida/chute) — e o dado que alimenta a matriz da
# tela de resultado e o deck "Acertei chutando" da tela de entrada. So preenche quando a
# confianca foi de fato declarada: tentativa sem isso (de antes do passo 8.1 existir) nao
# pode fingir um bucket que nunca teve.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) confianca declarada vira bucket ao vivo, na correcao, sem eviction nenhuma ===')
        await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'A');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          const q=simGeralActive.questoes;
          // 0: chute+acerto · 1: chute+erro · 2: duvida+acerto · 3: certeza+erro
          q[0].userAnswer=q[0].correta; q[0].confianca='chute';
          q[1].userAnswer=q[1].correta==='C'?'E':'C'; q[1].confianca='chute';
          q[2].userAnswer=q[2].correta; q[2].confianca='duvida';
          q[3].userAnswer=q[3].correta==='C'?'E':'C'; q[3].confianca='certeza';
          simGeralActive.tempoGastoSec=60;
          simGeralCorrigir();
          return true;}""")
        await page.wait_for_timeout(400)
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const itens=prova.chaves2.map(k=>db.acervo.find(x=>x._chaveForte===k));
          return itens.map(it=>({chuteAcertos:it.chuteAcertos,chuteErros:it.chuteErros,
                                  duvidaAcertos:it.duvidaAcertos,duvidaErros:it.duvidaErros,
                                  certezaAcertos:it.certezaAcertos,certezaErros:it.certezaErros}));}""")
        print('   buckets por questão: %s'%r)
        assert r[0]['chuteAcertos']==1 and r[0]['chuteErros']==0
        assert r[1]['chuteAcertos']==0 and r[1]['chuteErros']==1
        assert r[2]['duvidaAcertos']==1 and r[2]['duvidaErros']==0
        assert r[3]['certezaAcertos']==0 and r[3]['certezaErros']==1
        # nenhum bucket cruzado de sobra pra quem nao usou aquela confianca
        assert r[0]['duvidaAcertos']==0 and r[0]['certezaAcertos']==0
        print('   OK\n')

        print('=== B) sem confianca declarada, nenhum bucket cruzado e populado (so os contadores gerais) ===')
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const item=db.acervo.find(x=>x._chaveForte===prova.chaves2[0]);
          return {vezesRespondida:item.vezesRespondida,acertos:item.acertos,
                  somaBuckets:(item.chuteAcertos||0)+(item.chuteErros||0)+(item.duvidaAcertos||0)+
                              (item.duvidaErros||0)+(item.certezaAcertos||0)+(item.certezaErros||0)};}""")
        print('   item 0 (só teve chute declarado): %s'%r)
        assert r['somaBuckets']==1   # so o 1 chute da questao 0, nada mais
        print('   OK\n')

        print('=== C) 2a tentativa SOMA no bucket, nao substitui ===')
        r=await page.evaluate("""()=>{
          const provaId=db.provas[0].id;
          provaRefazer(provaId);
          simGeralActive.questoes[0].userAnswer=simGeralActive.questoes[0].correta;
          simGeralActive.questoes[0].confianca='chute';   // acertou de novo, no chute de novo
          simGeralActive.questoes.slice(1).forEach(q=>q.userAnswer=q.correta);   // sem confianca
          simGeralActive.tempoGastoSec=30;
          simGeralCorrigir();
          return true;}""")
        await page.wait_for_timeout(400)
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const item=db.acervo.find(x=>x._chaveForte===prova.chaves2[0]);
          return {chuteAcertos:item.chuteAcertos,vezesRespondida:item.vezesRespondida};}""")
        print('   depois da 2ª tentativa: %s'%r)
        assert r['chuteAcertos']==2 and r['vezesRespondida']==2
        print('   OK\n')

        print('=== D) prova no formato ANTIGO (nunca convertida) tambem popula os buckets, na eviction ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const questoes=QS('kPt','Português','📖','sP1','Crase',2,'D');
          const prova={id:genId(),num:1,nome:'',criadaEm:new Date().toISOString(),
            formato:'certoerrado',nivel:'dificil',limiteSec:0,origem:'ia',
            questoes,   // formato antigo: copia cheia, sem .chaves
            tentativas:[{data:new Date().toISOString(),
              respostas:[questoes[0].correta, questoes[1].correta==='C'?'E':'C'],
              confiancas:['certeza','duvida'],
              acertos:1,tempoGastoSec:60}]};
          const novas=acervoGuardarProva(prova);
          const itens=questoes.map(q=>db.acervo.find(x=>x.questao===q.questao));
          return {novas,
                  q0:{certezaAcertos:itens[0].certezaAcertos,vezesRespondida:itens[0].vezesRespondida},
                  q1:{duvidaErros:itens[1].duvidaErros,vezesRespondida:itens[1].vezesRespondida}};}""")
        print('   %s'%r)
        assert r['novas']==2
        assert r['q0']['certezaAcertos']==1 and r['q0']['vezesRespondida']==1
        assert r['q1']['duvidaErros']==1 and r['q1']['vezesRespondida']==1
        print('   OK\n')

        print('=== E) prova JA CONVERTIDA nao duplica os buckets na eviction (mesmo guard do passo 7) ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',2,'E');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          simGeralActive.questoes[0].userAnswer=simGeralActive.questoes[0].correta;
          simGeralActive.questoes[0].confianca='chute';
          simGeralActive.questoes[1].userAnswer=simGeralActive.questoes[1].correta;
          simGeralActive.tempoGastoSec=20;
          simGeralCorrigir();
          return true;}""")
        await page.wait_for_timeout(400)
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const antes=db.acervo.find(x=>x._chaveForte===prova.chaves2[0]).chuteAcertos;
          acervoGuardarProva(prova);   // simula uma eviction manual
          const depois=db.acervo.find(x=>x._chaveForte===prova.chaves2[0]).chuteAcertos;
          return {antes,depois};}""")
        print('   chuteAcertos antes/depois da eviction: %s / %s'%(r['antes'],r['depois']))
        assert r['antes']==r['depois']==1
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
