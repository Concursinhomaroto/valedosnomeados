# -*- coding: utf-8 -*-
# Passo 3 do plano do Banco de Questoes: busca por texto e os filtros que faltam. Reino e
# assunto ja tem porta propria (os modos 'materia'/'assunto' de MONTAR_MODOS) — os
# filtros aqui COMPOEM em cima do pool que o modo escolhido ja produziu. status/favorita/
# tags entram junto com o editor (proximo passo); o motor ja suporta os oito, mas so
# texto/formato/faixa de acerto/nunca respondida tem controle na tela por enquanto.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
from test_acervo import seed, QS

def marca(pr,qs,resultados):
    pr['tentativas']=[{'respostas':[q['correta'] if r=='C' else ('E' if q['correta']=='C' else 'C')
                                     for q,r in zip(qs,resultados)],
                        'acertos':resultados.count('C'),'tempoGastoSec':5}]

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)
        await page.evaluate("()=>{showScreen('provas');return true;}")

        print('=== A) busca por texto acha em <3s (uma chamada, sem digitar tudo) ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=[
            {questao:'Sobre a Lei 8.080/1990, julgue: compete ao SUS a vigilância sanitária.',
             correta:'C',formato:'certoerrado',subId:'sS1',subName:'Lei 8080',
             kingdomId:'kSus',kingdomName:'Saúde Pública',kingdomIcon:'⚕️'},
            {questao:'Sobre o calendário vacinal, julgue: a BCG é aplicada ao nascer.',
             correta:'C',formato:'certoerrado',subId:'sE1',subName:'Choque septico',
             kingdomId:'kEnf',kingdomName:'Enfermagem',kingdomIcon:'💉'}];
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          acervoGuardarProva(provaAchar(id)); db.provas=[];
          document.getElementById('provas-content').innerHTML=montarHTML();
          document.getElementById('banco-filtro-texto').value='vigilancia';
          bancoFiltroMudouTexto(document.getElementById('banco-filtro-texto'));
          const conta=document.getElementById('banco-filtro-conta').innerHTML;
          bancoListaToggle();
          const lista=document.getElementById('banco-filtro-lista').innerHTML;
          return {conta,acheiSUS:lista.includes('SUS')||lista.includes('vigilância'),
                  naoAcheiVacina:!lista.includes('BCG'),
                  focoNoInput:document.activeElement.id==='banco-filtro-texto'};}""")
        print('   contador: %s'%r['conta'])
        assert '1' in r['conta'] and 'encontrada' in r['conta']
        assert r['acheiSUS'] and r['naoAcheiVacina']
        print('   achou "vigilância" digitando "vigilancia" (sem acento) e não trouxe a outra')
        print('   OK\n')

        print('=== B) busca ignora maiúscula/minúscula e acento nos dois lados ===')
        r=await page.evaluate("""()=>{
          document.getElementById('banco-filtro-texto').value='VACINAL';
          bancoFiltroMudouTexto(document.getElementById('banco-filtro-texto'));
          return {conta:document.getElementById('banco-filtro-conta').textContent};}""")
        print('   "VACINAL" (maiúsculo) → %s'%r['conta'])
        assert '1' in r['conta']
        print('   OK\n')

        print('=== C) filtro por formato ===')
        r=await page.evaluate("""()=>{
          document.getElementById('banco-filtro-texto').value='';
          bancoFiltroMudouTexto(document.getElementById('banco-filtro-texto'));
          const qs=[{questao:'Múltipla escolha sobre triagem de Manchester.',correta:'B',
            alternativas:[{letra:'A',texto:'x'},{letra:'B',texto:'y'}],formato:'multipla',
            subId:'sE1',subName:'Choque septico',kingdomId:'kEnf',kingdomName:'Enfermagem',kingdomIcon:'💉'}];
          const id=provaGuardarLote(qs,{formato:'multipla'});
          acervoGuardarProva(provaAchar(id)); db.provas=[];
          bancoFiltroMudouFormato({value:'multipla'});
          const so=document.getElementById('banco-filtro-conta').textContent;
          bancoFiltroMudouFormato({value:'certoerrado'});
          const ce=document.getElementById('banco-filtro-conta').textContent;
          bancoFiltroMudouFormato({value:''});
          const tudo=document.getElementById('banco-filtro-conta').textContent;
          return {so,ce,tudo};}""")
        print('   só múltipla: %s · só certo/errado: %s · qualquer: %s'
              %(r['so'],r['ce'],r['tudo']))
        assert '1' in r['so'] and '2' in r['ce'] and '3' in r['tudo']
        print('   OK\n')

        print('=== D) nunca respondida — le o "respondida" unificado, nao um campo cru ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'R');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          // uma respondida (ainda numa prova VIVA, nunca arquivada — sem vezesRespondida)
          provaAchar(id).tentativas=[{respostas:[qs[0].correta,'',''],acertos:1,tempoGastoSec:5}];
          bancoFiltroMudouNaoRespondida({checked:true});
          const naoResp=document.getElementById('banco-filtro-conta').textContent;
          bancoFiltroMudouNaoRespondida({checked:false});
          return {naoResp};}""")
        print('   3 questões, 1 respondida (numa prova ainda viva) → "nunca respondida": %s'
              %r['naoResp'])
        assert '2' in r['naoResp']
        print('   funciona mesmo sem a questão ter sido arquivada ainda')
        print('   OK\n')

        print('=== E) faixa de acerto exclui quem nunca respondeu (nao confunde 0% com "nunca") ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kSus','Saúde Pública','⚕️','sS1','Lei 8080',3,'F');
          // A: 2 acertos em 2 (100%). B: 1 acerto em 4 (25%). C: nunca respondida.
          [qs[0],qs[0]].forEach(()=>{});
          let id=provaGuardarLote([qs[0]],{formato:'certoerrado'});
          provaAchar(id).tentativas=[{respostas:[qs[0].correta],acertos:1,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id)); db.provas=[];
          id=provaGuardarLote([qs[0]],{formato:'certoerrado'});
          provaAchar(id).tentativas=[{respostas:[qs[0].correta],acertos:1,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id)); db.provas=[];   // qs[0] agora e 2/2 = 100%
          for(let i=0;i<3;i++){
            id=provaGuardarLote([qs[1]],{formato:'certoerrado'});
            provaAchar(id).tentativas=[{respostas:[qs[1].correta==='C'?'E':'C'],acertos:0,tempoGastoSec:5}];
            acervoGuardarProva(provaAchar(id)); db.provas=[];
          }
          id=provaGuardarLote([qs[1]],{formato:'certoerrado'});
          provaAchar(id).tentativas=[{respostas:[qs[1].correta],acertos:1,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id)); db.provas=[];   // qs[1] agora e 1/4 = 25%
          id=provaGuardarLote([qs[2]],{formato:'certoerrado'});  // qs[2] nunca respondida
          acervoGuardarProva(provaAchar(id)); db.provas=[];
          bancoFiltroMudouFaixa('faixaMin',{value:'0'});
          bancoFiltroMudouFaixa('faixaMax',{value:'50'});
          const baixa=document.getElementById('banco-filtro-conta').textContent;
          bancoListaAberta=true; bancoListaRefrescar();
          const html=document.getElementById('banco-filtro-lista').innerHTML;
          bancoFiltroLimpar();
          return {baixa,pegouA:html.includes('F item 0'),pegouB:html.includes('F item 1'),
                  pegouC:html.includes('F item 2')};}""")
        print('   0%%-50%%: %s'%r['baixa'])
        print('   pegou a de 100%%: %s (não devia) · pegou a de 25%%: %s (devia) · pegou a nunca respondida: %s (não devia)'
              %(r['pegouA'],r['pegouB'],r['pegouC']))
        assert '1' in r['baixa'] and not r['pegouA'] and r['pegouB'] and not r['pegouC']
        print('   OK\n')

        print('=== F) filtro compõe com o MODO — nao substitui reino/assunto ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const enf=QS('kEnf','Enfermagem','💉','sE1','Choque septico',2,'CompE');
          const pt=QS('kPt','Português','📖','sP1','Crase',2,'CompP');
          let id=provaGuardarLote(enf,{formato:'certoerrado'});
          provaAchar(id).tentativas=[{respostas:enf.map(q=>q.correta==='C'?'E':'C'),acertos:0,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id)); db.provas=[];
          id=provaGuardarLote(pt,{formato:'certoerrado'});
          provaAchar(id).tentativas=[{respostas:pt.map(q=>q.correta==='C'?'E':'C'),acertos:0,tempoGastoSec:5}];
          acervoGuardarProva(provaAchar(id)); db.provas=[];
          document.getElementById('provas-content').innerHTML=montarHTML();
          document.getElementById('montar-modo').value='materia';
          montarSelMat=new Set(['kEnf']);
          document.getElementById('banco-filtro-texto').value='CompE';
          bancoFiltroMudouTexto(document.getElementById('banco-filtro-texto'));
          const soEnfETexto=document.getElementById('banco-filtro-conta').textContent;
          document.getElementById('banco-filtro-texto').value='CompP';   // e do Português
          bancoFiltroMudouTexto(document.getElementById('banco-filtro-texto'));
          const materiaErradaTexto=document.getElementById('banco-filtro-conta').textContent;
          return {soEnfETexto,materiaErradaTexto};}""")
        print('   modo=matéria(Enfermagem) + texto="CompE": %s'%r['soEnfETexto'])
        print('   modo=matéria(Enfermagem) + texto="CompP" (é de Português): %s'%r['materiaErradaTexto'])
        assert '2' in r['soEnfETexto']
        assert 'nenhuma' in r['materiaErradaTexto']
        print('   o filtro de texto não vaza pra fora do que o modo já restringiu')
        print('   OK\n')

        print('=== G) "Montar" respeita o filtro ativo, não só o modo ===')
        r=await page.evaluate("""()=>{
          document.getElementById('banco-filtro-texto').value='CompE';
          bancoFiltroMudouTexto(document.getElementById('banco-filtro-texto'));
          document.getElementById('montar-qtd').value='10';
          const antes=db.provas.length;
          montarAgora();
          const nova=db.provas[0];
          return {antes,depois:db.provas.length,itens:nova.questoes.length,
                  soCompE:nova.questoes.every(q=>q.questao.includes('CompE'))};}""")
        print('   montou com %s itens, todos batendo o texto filtrado: %s'
              %(r['itens'],r['soCompE']))
        assert r['depois']==r['antes']+1 and r['itens']==2 and r['soCompE']
        print('   OK\n')

        print('=== H) limpar filtro zera tudo, inclusive na tela ===')
        r=await page.evaluate("""()=>{
          bancoFiltroLimpar();
          const el=document.getElementById('banco-filtro-texto');
          renderSimGeralScreen();
          const novoEl=document.querySelector('#banco-filtro-texto');
          return {vazio:!bancoFiltroTemAlgo(), inputVazio:novoEl?novoEl.value==='':null};}""")
        print('   filtro ativo depois de limpar: %s · campo de texto na tela: vazio=%s'
              %(not r['vazio'],r['inputVazio']))
        assert r['vazio'] and r['inputVazio']
        print('   OK\n')

        print('=== I) motor suporta status/favorita/tags mesmo sem UI ainda (usado no proximo passo) ===')
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',3,'T');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          acervoGuardarProva(provaAchar(id));
          db.acervo[0].favorita=true;
          db.acervo[1].status='revisar';
          db.acervo[2].tags=['direito-administrativo'];
          const pool=montarAcervo();
          const fav=bancoAplicarFiltros(pool,{...bancoFiltro,favorita:true});
          const rev=bancoAplicarFiltros(pool,{...bancoFiltro,status:'revisar'});
          const tag=bancoAplicarFiltros(pool,{...bancoFiltro,tags:new Set(['direito-administrativo'])});
          return {fav:fav.length,rev:rev.length,tag:tag.length,
                  existentes:bancoTagsExistentes(),
                  poolLen:pool.length,
                  q0:{fav:db.acervo[0].favorita,st:db.acervo[0].status},
                  q1:{fav:db.acervo[1].favorita,st:db.acervo[1].status},
                  q2:{fav:db.acervo[2].favorita,st:db.acervo[2].status,tags:db.acervo[2].tags}};}""")
        print('   favorita=%s (esperado 1) · status=revisar=%s (esperado 1) · tag=%s (esperado 1)'
              %(r['fav'],r['rev'],r['tag']))
        print('   pool: %s · q0=%s q1=%s q2=%s'%(r['poolLen'],r['q0'],r['q1'],r['q2']))
        assert r['fav']==1 and r['rev']==1 and r['tag']==1
        assert r['existentes']==['direito-administrativo']
        print('   OK\n')

        print('=== J) favorita/status/tags nao somem quando a MESMA questao volta numa prova viva ===')
        # O bug de verdade: a questao ja tinha entrada no acervo (favoritada), e a MESMA
        # questao aparece de novo numa prova NOVA que ainda nem foi arquivada. Sem o
        # ajuste, a copia da prova viva (sem favorita/tags) tapava a do acervo.
        r=await page.evaluate("""()=>{
          db.acervo=[]; db.provas=[]; db.provasArquivo=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',1,'V');
          const id=provaGuardarLote(qs,{formato:'certoerrado'});
          acervoGuardarProva(provaAchar(id));   // primeira ocorrencia: vai pro acervo
          db.acervo[0].favorita=true;
          db.acervo[0].tags=['revisar-na-vespera'];
          // a MESMA questao aparece de novo, numa prova nova, AINDA NA LISTA (nao arquivada)
          const id2=provaGuardarLote(qs,{formato:'certoerrado'});
          const pool=montarAcervo();
          const achada=pool.find(x=>x.q.questao===qs[0].questao);
          const fav=bancoAplicarFiltros(pool,{...bancoFiltro,favorita:true});
          return {favoritaVisivel:achada&&achada.q.favorita,
                  tagsVisiveis:achada&&achada.q.tags,
                  filtroAcha:fav.length,
                  aindaTemProvaViva:db.provas.some(p=>p.id===id2)};}""")
        print('   prova nova (não arquivada) com a mesma questão · favorita visível: %s'
              %r['favoritaVisivel'])
        print('   tags visíveis: %s · filtro por favorita encontra: %s'
              %(r['tagsVisiveis'],r['filtroAcha']))
        assert r['favoritaVisivel'] and r['tagsVisiveis']==['revisar-na-vespera']
        assert r['filtroAcha']==1 and r['aindaTemProvaViva']
        print('   a marcação do acervo aparece mesmo com a questão ainda numa prova viva')
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
