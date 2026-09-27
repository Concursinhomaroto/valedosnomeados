# -*- coding: utf-8 -*-
# "Montar prova sob medida" era a secao do meio de Minhas Provas, prensada entre colar e
# as provas guardadas. Mas ela le o ACERVO, que e permanente e sobrevive as provas — ou
# seja, deixou de ser um utilitario daquela tela e virou um lugar. Aba propria.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) a aba existe, esta na barra das outras, e e a 4a ===')
        r=await page.evaluate("""()=>{
          const barras=[...document.querySelectorAll('.screen .rd-conectivos-tabs')]
            .filter(t=>t.parentElement.id.startsWith('screen-')&&
                       ['screen-simgeral','screen-provas','screen-caderno','screen-banco','screen-erros']
                         .includes(t.parentElement.id));
          const ordem=[...barras[0].querySelectorAll('button')].map(x=>x.textContent.trim());
          return {telas:barras.map(t=>t.parentElement.id),
                  ordem,
                  todasTem5:barras.every(t=>t.querySelectorAll('button').length===5),
                  cadaUmaTemUmAtivo:barras.every(t=>t.querySelectorAll('button.active').length===1),
                  existeATela:!!document.getElementById('screen-banco'),
                  existeOAlvo:!!document.getElementById('banco-content')};}""")
        print('   abas: %s'%' | '.join(r['ordem']))
        print('   telas com a barra: %s'%len(r['telas']))
        assert r['todasTem5'] and r['cadaUmaTemUmAtivo'], (r['todasTem5'],r['cadaUmaTemUmAtivo'])
        assert r['ordem'][3].endswith('Banco de Questões')
        assert r['existeATela'] and r['existeOAlvo']
        print('   entrou antes do Banco de Erros, nas 5 telas, sem duplicar o "ativo"')
        print('   OK\n')

        print('=== B) a tela vazia explica, em vez de ficar em branco ===')
        r=await page.evaluate("""()=>{
          showScreen('banco');
          const el=document.getElementById('banco-content');
          return {ativa:document.getElementById('screen-banco').classList.contains('active'),
                  vazio:!montarAcervo().length,
                  temTexto:/ainda está vazio/.test(el.innerText),
                  ensina:/Caderno da Banca/.test(el.innerText)&&/Minhas Provas/.test(el.innerText),
                  emBranco:el.innerHTML.trim()===''};}""")
        print('   banco vazio: %s · a tela diz o que fazer: %s · em branco: %s'
              %(r['vazio'],r['temTexto'],r['emBranco']))
        assert r['ativa'] and r['vazio'] and r['temTexto'] and r['ensina'] and not r['emBranco']
        print('   OK\n')

        print('=== C) com questoes, a aba mostra o montar ===')
        r=await page.evaluate("""()=>{
          provaGuardarLote(QS('kEnf','Enfermagem','💉','sE1','Choque septico',30,'A'),
                           {formato:'certoerrado'});
          provaGuardarLote(QS('kPt','Português','📖','sP1','Crase',12,'B'),
                           {formato:'certoerrado'});
          showScreen('banco');
          const el=document.getElementById('banco-content');
          return {titulo:/banco de questões/i.test(el.innerText),
                  modo:!!el.querySelector('#montar-modo'),
                  qtd:!!el.querySelector('#montar-qtd'),
                  botao:/Montar/.test(el.innerText),
                  conta:(el.innerText.match(/(\\d+) questões que você já tem/)||[])[1]};}""")
        print('   título: %s · seletor de modo: %s · campo de itens: %s · botão: %s'
              %(r['titulo'],r['modo'],r['qtd'],r['botao']))
        print('   diz quantas tem: %s'%r['conta'])
        assert r['titulo'] and r['modo'] and r['qtd'] and r['botao'] and r['conta']=='42'
        print('   OK\n')

        print('=== D) saiu de Minhas Provas, e o que era de la continua la ===')
        r=await page.evaluate("""()=>{
          showScreen('provas');
          const el=document.getElementById('provas-content');
          return {temMontar:!!el.querySelector('#montar-modo'),
                  temColar:/Colar/.test(el.innerText)||!!document.getElementById('sg-colar-txt'),
                  temProvas:/Provas guardadas/i.test(el.innerText),
                  temRenomear:!!el.querySelector('.prova-editar')};}""")
        print('   Minhas Provas ainda tem: colar=%s · provas guardadas=%s · renomear=%s'
              %(r['temColar'],r['temProvas'],r['temRenomear']))
        print('   e NÃO tem mais o montar: %s'%(not r['temMontar']))
        assert not r['temMontar'] and r['temColar'] and r['temProvas'] and r['temRenomear']
        print('   OK\n')

        print('=== E) montar dali funciona e leva pra Minhas Provas ===')
        r=await page.evaluate("""()=>{
          showScreen('banco');
          montarSelMat=new Set(['kEnf']);
          const el=document.getElementById('banco-content');
          el.querySelector('#montar-modo').value='materia';
          montarTrocarModo();
          document.getElementById('montar-qtd').value='9';
          const antes=db.provas.length;
          montarAgora();
          return {antes,depois:db.provas.length,
                  itens:db.provas[0].questoes.length,
                  foiPraProvas:document.getElementById('screen-provas').classList.contains('active'),
                  naLista:/Provas guardadas/i.test(document.getElementById('provas-content').innerText)};}""")
        print('   montou de dentro da aba: %s → %s provas, a nova com %s itens'
              %(r['antes'],r['depois'],r['itens']))
        print('   e te levou pra Minhas Provas, onde a prova está: %s'
              %(r['foiPraProvas'] and r['naLista']))
        assert r['depois']==r['antes']+1 and r['itens']==9
        assert r['foiPraProvas'] and r['naLista']
        print('   OK\n')

        print('=== F) navegar entre as 5 abas nao quebra nada ===')
        r=await page.evaluate("""()=>{
          const telas=['simgeral','provas','caderno','banco','erros','banco','provas','banco'];
          const vistos=[];
          telas.forEach(t=>{showScreen(t);
            vistos.push(document.querySelectorAll('.screen.active').length);});
          const el=document.getElementById('banco-content');
          return {sempreUma:vistos.every(n=>n===1),
                  aindaRenderiza:!!el.querySelector('#montar-modo'),
                  menuPai:!!document.getElementById('nav-simgeral')
                          &&document.getElementById('nav-simgeral').classList.contains('active')};}""")
        print('   sempre 1 tela ativa: %s · a aba continua renderizando: %s'
              %(r['sempreUma'],r['aindaRenderiza']))
        print('   o menu lateral segue destacando Simulado Geral: %s'%r['menuPai'])
        assert r['sempreUma'] and r['aindaRenderiza'] and r['menuPai']
        print('   OK\n')

        graves=[e for e in errs if 'selectedPixTier' not in e]
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
