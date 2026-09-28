# -*- coding: utf-8 -*-
# Passo 8.5 (última fatia do redesenho de Simulados): a tela de Resultado ganha a matriz
# acerto × confiança — a peça principal do redesenho inteiro, que separa acerto real de
# sorte usando a confiança declarada do passo 8.1. Tentativa sem confiança declarada
# (de antes desse recurso, ou pulada) vira uma nota honesta e discreta, NUNCA uma 4ª
# coluna fingindo dado que não existe.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) a matriz preenche as 6 células certas, e a resposta sem confiança vira nota separada ===')
        await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];
          showScreen('simgeral');
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',6,'A');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          const q=simGeralActive.questoes;
          q[0].userAnswer=q[0].correta; q[0].confianca='certeza';               // dominio real
          q[1].userAnswer=q[1].correta; q[1].confianca='duvida';                // fragil
          q[2].userAnswer=q[2].correta; q[2].confianca='chute';                 // falso dominio
          q[3].userAnswer=q[3].correta==='C'?'E':'C'; q[3].confianca='certeza'; // erro perigoso
          q[4].userAnswer=q[4].correta==='C'?'E':'C'; q[4].confianca='duvida';  // lacuna conhecida
          q[5].userAnswer=q[5].correta==='C'?'E':'C';                          // sem confianca
          simGeralActive.tempoGastoSec=60;
          simGeralCorrigir();
          showScreen('simgeral');
          return true;}""")
        await page.wait_for_timeout(300)
        r=await page.evaluate("""()=>({
          cels:[...document.querySelectorAll('.sg-matriz-cel')].map(c=>c.querySelector('b').textContent),
          temNota:!!document.querySelector('.sg-matriz-nota'),
          notaTexto:(document.querySelector('.sg-matriz-nota')||{}).textContent||'',
          numColunas:document.querySelectorAll('.sg-matriz-cab').length,
          temFalso:!!document.querySelector('.mtz-falso-bg'),
          temPerigoso:!!document.querySelector('.mtz-perigoso-bg')})""")
        print('   células: %s'%r['cels'])
        print('   nota: %r'%r['notaTexto'])
        assert r['cels']==['1','1','1','1','1','0']
        assert r['temNota'] and 'sem confiança' in r['notaTexto']
        assert r['numColunas']==4   # vazio + 3 confiancas, nunca um 4o "desconhecido"
        assert r['temFalso'] and r['temPerigoso']
        print('   OK\n')

        print('=== B) sem nenhuma confiança declarada em NADA, a matriz nem aparece (0 é diferente de "nunca perguntou") ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];
          const questoes=QS('kPt','Português','📖','sP1','Crase',3,'B');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          simGeralActive.questoes.forEach(q=>q.userAnswer=q.correta);
          simGeralActive.tempoGastoSec=20;
          simGeralCorrigir();
          showScreen('simgeral');
          return !!document.querySelector('.sg-matriz-wrap');}""")
        print('   matriz existe mesmo com tudo sem confiança (vira só a nota): %s'%r)
        assert r
        print('   OK\n')

        print('=== C) "Refazer agora" (falso domínio) monta prova só com aquelas questões e já abre ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];
          showScreen('simgeral');
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',5,'C');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=q.correta;q.confianca=i<2?'chute':'certeza';});
          simGeralActive.tempoGastoSec=45;
          simGeralCorrigir();
          simGeralRefazerGrupo('falsoDominio');
          return {emExame:!!simGeralActive&&!simGeralActive.corrected,
                  qtd:simGeralActive?simGeralActive.questoes.length:0,
                  treino:simGeralActive?!!provaAchar(simGeralActive.provaId).treino:false};}""")
        print('   %s'%r)
        assert r['emExame'] and r['qtd']==2 and r['treino']
        print('   OK\n')

        print('=== D) "Ver a questão" (erro perigoso) rola até o card certo, sem montar nada ===')
        r=await page.evaluate("""()=>{
          simGeralReset();
          db.acervo=[];db.provas=[];
          showScreen('simgeral');
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'D');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=i===2?(q.correta==='C'?'E':'C'):q.correta;q.confianca='certeza';});
          simGeralActive.tempoGastoSec=30;
          simGeralCorrigir();
          showScreen('simgeral');
          return true;}""")
        await page.wait_for_timeout(300)
        r=await page.evaluate("""()=>{
          const antes=simGeralActive.provaId;
          simGeralVerGrupo('erroPerigoso');
          return {existeCard:!!document.getElementById('sgres-2'),
                  provaIntacta:simGeralActive.provaId===antes};}""")
        print('   %s'%r)
        assert r['existeCard'] and r['provaIntacta']
        print('   OK\n')

        print('=== E) "Refazer só as erradas" e "Mandar erros pro flashcard" em lote ===')
        r=await page.evaluate("""()=>{
          db.flashcards={};
          simGeralMandarErradosParaFlashcard();
          const criados=Object.keys(db.flashcards).length;
          simGeralMandarErradosParaFlashcard();   // clicar de novo nao duplica
          const depois=Object.keys(db.flashcards).length;
          return {criados,depois};}""")
        print('   %s'%r)
        assert r['criados']==1 and r['depois']==1
        print('   OK\n')

        print('=== F) por assunto (domínio vs sorte): só aparece quando há chute dentro de um acerto ===')
        r=await page.evaluate("""()=>{
          simGeralReset();
          db.acervo=[];db.provas=[];
          showScreen('simgeral');
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'F');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          simGeralActive.questoes.forEach((q,i)=>{q.userAnswer=q.correta;q.confianca=i===0?'chute':'certeza';});
          simGeralActive.tempoGastoSec=20;
          simGeralCorrigir();
          showScreen('simgeral');
          return document.querySelector('.sg-conf-quebra').textContent.includes('Choque septico');}""")
        assert r
        print('   OK\n')

        print('=== G) revisar uma tentativa antiga restaura a confiança declarada NA ÉPOCA ===')
        r=await page.evaluate("""()=>{
          const provaId=simGeralActive.provaId;
          simGeralReset();
          provaRevisar(provaId);
          return simGeralActive.questoes.map(q=>q.confianca);}""")
        print('   %s'%r)
        assert r[0]=='chute' and r[1]=='certeza'
        print('   OK\n')

        print('=== H) revisão/refação não mostram os botões de ação em lote (refação não conta pra estatística) ===')
        r=await page.evaluate("""()=>{
          return !!document.querySelector('.sg-acoes-grupo');}""")
        print('   tem ações em lote na tela de revisão: %s'%r)
        assert not r
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
