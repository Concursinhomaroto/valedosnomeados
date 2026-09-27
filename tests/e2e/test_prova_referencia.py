# -*- coding: utf-8 -*-
# Passo 6 do plano: prova guardada (ja com pelo menos 1 tentativa) passa a referenciar o
# acervo por chave, em vez de carregar copia inteira das questoes dentro de db.provas —
# o mesmo modelo que db.provasArquivo ja usa desde o passo 1. Decisao confirmada com o
# usuario: corrigir uma questao no Acervo passa a valer retroativamente pra prova VIVA
# que ja a contem tambem (ate hoje isso so acontecia pro arquivo).
#
# "Prova esperando nao e historico" continua valendo: a conversao so acontece na 1a
# tentativa, nunca na criacao — regra ja testada em test_prova_esperando.py, aqui so
# confirmamos que ela sobrevive.
import asyncio, sys, json
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) esperando fica em copia cheia; 1a tentativa converte pra referencia ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const id=provaGuardarLote(QS('kEnf','Enfermagem','💉','sE1','Choque septico',6,'A'),
                                    {formato:'certoerrado'});
          const antes={temQuestoes:!!provaAchar(id).questoes,temChaves:!!provaAchar(id).chaves,
                       noAcervo:db.acervo.length};
          const prova=provaAchar(id);
          prova.tentativas=[{data:new Date().toISOString(),
            respostas:['C','C','C','C','C','C'],acertos:6,tempoGastoSec:60}];
          // simula o gatilho que provaGuardar chamaria na 1a tentativa de verdade
          provaConverterParaReferencia(prova);
          const depois={temQuestoes:!!provaAchar(id).questoes,temChaves:!!provaAchar(id).chaves,
                        chaves2Len:(provaAchar(id).chaves2||[]).length,
                        noAcervo:db.acervo.length,
                        textoIgual:provaQuestoes(prova)[0].questao.startsWith('A ')};
          return {antes,depois};}""")
        print('   esperando: copia cheia=%s, referencia=%s'%(r['antes']['temQuestoes'],r['antes']['temChaves']))
        print('   depois da 1a tentativa: copia cheia=%s, referencia=%s (banco: %s → %s)'
              %(r['depois']['temQuestoes'],r['depois']['temChaves'],r['antes']['noAcervo'],r['depois']['noAcervo']))
        assert r['antes']['temQuestoes'] and not r['antes']['temChaves'] and r['antes']['noAcervo']==0
        assert not r['depois']['temQuestoes'] and r['depois']['temChaves']
        assert r['depois']['chaves2Len']==6 and r['depois']['noAcervo']==6
        assert r['depois']['textoIgual']
        print('   OK\n')

        print('=== B) corrigir o enunciado no Acervo muda o que a prova VIVA mostra ===')
        r=await page.evaluate("""()=>{
          const prova0=db.provas[0];
          const q=db.acervo.find(x=>x._chaveForte===prova0.chaves2[0]);
          const cfAntes=q._chaveForte;
          const dados={...q,questao:'A item 0 sobre Choque septico — TEXTO CORRIGIDO'};
          const mudou=bancoAplicarEdicao(q,dados);
          const prova=db.provas[0];
          const hidratada=provaQuestoes(prova)[0];
          return {mudou,cfMudou:q._chaveForte!==cfAntes,
                  textoNaProva:hidratada.questao,
                  chaves2Bate:prova.chaves2[0]===q._chaveForte};}""")
        print('   endereço/identidade mudou: %s'%r['cfMudou'])
        print('   a prova viva já mostra: %r'%r['textoNaProva'])
        assert r['mudou'] and r['cfMudou']
        assert 'TEXTO CORRIGIDO' in r['textoNaProva']
        assert r['chaves2Bate']
        print('   igual ao que já acontecia com o arquivo — decisão confirmada com o usuário')
        print('   OK\n')

        print('=== C) corrigir o GABARITO recalcula o placar da tentativa ja guardada ===')
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          const antes=provaPlacar(prova,prova.tentativas[0]);
          const q=db.acervo.find(x=>x._chaveForte===prova.chaves2[0]);   // índice 0, respondida 'C'
          const respondida=prova.tentativas[0].respostas[0];
          const acertavaAntes=q.correta===respondida;
          const dados={...q,correta:respondida};   // banca corrigiu: agora bate com o que foi marcado
          bancoAplicarEdicao(q,dados);
          const depois=provaPlacar(prova,prova.tentativas[0]);
          return {antesAcertos:antes.acertos,depoisAcertos:depois.acertos,acertavaAntes};}""")
        print('   acertava antes da correção: %s · acertos antes: %s · depois: %s'
              %(r['acertavaAntes'],r['antesAcertos'],r['depoisAcertos']))
        esperado=r['antesAcertos']+(0 if r['acertavaAntes'] else 1)
        assert r['depoisAcertos']==esperado
        print('   a banca corrigiu o gabarito, e o placar da prova viva recalcula sozinho')
        print('   OK\n')

        print('=== D) o payload que sobe pro Firebase encolhe MUITO depois de convertida ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',30,
            'Enunciado bem mais longo pra simular uma questao Cebraspe de verdade, com bastante texto de contexto e justificativa detalhada dentro da explicacao tambem, porque e assim que as questoes de concurso realmente sao');
          const id=provaGuardarLote(questoes,{formato:'certoerrado'});
          const bytesCheia=JSON.stringify(db.provas).length;
          const prova=provaAchar(id);
          prova.tentativas=[{data:new Date().toISOString(),
            respostas:questoes.map(q=>q.correta),acertos:30,tempoGastoSec:200}];
          provaConverterParaReferencia(prova);
          const bytesReferencia=JSON.stringify(db.provas).length;
          return {bytesCheia,bytesReferencia,
                  intacta:provaQuestoes(prova).every(q=>!q._faltando)};}""")
        reducao=100*(1-r['bytesReferencia']/r['bytesCheia'])
        print('   30 questões: %s bytes em copia cheia → %s bytes em referência (%.0f%% menor)'
              %(r['bytesCheia'],r['bytesReferencia'],reducao))
        assert r['bytesReferencia']<r['bytesCheia']*0.5, 'esperava reducao grande, o ponto inteiro do passo 6'
        assert r['intacta']
        print('   OK\n')

        print('=== E) prova que sai pelo teto (ja convertida) arquiva sem redigitar nada ===')
        r=await page.evaluate("""()=>{
          const antesArq=(db.provasArquivo||[]).length;
          const prova=db.provas[0];
          const chaves2Antes=prova.chaves2.slice();
          provaArquivar(prova);
          const arq=db.provasArquivo.find(a=>a.id===prova.id);
          return {arquivou:!!arq,
                  mesmasChaves2:JSON.stringify(arq.chaves2)===JSON.stringify(chaves2Antes),
                  remontou:provaDoArquivo(prova.id).questoes.length};}""")
        print('   arquivou: %s · manteve as mesmas chaves2 (não recalculou): %s · remontou %s itens'
              %(r['arquivou'],r['mesmasChaves2'],r['remontou']))
        assert r['arquivou'] and r['mesmasChaves2'] and r['remontou']==30
        print('   OK\n')

        print('=== F) grifo feito na 1a prova (antes de existir) sobrevive a conversao ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const questoes=QS('kPt','Português','📖','sP1','Crase',4,'F');
          simGeralActive={questoes:questoes.map(q=>({...q})),startedAt:Date.now(),limiteSec:0,
                          corrected:false,formato:'certoerrado',nivel:'dificil'};
          // grifo feito ANTES de existir prova.provaId (marcaAlvo 'a:0' sem prova ainda)
          marcaAlvo('a:0').set([{t:questoes[0].questao.slice(0,6),n:0,c:'v'}]);
          simGeralActive.questoes.forEach(q=>q.userAnswer=q.correta);
          simGeralActive.tempoGastoSec=60;
          simGeralCorrigir();
          return true;}""")
        await page.wait_for_timeout(400)
        r=await page.evaluate("""()=>{
          const prova=db.provas[0];
          return {temChaves:!!prova.chaves,
                  grifoNaProva:(provaQuestoes(prova)[0].marcas||[]).length};}""")
        print('   convertida: %s · grifo sobreviveu à conversão: %s'%(r['temChaves'],r['grifoNaProva']))
        assert r['temChaves'] and r['grifoNaProva']==1
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
