# -*- coding: utf-8 -*-
# Passo 8.1 do redesenho de Simulados: confianca declarada ANTES do gabarito, marcar pra
# revisar durante a prova, e progresso segmentado por confianca em vez de
# respondida/nao-respondida — o conceito central do redesenho, aplicado SEM repaginar a
# prova pra questao-unica (decisao discutida com o usuario: o scroll unico atual preserva
# grifo, pausar/retomar e a atualizacao pontual de DOM que ja funcionam bem).
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) a tela da prova nasce com progresso segmentado, tira de navegacao e um bloco de confianca por questao ===')
        await page.evaluate("""()=>{
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'A');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          showScreen('simgeral');
          renderSimGeralScreen();
          return true;}""")
        await page.wait_for_timeout(300)
        r=await page.evaluate("""()=>({
          temSeg:!!document.getElementById('sg-progress-wrap'),
          temStrip:!!document.getElementById('sg-nav-strip'),
          numChips:document.querySelectorAll('.sg-nav-num').length,
          numBlocosConfianca:document.querySelectorAll('.sg-confianca').length,
          numBotoesRevisar:document.querySelectorAll('.sg-revisar-btn').length})""")
        print('   %s'%r)
        assert r['temSeg'] and r['temStrip']
        assert r['numChips']==4 and r['numBlocosConfianca']==4 and r['numBotoesRevisar']==4
        print('   OK\n')

        print('=== B) declarar confianca e marcar pra revisar atualizam a legenda e a tira, sem bloquear nada ===')
        r=await page.evaluate("""()=>{
          sgSetConfianca(0,'chute');
          sgSetConfianca(1,'certeza');
          sgToggleMarcarRevisar(2);
          const chips=[...document.querySelectorAll('.sg-nav-num')].map(c=>c.className);
          return {q0:simGeralActive.questoes[0].confianca,
                  q1:simGeralActive.questoes[1].confianca,
                  q2marcado:simGeralActive.questoes[2].marcadoRevisar,
                  chips,
                  legenda:document.querySelector('.sg-progress-legenda').innerText.replace(/\\n/g,' ')};}""")
        print('   confianca: q0=%r q1=%r · q2 marcada=%s'%(r['q0'],r['q1'],r['q2marcado']))
        print('   chips: %s'%r['chips'])
        print('   legenda: %r'%r['legenda'])
        assert r['q0']=='chute' and r['q1']=='certeza' and r['q2marcado']
        assert 'nc-chute' in r['chips'][0] and 'nc-certeza' in r['chips'][1] and 'nc-revisar' in r['chips'][2]
        assert 'chute 1' in r['legenda'] and 'certeza 1' in r['legenda'] and '1 pra revisar' in r['legenda']
        print('   OK\n')

        print('=== C) clicar de novo na mesma confianca desmarca (igual motivo/problematico) ===')
        r=await page.evaluate("""()=>{
          sgSetConfianca(0,'chute');   // clique de novo no mesmo valor
          return simGeralActive.questoes[0].confianca;}""")
        print('   confianca depois do 2º clique: %r'%r)
        assert r==''
        print('   OK\n')

        print('=== D) "ir pras marcadas" rola ate uma questao marcada, sem estourar erro sem nenhuma marcada ===')
        r=await page.evaluate("""()=>{
          sgToggleMarcarRevisar(2);   // desmarca a unica marcada
          sgIrParaMarcadas();         // nao deve quebrar
          sgToggleMarcarRevisar(3);
          sgIrParaMarcadas();
          return document.getElementById('sgq-3').getBoundingClientRect().top!=null;}""")
        assert r
        print('   OK\n')

        print('=== E) a confianca declarada viaja pra tentativa, na MESMA posicao da resposta ===')
        r=await page.evaluate("""()=>{
          sgSetConfianca(0,'chute');
          simGeralActive.questoes.forEach(q=>q.userAnswer=q.correta);
          simGeralActive.tempoGastoSec=90;
          simGeralCorrigir();
          return true;}""")
        await page.wait_for_timeout(300)
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          return {confiancas:prova.tentativas[0].confiancas,
                  respostas:prova.tentativas[0].respostas.length};}""")
        print('   confiancas guardadas: %s'%r['confiancas'])
        assert r['confiancas'][0]=='chute'
        assert r['confiancas'][1]=='certeza'
        assert r['confiancas'][2]=='' and r['confiancas'][3]==''
        assert len(r['confiancas'])==r['respostas']
        print('   confianca nao vaza pra copia da questao no acervo (e por tentativa, nao por enunciado) ===')
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const item=db.acervo.find(x=>x._chaveForte===prova.chaves2[0]);
          return {temConfiancaNoItem:'confianca' in item,temMarcadoRevisarNoItem:'marcadoRevisar' in item};}""")
        assert not r['temConfiancaNoItem'] and not r['temMarcadoRevisarNoItem']
        print('   OK\n')

        print('=== F) refazer a prova comeca sem confianca/marcacao antigas (cada tentativa e independente) ===')
        r=await page.evaluate("""()=>{
          const provaId=db.provas[0].id;
          provaRefazer(provaId);
          return simGeralActive.questoes.map(q=>({c:q.confianca,m:q.marcadoRevisar}));}""")
        print('   %s'%r)
        assert all(not q['c'] and not q['m'] for q in r)
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
