# -*- coding: utf-8 -*-
# Terceiro buraco do mesmo bug — achado por DEDUCAO, depois do backfill de miniboss (que
# corrige sub.simHistorico) ter migrado só 4 de 812 tentativas na conta real do usuário.
# A explicação: quase toda entrada geral:true de sub.simHistorico é espelho de um Simulado
# Geral cuja PROVA em si já saiu de db.provas (evictada pelo teto de PROVAS_MAX/bytes, ou
# apagada a mão) e foi pro arquivo (db.provasArquivo) — que guarda chaves2+tentativas
# intactos, mas nunca teve backfill nenhum. acervoGuardarProva roda sempre ANTES de
# qualquer arquivamento e cobre a contagem — mas só de HOJE em diante (o carimbo em
# provaArquivar é novo). Tudo que já estava arquivado antes disso não tem esse carimbo, e é
# justamente ali que mora a maior parte da vida de estudo de quem usa o app há tempo.
#
# acervoBackfillDeProvasArquivadas() varre db.provasArquivo sem _acervoBackfillEm, soma os
# contadores em ordem cronológica de t.data (mesmo mecanismo do backfill de db.provas —
# nem precisa converter formato, arquivo sempre tem chaves/chaves2 prontos).
#
# Bug de ordem corrigido de passagem: acervoCarregar chamava o backfill ANTES de
# provarqCarregar — a fonte mais gorda das três (db.provasArquivo) ainda não tinha sido
# carregada da nuvem/idb nesse ponto, então o backfill automático do boot nunca via nada
# pra migrar sozinho.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) duas provas arquivadas ANTES desta versão (sem _acervoBackfillEm), questão compartilhada ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          const qsA=QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'ArqA');
          qsA.forEach(q=>{q._chaveForte=acervoChave2(q);});
          const qsB=[{...qsA[0]},...QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',2,'ArqB')];
          qsB.forEach(q=>{if(!q._chaveForte)q._chaveForte=acervoChave2(q);});
          // simula o que acervoGuardarProva JA tinha feito antigamente: as questoes
          // entraram no banco (INSERT), mas sem nenhum contador de verdade — o campo
          // vezesRespondida so passou a existir a partir do passo 7.
          const vistos=new Set();
          [...qsA,...qsB].forEach(q=>{
            const k=q._chaveForte;
            if(vistos.has(k))return; vistos.add(k);
            db.acervo.push({...q,tags:[],favorita:false,status:'ativa',
              vezesRespondida:0,acertos:0,erros:0,ultimaVezEm:null,dificuldadeAferida:null,
              certezaAcertos:0,certezaErros:0,duvidaAcertos:0,duvidaErros:0,chuteAcertos:0,chuteErros:0,
              criacao:new Date().toISOString(),origem:'ia'});
          });
          // dois esqueletos de arquivo, SEM _acervoBackfillEm (o jeito que provaArquivar
          // sempre produziu ate esta versao)
          db.provasArquivo=[
            {id:genId(),num:2,nome:'',criadaEm:'2024-03-01T00:00:00.000Z',arquivadaEm:'2024-03-01T00:00:00.000Z',
             formato:'certoerrado',nivel:'dificil',origem:'ia',treino:false,limiteSec:0,
             chaves:qsB.map(q=>montarChaveQ(q)),chaves2:qsB.map(q=>q._chaveForte),marcacoes:{},
             tentativas:[{data:'2024-03-01T00:00:00.000Z',
               respostas:[qsB[0].correta==='C'?'E':'C',qsB[1].correta,qsB[2].correta],acertos:2,tempoGastoSec:300}]},
            {id:genId(),num:1,nome:'',criadaEm:'2024-01-01T00:00:00.000Z',arquivadaEm:'2024-02-15T00:00:00.000Z',
             formato:'certoerrado',nivel:'dificil',origem:'ia',treino:false,limiteSec:0,
             chaves:qsA.map(q=>montarChaveQ(q)),chaves2:qsA.map(q=>q._chaveForte),marcacoes:{},
             tentativas:[
               {data:'2024-01-01T00:00:00.000Z',respostas:[qsA[0].correta,qsA[1].correta,qsA[2].correta==='C'?'E':'C',qsA[3].correta],acertos:3,tempoGastoSec:600},
               {data:'2024-02-01T00:00:00.000Z',respostas:[qsA[0].correta,qsA[1].correta==='C'?'E':'C',qsA[2].correta,qsA[3].correta],acertos:3,tempoGastoSec:500}
             ]}
          ];
          return {acervoAntes:db.acervo.length,carimbadas:db.provasArquivo.filter(a=>a._acervoBackfillEm).length};}""")
        print('   %s'%r)
        assert r['acervoAntes']==6 and r['carimbadas']==0
        print('   OK\n')

        print('=== B) backfill: soma as 3 tentativas arquivadas, ultimoResultado respeita a DATA de verdade ===')
        r=await page.evaluate("""()=>{
          const rel=acervoBackfillDeProvasArquivadas();
          const arqA=db.provasArquivo.find(a=>a.num===1);
          const q0=db.acervo.find(x=>x._chaveForte===arqA.chaves2[0]);
          return {rel,
                  q0:{vezes:q0.vezesRespondida,acertos:q0.acertos,erros:q0.erros,
                      ultimoResultado:q0.ultimoResultado,ultimaVezEm:q0.ultimaVezEm},
                  carimbadas:db.provasArquivo.filter(a=>a._acervoBackfillEm).length};}""")
        print('   relatório: %s'%r['rel'])
        print('   q0 (compartilhada arqA+arqB): %s'%r['q0'])
        assert r['rel']['arquivadasMigradas']==2
        assert r['rel']['tentativasContadas']==3
        # q0: arqA acertou 2x (jan, fev) + arqB errou 1x (mar, a mais recente) = 3 vezes, 2 acertos, 1 erro
        assert r['q0']['vezes']==3 and r['q0']['acertos']==2 and r['q0']['erros']==1
        assert r['q0']['ultimoResultado']=='X'
        assert r['q0']['ultimaVezEm'].startswith('2024-03-01')
        assert r['carimbadas']==2
        print('   OK\n')

        print('=== C) idempotente: rodar de novo não soma nada outra vez ===')
        r=await page.evaluate("""()=>{
          const arqA=db.provasArquivo.find(a=>a.num===1);
          const q0=db.acervo.find(x=>x._chaveForte===arqA.chaves2[0]);
          const antes={vezes:q0.vezesRespondida,acertos:q0.acertos,erros:q0.erros};
          const rel2=acervoBackfillDeProvasArquivadas();
          const depois={vezes:q0.vezesRespondida,acertos:q0.acertos,erros:q0.erros};
          return {antes,depois,rel2};}""")
        print('   %s'%r)
        assert r['antes']==r['depois']
        assert r['rel2']==({'arquivadasMigradas':0,'tentativasContadas':0,'questoesNovas':0,'questoesColidiram':0})
        print('   OK\n')

        print('=== D) prova apagada AGORA nasce carimbada — próximo backfill não a conta de novo ===')
        r=await page.evaluate("""()=>{
          showScreen('provas');
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'Nova');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.tentativas=[{data:new Date().toISOString(),respostas:pr.questoes.map(q=>q.correta),acertos:3,tempoGastoSec:100}];
          provaApagar(id);
          const arq=db.provasArquivo.find(a=>a.id===id);
          const antesCarimbo=!!arq._acervoBackfillEm;
          const rel=acervoBackfillDeProvasArquivadas();
          return {antesCarimbo,rel,arquivadasNoAr:db.provasArquivo.filter(a=>!a._acervoBackfillEm).length};}""")
        print('   %s'%r)
        assert r['antesCarimbo'], 'provaApagar->provaArquivar tinha que carimbar na hora'
        assert r['rel']==({'arquivadasMigradas':0,'tentativasContadas':0,'questoesNovas':0,'questoesColidiram':0})
        print('   OK\n')

        print('=== E) prova arquivada nunca feita não quebra nada, só marca ===')
        r=await page.evaluate("""()=>{
          db.provasArquivo.push({id:genId(),num:9,nome:'',criadaEm:new Date().toISOString(),
            arquivadaEm:new Date().toISOString(),formato:'certoerrado',nivel:'dificil',
            origem:'ia',treino:false,limiteSec:0,chaves:[],chaves2:[],marcacoes:{},tentativas:[]});
          const rel=acervoBackfillDeProvasArquivadas();
          return {rel,todasCarimbadas:db.provasArquivo.every(a=>a._acervoBackfillEm)};}""")
        print('   %s'%r)
        assert r['rel']==({'arquivadasMigradas':0,'tentativasContadas':0,'questoesNovas':0,'questoesColidiram':0})
        assert r['todasCarimbadas']
        print('   OK\n')

        print('=== F) acervoCarregar (boot real) roda o backfill DEPOIS de carregar db.provasArquivo ===')
        r=await page.evaluate("""async()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'Boot');
          qs.forEach(q=>{q._chaveForte=acervoChave2(q);});
          qs.forEach(q=>db.acervo.push({...q,tags:[],favorita:false,status:'ativa',
            vezesRespondida:0,acertos:0,erros:0,ultimaVezEm:null,dificuldadeAferida:null,
            certezaAcertos:0,certezaErros:0,duvidaAcertos:0,duvidaErros:0,chuteAcertos:0,chuteErros:0,
            criacao:new Date().toISOString(),origem:'ia'}));
          db.provasArquivo=[{id:genId(),num:1,nome:'',criadaEm:'2024-05-01T00:00:00.000Z',
            arquivadaEm:'2024-05-01T00:00:00.000Z',formato:'certoerrado',nivel:'dificil',
            origem:'ia',treino:false,limiteSec:0,chaves:qs.map(q=>montarChaveQ(q)),
            chaves2:qs.map(q=>q._chaveForte),marcacoes:{},
            tentativas:[{data:'2024-05-01T00:00:00.000Z',respostas:qs.map(q=>q.correta),acertos:3,tempoGastoSec:100}]}];
          acervoSalvar(true);
          provarqSalvar(true);
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          await acervoCarregar();
          const arqDeVolta=db.provasArquivo.length>0;
          const contado=db.acervo.filter(x=>x.questao&&x.questao.includes('Boot')&&x.vezesRespondida>0).length;
          return {arqDeVolta,contado};}""")
        print('   %s'%r)
        assert r['arqDeVolta'], 'provarqCarregar tinha que trazer o arquivo de volta antes do backfill rodar'
        assert r['contado']==3, 'acervoCarregar tinha que contar as 3 questoes do arquivo sozinho, no boot'
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
