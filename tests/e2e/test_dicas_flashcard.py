# -*- coding: utf-8 -*-
# Dicas -> Flashcards: a revisao de fixacao e a do Flashcard (FSRS, fila, badge), nao um modo
# a parte. Dica ligada a um assunto vira card do chefao (id fixo fcd_<dica>): frente = pergunta
# da dica, verso = conteudo. Cobre os tres tipos, dedup, dica sem assunto, edicao que atualiza o
# card sem zerar o historico, apagar dica apagando o card, o envio em lote pelo filtro e a
# protecao de lista parcial (sem lapide nao apaga card).
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright
from test_aba_dicas import abrir, seed, graves

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        ctx,page,errs=await abrir(browser,seed())
        await page.evaluate("""()=>{
          db.dicas=[
            dicaNormalizar({id:'a',kingdomId:'kPt',subId:'sCrase',titulo:'Crase antes de hora',regra:'Hora leva artigo.',aplicar:'Troque por meio-dia.',
              cuidado:'Desde nao pede.',exemplos:'✔ Das 8h as 12h.\\n✖ Desde as 7h.'},'minha'),
            dicaNormalizar({id:'n',kingdomId:'kEnf',tipo:'numero',subId:'sFrio',titulo:'Faixa',rotulo:'Temperatura da rede de frio',valor:'+2 a +8 °C'},'minha'),
            dicaNormalizar({id:'p',kingdomId:'kPt',tipo:'par',subId:'sPron',titulo:'Mal x Mau',a:'Mal',b:'Mau',diferenca:'Mau e o oposto de bom'},'minha'),
            dicaNormalizar({id:'s',kingdomId:'kPt',titulo:'Sem assunto',regra:'x'},'minha'),
            dicaNormalizar({id:'b',kingdomId:'kPt',topicId:'tP',titulo:'Boss inteiro',regra:'y'},'minha'),
            dicaNormalizar({id:'r',kingdomId:'kPt',subId:'sReg',titulo:'Rascunho',regra:'z',rascunho:true},'ia')];
          showScreen('dicas');renderDicasScreen();}""")

        print('=== A) botao em lote conta so o que pode virar card ===')
        r=await page.evaluate("()=>({btn:(document.querySelector('.dicas-fc-enviar')||{}).textContent,n:dicasFlashElegiveis(dicasAplicarFiltros()).length})")
        print('   %s'%r)
        assert r['n']==4 and '4' in r['btn']        # a, n, p e b — fora a sem assunto e o rascunho
        print('   OK\n')

        print('=== B) mandar pro flashcard cria os cards no chefao certo ===')
        await page.click('.dicas-fc-enviar')
        r=await page.evaluate("""()=>{const f=db.flashcards;const g=id=>f['fcd_'+id];
          return {n:Object.values(f).filter(c=>c.tags==='dica').length,
            a:g('a'),n_:g('n'),p:g('p'),b:g('b'),s:g('s')||null,r:g('r')||null,
            badge:(document.querySelector('.dicas-fc-ir')||{}).textContent};}""")
        a=r['a']
        print('   %s cards · frente "%s"'%(r['n'],a['pergunta']))
        assert r['n']==4 and r['s'] is None and r['r'] is None
        assert a['mbId']=='tP' and a['subId']=='sCrase' and a['subNome']=='Crase' and a['dicaId']=='a'
        assert a['resposta'].startswith('Regra\\nHora leva artigo.'.replace('\\n','\n')) and 'Como aplicar\nTroque' in a['resposta'] and '✔ Das 8h' in a['resposta'] and '✖ Desde' in a['resposta']
        assert r['n_']['pergunta']=='Temperatura da rede de frio' and r['n_']['resposta']=='+2 a +8 °C' and r['n_']['mbId']=='tE'
        assert r['p']['pergunta']=='Mal × Mau\nQual é a diferença?' and r['p']['resposta']=='Mau e o oposto de bom'
        assert r['b']['mbId']=='tP' and 'subId' not in r['b']
        assert a['acertos']==0 and a['erros']==0 and a['ultimaRevisao'] is None
        assert 'Estudar' in r['badge']
        print('   OK\n')

        print('=== C) mandar de novo nao duplica ===')
        r=await page.evaluate("()=>{dicasFlashEnviar();return Object.values(db.flashcards).filter(c=>c.tags==='dica').length}")
        assert r==4
        print('   OK\n')

        print('=== D) editar a dica atualiza o card e preserva o historico ===')
        r=await page.evaluate("""()=>{
          const c=db.flashcards.fcd_a;c.acertos=3;c.erros=1;c.ultimaRevisao='2026-10-30T10:00:00Z';c.sm2={interval:9};
          const d=db.dicas.find(x=>x.id==='a');d.regra='Hora determinada leva artigo: as 14h.';d.editadaEm=new Date().toISOString();
          dicasSalvar(true);
          const n=db.flashcards.fcd_a;
          return {txt:n.resposta,ac:n.acertos,er:n.erros,ult:n.ultimaRevisao,iv:n.sm2&&n.sm2.interval};}""")
        print('   %s'%r)
        assert 'as 14h' in r['txt'] and r['ac']==3 and r['er']==1 and r['ult'] and r['iv']==9
        print('   OK\n')

        print('=== E) mudar o assunto da dica move o card de chefao ===')
        r=await page.evaluate("""()=>{const d=db.dicas.find(x=>x.id==='a');d.subId='sFrio';d.kingdomId='kEnf';dicasSalvar(true);
          const c=db.flashcards.fcd_a;return {mb:c.mbId,sub:c.subId};}""")
        assert r=={'mb':'tE','sub':'sFrio'}, r
        print('   OK\n')

        print('=== F) botao do cartao alterna; dica sem assunto avisa ===')
        r=await page.evaluate("""()=>{
          renderDicasScreen();
          const txt=id=>(document.querySelector('#dica-'+id+' .dica-btn-fc')||{}).textContent;
          const antes=[txt('a'),txt('s')];
          dicaFlashAlternar('s');const t1=__toasts[__toasts.length-1];
          dicaFlashAlternar('a');           // confirm=true: tira do deck
          const sem=!db.flashcards.fcd_a;
          dicaFlashAlternar('a');           // volta
          return {antes,t1,sem,volta:!!db.flashcards.fcd_a};}""")
        print('   %s'%r)
        assert 'No flashcard' in r['antes'][0] and r['antes'][1]=='📇 Flashcard' and 'Ligue a dica' in r['t1'] and r['sem'] and r['volta']
        print('   OK\n')

        print('=== G) apagar a dica apaga o card; lista parcial nao apaga ===')
        r=await page.evaluate("""()=>{
          const antes=!!db.flashcards.fcd_p;
          // lista parcial: a dica some da lista mas SEM lapide (aparelho atrasado) -> card fica
          const guarda=db.dicas.find(x=>x.id==='b');db.dicas=db.dicas.filter(x=>x.id!=='b');dicasSalvar(true);
          const ficou=!!db.flashcards.fcd_b;
          db.dicas.push(guarda);
          dicaApagar('p');
          return {antes,ficou,apagou:!db.flashcards.fcd_p};}""")
        print('   %s'%r)
        assert r['antes'] and r['ficou'] and r['apagou']
        print('   OK\n')

        assert not graves(errs),graves(errs)
        print('erros de JS: nenhum\nOK')
        await browser.close()
asyncio.run(main())
