# -*- coding: utf-8 -*-
# Passo 4 do plano: editar questao do banco, criar a mao, importar em lote. O risco real
# e o endereco de provasArquivo[].chaves — ele e recalculado ao vivo a partir do texto
# (montarChaveQ), entao editar enunciado/formato precisa reendercar toda referencia velha
# (bancoReenderecarArquivo), senao a prova ja arquivada perde a questao silenciosamente.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("()=>{showScreen('banco');window.confirm=()=>true;return true;}")
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');return true;}",QS)

        print('=== A) editar explicacao/fonte/tags/favorita/status nao mexe na identidade ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          acervoGuardarProva({questoes:QS('kEnf','Enfermagem','💉','sE1','Choque septico',1,'A'),tentativas:[]});
          showScreen('banco');
          const q=db.acervo[0];
          const cfAntes=q._chaveForte;
          bancoEditarAbrir(cfAntes);
          document.getElementById('banco-edit-'+cfAntes+'-explicacao').value='nova explicação';
          document.getElementById('banco-edit-'+cfAntes+'-fonte').value='Lei 8080, art 5';
          document.getElementById('banco-edit-'+cfAntes+'-tags').value='urgencia, prova-antiga';
          document.getElementById('banco-edit-'+cfAntes+'-favorita').checked=true;
          document.getElementById('banco-edit-'+cfAntes+'-status').value='revisar';
          bancoEditarSalvar(cfAntes);
          const depois=db.acervo.find(x=>x._chaveForte===cfAntes);
          return {existeMesmaChave:!!depois,
                  explicacao:depois&&depois.explicacao,
                  fonte:depois&&depois.fonte,
                  tags:depois&&depois.tags,
                  favorita:depois&&depois.favorita,
                  status:depois&&depois.status,
                  aindaEditando:bancoEditando.has(cfAntes)};}""")
        print('   chave forte preservada: %s · favorita=%s · status=%s · tags=%s'
              %(r['existeMesmaChave'],r['favorita'],r['status'],r['tags']))
        assert r['existeMesmaChave']
        assert r['explicacao']=='nova explicação' and r['fonte']=='Lei 8080, art 5'
        assert r['tags']==['urgencia','prova-antiga'] and r['favorita'] and r['status']=='revisar'
        assert not r['aindaEditando']
        print('   OK\n')

        print('=== B) editar o enunciado migra a chave e reendereca prova ja arquivada ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const questoes=QS('kEnf','Enfermagem','💉','sE1','Choque septico',1,'B');
          acervoGuardarProva({questoes,tentativas:[]});
          const provaComEla={id:'pB',num:1,criadaEm:new Date().toISOString(),formato:'certoerrado',
            questoes,
            tentativas:[{data:new Date().toISOString(),respostas:['E'],acertos:0,tempoGastoSec:5}]};
          provaArquivar(provaComEla);
          showScreen('banco');
          const arq=db.provasArquivo[0];
          const enderecoAntes=arq.chaves[0];
          const q=db.acervo.find(x=>acervoChave2De(x)===arq.chaves2[0]);
          const cfAntes=q._chaveForte;
          bancoEditarAbrir(cfAntes);
          document.getElementById('banco-edit-'+cfAntes+'-questao').value='B item 0 sobre Choque septico — texto CORRIGIDO';
          bancoEditarSalvar(cfAntes);
          const remontada=provaDoArquivo(arq.id);
          return {enderecoMudou:arq.chaves[0]!==enderecoAntes,
                  remontouAlgo:!!remontada,
                  itens:remontada?remontada.questoes.length:0,
                  textoNovo:remontada&&remontada.questoes[0].questao.includes('CORRIGIDO')};}""")
        print('   endereço mudou: %s · reachou %s item(ns), texto corrigido: %s'
              %(r['enderecoMudou'],r['itens'],r['textoNovo']))
        assert r['enderecoMudou'] and r['remontouAlgo'] and r['itens']==1 and r['textoNovo']
        print('   sem o reendereçamento, a prova arquivada teria perdido a questão (faltando++)')
        print('   OK\n')

        print('=== C) criar questao a mao entra no banco com o assunto certo ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          bancoCriarAbrir();
          document.getElementById('banco-novo-questao').value='Segundo a CF/88, a saúde é direito de todos e dever do Estado.';
          document.getElementById('banco-novo-gabarito').value='C';
          document.getElementById('banco-novo-assunto').value='sS1';
          bancoCriarSalvar();
          const q=db.acervo[0];
          return {total:db.acervo.length,
                  subId:q&&q.subId, subName:q&&q.subName,
                  kingdomName:q&&q.kingdomName, origem:q&&q.origem,
                  aindaCriando:bancoCriando};}""")
        print('   total no banco: %s · assunto: %s (%s) · origem: %s'
              %(r['total'],r['subName'],r['kingdomName'],r['origem']))
        assert r['total']==1 and r['subId']=='sS1' and r['subName']=='Lei 8080'
        assert r['kingdomName']=='Saúde Pública' and r['origem']=='manual' and not r['aindaCriando']
        print('   OK\n')

        print('=== D) criar uma "duplicata" funde em vez de duplicar ===')
        r=await page.evaluate("""()=>{
          bancoCriarAbrir();
          document.getElementById('banco-novo-questao').value='Segundo a CF/88, a saúde é direito de todos e dever do Estado.';
          document.getElementById('banco-novo-gabarito').value='C';
          document.getElementById('banco-novo-assunto').value='sS1';
          document.getElementById('banco-novo-explicacao').value='explicação nova, a antiga não tinha';
          bancoCriarSalvar();
          return {total:db.acervo.length, explicacao:db.acervo[0].explicacao};}""")
        print('   total continua: %s · ganhou a explicação que faltava: %s'%(r['total'],r['explicacao']))
        assert r['total']==1 and r['explicacao']=='explicação nova, a antiga não tinha'
        print('   OK\n')

        print('=== E) importar em lote por JSON ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const lote=[
            {questao:'Item importado 1 sobre crase',correta:'C',formato:'certoerrado'},
            {questao:'Item importado 2 sobre crase',correta:'E',formato:'certoerrado'}];
          bancoImportarAbrir();
          document.getElementById('banco-importar-assunto').value='sP1';
          document.getElementById('banco-importar-txt').value=JSON.stringify(lote);
          bancoImportarProcessar();
          return {total:db.acervo.length,
                  todasComAssunto:db.acervo.every(q=>q.subId==='sP1'),
                  origens:db.acervo.map(q=>q.origem),
                  aindaImportando:bancoImportando};}""")
        print('   %s questões importadas, todas com o assunto escolhido: %s'
              %(r['total'],r['todasComAssunto']))
        assert r['total']==2 and r['todasComAssunto']
        assert all(o=='importada' for o in r['origens']) and not r['aindaImportando']
        print('   OK\n')

        print('=== F) item quebrado no lote e descartado, o resto entra ===')
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          const lote=[
            {questao:'Item bom sobre crase',correta:'C',formato:'certoerrado'},
            {questao:'',correta:'C',formato:'certoerrado'},
            {questao:'Item sem gabarito valido',correta:'X',formato:'certoerrado'}];
          bancoImportarAbrir();
          document.getElementById('banco-importar-assunto').value='sP1';
          document.getElementById('banco-importar-txt').value=JSON.stringify(lote);
          bancoImportarProcessar();
          return {total:db.acervo.length};}""")
        print('   3 no lote, 1 bom → banco: %s'%r['total'])
        assert r['total']==1
        print('   OK\n')

        print('erros de JS: %s'%(real_errors(errs) or 'nenhum'))
        assert not real_errors(errs)
        await b.close()
        print('OK')

asyncio.run(main())
