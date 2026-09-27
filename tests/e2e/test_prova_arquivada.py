# -*- coding: utf-8 -*-
# "Ela fica guardada onde que eu nao vejo?" — ficava em lugar nenhum. O banco salvava as
# QUESTOES da prova que saia da lista, mas nao a prova: o agrupamento, as suas respostas
# daquele dia e o placar iam embora junto. Revisar prova por prova acabava com a prova.
# Agora fica o esqueleto (nome, data, tentativas, chaves) e a prova e remontada do banco.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) prova que sai da lista deixa o esqueleto ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',20,'A');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.nome='Simulado da segunda';
          pr.tentativas=[{data:new Date().toISOString(),
            respostas:pr.questoes.map((q,i)=>i<13?q.correta:(q.correta==='C'?'E':'C')),
            acertos:13,tempoGastoSec:3600}];
          acervoGuardarProva(pr); provaArquivar(pr);
          db.provas=[];
          const a=db.provasArquivo[0];
          return {arquivadas:db.provasArquivo.length, nome:a.nome, chaves:(a.chaves||[]).length,
                  tentativas:(a.tentativas||[]).length, acertos:a.tentativas[0].acertos,
                  tempo:a.tentativas[0].tempoGastoSec,
                  semEnunciado:JSON.stringify(a).indexOf('sobre Choque septico')<0,
                  tamEsqueleto:JSON.stringify(a).length,
                  tamInteira:JSON.stringify(pr).length};}""")
        print('   arquivada "%s": %s chaves, %s tentativa (%s acertos, %ss)'
              %(r['nome'],r['chaves'],r['tentativas'],r['acertos'],r['tempo']))
        print('   esqueleto: %s bytes · prova inteira seria: %s bytes'
              %(r['tamEsqueleto'],r['tamInteira']))
        assert r['arquivadas']==1 and r['chaves']==20 and r['acertos']==13
        assert r['semEnunciado'], 'duplicou o enunciado no arquivo'
        assert r['tamEsqueleto']<r['tamInteira']/3
        print('   o enunciado não é duplicado: ele já está no banco')
        print('   OK\n')

        print('=== B) a prova e remontada, com as SUAS respostas no lugar certo ===')
        r=await page.evaluate("""()=>{
          const a=db.provasArquivo[0];
          const pr=provaDoArquivo(a.id);
          const t=pr.tentativas[0];
          const certos=pr.questoes.filter((q,i)=>t.respostas[i]===q.correta).length;
          return {itens:pr.questoes.length, faltando:pr.faltando,
                  acertos:t.acertos, conferido:certos,
                  temEnunciado:!!pr.questoes[0].questao,
                  temComentario:!!pr.questoes[0].explicacao,
                  rotulo:provaRotulo(pr)};}""")
        print('   remontada: %s itens · %s acertos (conferido item a item: %s)'
              %(r['itens'],r['acertos'],r['conferido']))
        print('   com enunciado: %s · "%s"'%(r['temEnunciado'],r['rotulo']))
        assert r['itens']==20 and r['faltando']==0
        assert r['acertos']==13 and r['conferido']==13 and r['temEnunciado']
        print('   OK\n')

        print('=== C) abrir a revisao dela de verdade ===')
        r=await page.evaluate("""()=>{
          provaRevisarArquivada(db.provasArquivo[0].id);
          const h=document.getElementById('simgeral-content').innerHTML;
          const marcadas=simGeralActive.questoes.filter(q=>q.userAnswer).length;
          const certas=simGeralActive.questoes.filter(q=>q.userAnswer===q.correta).length;
          return {abriu:!!simGeralActive, soLeitura:!!simGeralActive.revisando,
                  arquivada:!!simGeralActive.arquivada, corrigida:!!simGeralActive.corrected,
                  marcadas,certas, semProvaId:simGeralActive.provaId===null,
                  placar:/13\\/20/.test(h), avisoLeitura:/Só leitura/.test(h)};}""")
        print('   abriu em só-leitura: %s · placar 13/20 na tela: %s'
              %(r['soLeitura'],r['placar']))
        print('   as suas 20 marcações voltaram, %s certas'%r['certas'])
        assert r['abriu'] and r['soLeitura'] and r['corrigida'] and r['arquivada']
        assert r['marcadas']==20 and r['certas']==13 and r['placar'] and r['avisoLeitura']
        assert r['semProvaId'], 'revisão de arquivada não pode escrever numa prova viva'
        print('   OK\n')

        print('=== D) item quebrado saiu do banco: some da prova E das respostas ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',6,'D');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          const pr=provaAchar(id);
          pr.questoes[2].motivo='datado';            // nunca entra no banco
          pr.tentativas=[{data:new Date().toISOString(),
            respostas:pr.questoes.map(q=>q.correta), acertos:6,tempoGastoSec:60}];
          acervoGuardarProva(pr); provaArquivar(pr);
          db.provas=[];
          const rem=provaDoArquivo(db.provasArquivo[0].id);
          const t=rem.tentativas[0];
          const alinhado=rem.questoes.every((q,i)=>t.respostas[i]===q.correta);
          return {noBanco:db.acervo.length, chaves:db.provasArquivo[0].chaves.length,
                  remontada:rem.questoes.length, faltando:rem.faltando,
                  respostas:t.respostas.length, alinhado, acertos:t.acertos};}""")
        print('   prova de 6 com 1 quebrado → banco: %s · remontada: %s (faltando %s)'
              %(r['noBanco'],r['remontada'],r['faltando']))
        print('   respostas: %s · gabarito alinhado item a item: %s'%(r['respostas'],r['alinhado']))
        assert r['chaves']==6 and r['remontada']==5 and r['faltando']==1
        assert r['respostas']==5 and r['alinhado'] and r['acertos']==5
        print('   a questão sai da prova E da lista de respostas — senão o gabarito andava uma casa')
        print('   OK\n')

        print('=== E) aparece em Minhas Provas, fechado, e abre no clique ===')
        r=await page.evaluate("""()=>{
          provarqAberto=false;
          showScreen('provas');
          const el=document.getElementById('provas-content');
          const fechado=el.innerHTML;
          const botao=el.querySelector('.sg-mais');
          botao.click();
          const aberto=document.getElementById('provas-content').innerHTML;
          return {titulo:/Provas arquivadas \\(1\\)/.test(fechado),
                  listaFechada:!/provaRevisarArquivada/.test(fechado),
                  listaAberta:/provaRevisarArquivada/.test(aberto),
                  explica:/remontada/.test(fechado)};}""")
        print('   "Provas arquivadas (1)" na tela: %s · fechado por padrão: %s'
              %(r['titulo'],r['listaFechada']))
        print('   abre no clique: %s · explica o que é: %s'%(r['listaAberta'],r['explica']))
        assert all(r.values())
        print('   OK\n')

        print('=== F) arquivar e idempotente, e o teto e alto ===')
        r=await page.evaluate("""()=>{
          const pr={id:'x1',num:9,criadaEm:new Date().toISOString(),
                    questoes:QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'F'),
                    tentativas:[]};
          const a=provaArquivar(pr), bb=provaArquivar(pr), c=provaArquivar(pr);
          return {primeira:a,segunda:bb,terceira:c,
                  total:db.provasArquivo.filter(x=>x.id==='x1').length,
                  teto:PROVARQ_MAX};}""")
        print('   arquivar 3x a mesma prova: %s/%s/%s · no arquivo: %s (teto %s)'
              %(r['primeira'],r['segunda'],r['terceira'],r['total'],r['teto']))
        assert r['primeira'] and not r['segunda'] and not r['terceira'] and r['total']==1
        assert r['teto']==5000
        print('   OK\n')

        print('=== G) o arquivo nao entra no registro principal ===')
        r=await page.evaluate("""()=>{
          const pay=payloadParaFirebase();
          return {noPayload:pay.provasArquivo, acervo:pay.acervo,
                  emMemoria:db.provasArquivo.length};}""")
        print('   %s provas no arquivo, no payload: %s'%(r['emMemoria'],r['noPayload']))
        assert r['noPayload'] is None and r['acervo'] is None and r['emMemoria']>0
        print('   mesmo tratamento do banco: nó próprio, fora do que sobe a cada saveDB')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
