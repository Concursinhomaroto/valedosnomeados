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

        print('=== G) escolher o chefão estreita o select de assunto — achado ao vivo ===')
        # "aqui pra importar eu preciso escolher o chefão" — com varios assuntos por
        # materia, o select unico virava uma lista longa demais pra achar o certo.
        r=await page.evaluate("""()=>{
          bancoImportarAbrir();
          const chefaoSel=document.getElementById('banco-importar-assunto-chefao');
          const assuntoSel=document.getElementById('banco-importar-assunto');
          const antes=[...assuntoSel.options].filter(o=>o.value).map(o=>o.value).sort();
          const opt=[...chefaoSel.options].find(o=>o.textContent.includes('Urgencia'));
          chefaoSel.value=opt.value;
          chefaoSel.dispatchEvent(new Event('change'));
          const depois=[...assuntoSel.options].filter(o=>o.value).map(o=>o.value).sort();
          return {antes,depois};}""")
        print('   %s'%r)
        assert r['antes']==['sE1','sE2','sP1','sS1'], 'sem filtro, todos os assuntos de todas as materias'
        assert r['depois']==['sE1','sE2'], 'com o chefao "Urgencia", so os assuntos dele'
        print('   OK\n')

        print('=== H) lote com VARIOS assuntos, sem escolher nenhum — acha cada um pelo nome ===')
        # "eu preciso enviar o json com todos os assuntos do chefão, sem precisar escolher
        # um, e ele direcionar para o assunto" — cada item do JSON ja traz o proprio
        # "assunto"/"assuntoNome" (mesmo formato usado em Colar prova).
        r=await page.evaluate("""()=>{
          db.provas=[];db.provasArquivo=[];db.acervo=[];
          bancoImportarAbrir();
          // Assunto fica em branco de proposito — "Escolha o assunto..."
          const lote=[
            {assunto:1,assuntoNome:'Choque septico',afirmacao:'Item sobre choque.',gabarito:'C',explicacao:'x'},
            {assunto:2,assuntoNome:'Lei 8080',afirmacao:'Item sobre a lei.',gabarito:'E',explicacao:'x'},
            {assunto:3,assuntoNome:'Crase',afirmacao:'Item sobre crase.',gabarito:'C',explicacao:'x'},
            {assunto:9,assuntoNome:'Assunto que nao existe em lugar nenhum',afirmacao:'Nao deveria casar.',gabarito:'E'}
          ];
          document.getElementById('banco-importar-txt').value=JSON.stringify(lote);
          bancoImportarProcessar();
          return {total:db.acervo.length,
                  subs:db.acervo.map(q=>q.subId).sort(),
                  pendentes:bancoImportarPendentes.map(p=>({nome:p.nome,n:p.itens.length}))};}""")
        print('   %s'%r)
        assert r['total']==3 and r['subs']==['sE1','sP1','sS1'], 'os 3 reconheciveis entram, o inventado nao (ainda)'
        assert r['pendentes']==[{'nome':'Assunto que nao existe em lugar nenhum','n':1}], 'quem nao bateu vira pendencia, nao some calado'
        print('   OK\n')

        print('=== I) pendência resolvida manualmente entra no banco e vira apelido pra próxima vez ===')
        # "tem questões que não estão linkando... ele não levou todos" — antes o item sem
        # correspondência era descartado sem aviso; agora fica pendente ate o usuario
        # escolher o assunto certo (ou descartar), e a escolha vira apelido lembrado.
        r=await page.evaluate("""()=>{
          const sel=document.getElementById('banco-importar-pend-0');
          sel.value='sE2';   // PCR
          bancoImportarPendenteEscolher(0,'banco-importar-pend-0');
          return {total:db.acervo.length,
                  pendentesRestantes:bancoImportarPendentes.length,
                  novoItem:db.acervo.find(q=>q.subId==='sE2')};}""")
        print('   %s'%r)
        assert r['total']==4 and r['pendentesRestantes']==0
        assert r['novoItem'] and r['novoItem']['subId']=='sE2'
        print('   OK\n')

        r=await page.evaluate("""()=>{
          bancoImportarAbrir();
          document.getElementById('banco-importar-txt').value=JSON.stringify(
            [{assuntoNome:'Assunto que nao existe em lugar nenhum',afirmacao:'Outro item do mesmo nome.',gabarito:'C',explicacao:'x'}]);
          bancoImportarProcessar();
          return {total:db.acervo.length,pendentes:bancoImportarPendentes.length};}""")
        print('   reimportando o mesmo nome (deve usar o apelido): %s'%r)
        assert r['total']==5 and r['pendentes']==0, 'nome ja resolvido uma vez tem que casar sozinho da proxima'
        print('   OK\n')

        print('=== J) "Mover assunto" corrige em massa um lote que caiu no assunto errado ===')
        # "coloquei os assuntos de legislação e ele não levou todos" — quando um lote
        # acaba no assunto errado (ex.: casamento por nome pegou um parecido por
        # engano), a correção não pode exigir editar questão por questão.
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          QS('kEnf','Enfermagem','💉','sE1','Choque septico',4,'X').forEach(q=>{
            db.acervo.push({...q,_chaveForte:acervoChave2(q),tags:[],favorita:false,status:'ativa',
              vezesRespondida:0,acertos:0,criacao:new Date().toISOString(),origem:'ia'});
          });
          showScreen('banco');
          bancoMoverAssuntoAbrir();
          document.getElementById('banco-mover-de').value='sE1';
          document.getElementById('banco-mover-para').value='sE2';
          bancoMoverAssuntoExecutar();
          return {
            deRestante: db.acervo.filter(q=>q.subId==='sE1').length,
            paraAgora: db.acervo.filter(q=>q.subId==='sE2').map(q=>q.subName)};}""")
        print('   %s'%r)
        assert r['deRestante']==0 and len(r['paraAgora'])==4 and all(n=='PCR' for n in r['paraAgora'])
        print('   OK\n')

        print('erros de JS: %s'%(real_errors(errs) or 'nenhum'))
        assert not real_errors(errs)
        await b.close()
        print('OK')

asyncio.run(main())
