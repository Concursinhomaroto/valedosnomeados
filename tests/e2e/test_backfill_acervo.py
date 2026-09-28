# -*- coding: utf-8 -*-
# Bug achado pelo usuário depois do passo 8 ir ao ar: db.acervo vazio apesar de db.provas
# ter provas cheias de questão já respondida. Causa raiz: o passo 6 fez prova virar
# referência por chave, mas o único gatilho de conversão pra quem JÁ tinha prova com
# tentativa era guardar uma prova NOVA — e mesmo esse gatilho (a varredura preguiçosa de
# provasAparar) só trocava o formato, sem somar os contadores das tentativas antigas.
#
# acervoBackfillDeProvasAntigas() varre db.provas, converte quem falta e soma TODAS as
# tentativas de cada questão (não só a última) — em ordem CRONOLÓGICA de verdade entre
# provas diferentes, pra ultimoResultado/ultimaVezEm não dependerem da ordem de db.provas.
# Roda sozinha no boot (acervoCarregar) e também dentro de provasAparar; idempotente por
# prova (_acervoBackfillEm), nunca apaga nada de db.provas.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) duas provas legadas (nunca convertidas), uma com 2 tentativas, questão compartilhada entre as duas ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          const qsA=QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'LegA');
          const provaA={id:genId(),num:1,nome:'',criadaEm:new Date().toISOString(),
            formato:'certoerrado',nivel:'dificil',limiteSec:0,origem:'ia',
            questoes:qsA,
            tentativas:[
              {data:'2024-01-01T00:00:00.000Z',respostas:[qsA[0].correta,qsA[1].correta,qsA[2].correta==='C'?'E':'C',qsA[3].correta],acertos:3,tempoGastoSec:600},
              {data:'2024-02-01T00:00:00.000Z',respostas:[qsA[0].correta,qsA[1].correta==='C'?'E':'C',qsA[2].correta,qsA[3].correta],acertos:3,tempoGastoSec:500}
            ]};
          const qsB=[{...qsA[0]},...QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',2,'LegB')];
          const provaB={id:genId(),num:2,nome:'',criadaEm:new Date().toISOString(),
            formato:'certoerrado',nivel:'dificil',limiteSec:0,origem:'ia',
            questoes:qsB,
            tentativas:[{data:'2024-03-01T00:00:00.000Z',
              respostas:[qsB[0].correta==='C'?'E':'C',qsB[1].correta,qsB[2].correta],acertos:2,tempoGastoSec:300}]};
          db.provas=[provaB,provaA];   // mais nova primeiro, como o app sempre guarda
          return {acervoAntes:db.acervo.length,convertidas:!!provaA.chaves||!!provaB.chaves};}""")
        print('   %s'%r)
        assert r['acervoAntes']==0 and not r['convertidas']
        print('   OK\n')

        print('=== B) backfill: converte as duas, soma as 3 tentativas, ultimoResultado respeita a DATA de verdade ===')
        r=await page.evaluate("""()=>{
          const rel=acervoBackfillDeProvasAntigas();
          const provaA=db.provas.find(p=>p.num===1), provaB=db.provas.find(p=>p.num===2);
          const q0=db.acervo.find(x=>x._chaveForte===provaA.chaves2[0]);
          return {rel,
                  provaAConvertida:!!provaA.chaves,provaBConvertida:!!provaB.chaves,
                  q0:{vezes:q0.vezesRespondida,acertos:q0.acertos,erros:q0.erros,ultimoResultado:q0.ultimoResultado},
                  tentativasIntactas:provaA.tentativas.length===2&&provaB.tentativas.length===1,
                  provasNaoApagadas:db.provas.length===2};}""")
        print('   relatório: %s'%r['rel'])
        print('   q0 (compartilhada A+B): %s'%r['q0'])
        assert r['provaAConvertida'] and r['provaBConvertida']
        # q0: provaA acertou 2x (jan, fev) + provaB errou 1x (mar, a mais recente) = 3 vezes, 2 acertos, 1 erro
        assert r['q0']['vezes']==3 and r['q0']['acertos']==2 and r['q0']['erros']==1
        assert r['q0']['ultimoResultado']=='X'   # a tentativa mais RECENTE por DATA foi a de marco (provaB), que errou
        assert r['tentativasIntactas'] and r['provasNaoApagadas']
        assert r['rel']['provasMigradas']==2
        assert r['rel']['tentativasContadas']==3
        assert r['rel']['questoesNovas']==6 and r['rel']['questoesColidiram']==1
        print('   OK\n')

        print('=== C) idempotente: rodar de novo não soma nada outra vez ===')
        r=await page.evaluate("""()=>{
          const provaA=db.provas.find(p=>p.num===1);
          const q0=db.acervo.find(x=>x._chaveForte===provaA.chaves2[0]);
          const antes={vezes:q0.vezesRespondida,acertos:q0.acertos,erros:q0.erros};
          const rel2=acervoBackfillDeProvasAntigas();
          const depois={vezes:q0.vezesRespondida,acertos:q0.acertos,erros:q0.erros};
          return {antes,depois,rel2};}""")
        print('   %s'%r)
        assert r['antes']==r['depois']
        assert r['rel2']==({'provasMigradas':0,'tentativasContadas':0,'questoesNovas':0,'questoesColidiram':0})
        print('   OK\n')

        print('=== D) confiança fica ausente nas tentativas antigas — nenhum bucket cruzado é inventado ===')
        r=await page.evaluate("""()=>{
          const provaA=db.provas.find(p=>p.num===1);
          const q0=db.acervo.find(x=>x._chaveForte===provaA.chaves2[0]);
          return{certeza:q0.certezaAcertos,duvida:q0.duvidaAcertos,chute:q0.chuteAcertos};}""")
        print('   %s'%r)
        assert not r['certeza'] and not r['duvida'] and not r['chute']
        print('   OK\n')

        print('=== E) acervoCarregar (o caminho real do boot) dispara o backfill sozinho, e avisa só quando há algo pra avisar ===')
        # db.acervo=[] só limpa a variável em memória — acervoCarregar funde de volta o que
        # já foi salvo (idb/nuvem mockados) nos cenários anteriores, do jeito certo. Por
        # isso a checagem é "as 3 questões do Boot entraram", não um total exato.
        r=await page.evaluate("""async()=>{
          db.acervo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'Boot');
          db.provas=[{id:genId(),num:3,nome:'',criadaEm:new Date().toISOString(),
            formato:'certoerrado',nivel:'dificil',limiteSec:0,origem:'ia',questoes:qs,
            tentativas:[{data:new Date().toISOString(),respostas:qs.map(q=>q.correta),acertos:3,tempoGastoSec:100}]}];
          await acervoCarregar();
          const t1=document.getElementById('toast');
          const boostrapadas=db.acervo.filter(x=>x.questao.includes('Boot')).length;
          const primeiraVez={boostrapadas,toast:t1.style.display!=='none'?t1.textContent:null};
          t1.style.display='none';
          await acervoCarregar();
          const t2=document.getElementById('toast');
          return {primeiraVez,segundaVezToastou:t2.style.display!=='none'};}""")
        print('   %s'%r)
        assert r['primeiraVez']['boostrapadas']==3
        assert r['primeiraVez']['toast'] and 'recuperada' in r['primeiraVez']['toast']
        assert not r['segundaVezToastou']
        print('   OK\n')

        print('=== F) prova nova finalizada AGORA entra no acervo na hora — não é o mesmo bug, é só retroativo ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          showScreen('simgeral');
          const questoes=QS('kPt','Português','📖','sP1','Crase',3,'Nova');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          simGeralActive.questoes.forEach(q=>q.userAnswer=q.correta);
          simGeralActive.tempoGastoSec=30;
          simGeralCorrigir();
          return db.acervo.length;}""")
        print('   acervo imediatamente após finalizar (sem backfill nenhum rodar): %s'%r)
        assert r==3
        print('   OK\n')

        print('=== G) refazer uma prova legada corrige o gatilho de conversão que checava !tentativas.length ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'Refaz');
          const prova={id:genId(),num:1,nome:'',criadaEm:new Date().toISOString(),
            formato:'certoerrado',nivel:'dificil',limiteSec:0,origem:'montada',treino:true,
            questoes:qs,
            tentativas:[{data:'2024-01-01T00:00:00.000Z',respostas:qs.map(q=>q.correta),acertos:3,tempoGastoSec:200}]};
          db.provas=[prova];
          provaRefazer(prova.id);
          simGeralActive.questoes.forEach(q=>q.userAnswer=q.correta);
          simGeralActive.tempoGastoSec=50;
          provaCorrigirRefacao();
          return {convertida:!!prova.chaves,tentativas:prova.tentativas.length,acervoTemAlgo:db.acervo.length>0};}""")
        print('   %s'%r)
        assert r['convertida'] and r['tentativas']==2 and r['acervoTemAlgo']
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
