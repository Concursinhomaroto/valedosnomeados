# -*- coding: utf-8 -*-
# Passo 8.3 do redesenho de Simulados: a tela "Simulado Geral" vira "Treinar" e troca de
# porta de entrada — em vez da árvore de 318 assuntos (que continua existindo, só passa a
# se chamar "montagem avançada"), a entrada organiza pela SUA RELAÇÃO com a questão: nunca
# vista, errou e não revisou, acertou chutando, domina. "Banco de Questões" vira "Acervo".
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from test_acervo import seed, QS

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,seed())
        await page.evaluate("(f)=>{window.QS=eval('('+f+')');window.confirm=()=>true;return true;}",QS)

        print('=== A) abas e menu lateral renomeados ===')
        r=await page.evaluate("""()=>{
          showScreen('simgeral');
          const tabs=[...document.querySelectorAll('#screen-simgeral .rd-conectivos-tabs button')].map(b=>b.textContent.trim());
          return {tabs,sidebar:document.getElementById('nav-simgeral').textContent.trim()};}""")
        print('   abas: %s · sidebar: %r'%(r['tabs'],r['sidebar']))
        assert 'Treinar' in r['tabs'] and 'Acervo' in r['tabs']
        assert 'Simulado Geral' not in r['tabs'] and 'Banco de Questões' not in r['tabs']
        assert 'TREINAR' in r['sidebar']
        print('   OK\n')

        print('=== B) acervo quase vazio: 1 cartão de onboarding, nunca 8 decks mortos ===')
        r=await page.evaluate("""()=>{
          db.acervo=[];db.provas=[];db.provasArquivo=[];
          renderSimGeralScreen();
          return {onboard:!!document.querySelector('#simgeral-content .empty'),
                  decks:!!document.querySelector('.treinar-decks')};}""")
        print('   %s'%r)
        assert r['onboard'] and not r['decks']
        print('   OK\n')

        print('=== C) com acervo de verdade, cada deck conta certo e nenhum número é morto (exceto os 2 que ficam) ===')
        r=await page.evaluate("""()=>{
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',12,'A');
          qs.forEach((q,i)=>{
            q._chaveForte=acervoChave2(q);
            Object.assign(q,acervoCamposNovos('ia'));
            if(i<3){q.vezesRespondida=3;q.acertos=0;q.erros=3;q.dificuldadeAferida='dificil';q.ultimoResultado='X';}
          });
          qs[5].favorita=true; qs[5].vezesRespondida=1; qs[5].acertos=1; qs[5].ultimoResultado='C';
          qs[6].chuteAcertos=2; qs[6].vezesRespondida=2; qs[6].acertos=2; qs[6].ultimoResultado='C';
          db.acervo=qs;
          renderSimGeralScreen();
          const nomes=[...document.querySelectorAll('.treinar-deck-nome')].map(e=>e.textContent);
          const nums={};
          document.querySelectorAll('.treinar-deck').forEach(el=>{
            nums[el.querySelector('.treinar-deck-nome').textContent]=el.querySelector('.treinar-deck-num').textContent;
          });
          return {nomes,nums,total:document.querySelector('.treinar-faixa-total b').textContent};}""")
        print('   decks visíveis: %s'%r['nomes'])
        print('   contagens: %s'%r['nums'])
        assert r['total']=='12'
        assert r['nums']['Feridas abertas']=='3'
        assert r['nums']['Favoritas']=='1'
        assert r['nums']['Acertei chutando']=='1'
        # nenhuma questao favoritada nesta massa alem da qs[5] marcada acima: sem ela, o
        # deck teria de sumir — testado isolado logo abaixo, sem misturar com esta massa
        assert 'Nunca vistas' in r['nomes']
        assert 'Refazer' in r['nomes']   # fica visivel mesmo em 0 — sustenta o loop diario
        print('   OK\n')

        print('=== C.1) deck sem nenhuma questao (Favoritas, sem favorita nenhuma) some da grade ===')
        r=await page.evaluate("""()=>{
          db.acervo.forEach(q=>q.favorita=false);
          renderSimGeralScreen();
          return [...document.querySelectorAll('.treinar-deck-nome')].map(e=>e.textContent);}""")
        print('   decks: %s'%r)
        assert 'Favoritas' not in r
        print('   OK\n')

        print('=== D) clicar Treinar num deck monta a prova e já abre pra responder — 2 cliques ===')
        r=await page.evaluate("""()=>{
          treinarComDeck('feridas');
          const prova=simGeralActive?provaAchar(simGeralActive.provaId):null;
          return {emExame:!!simGeralActive&&!simGeralActive.corrected,
                  qtd:simGeralActive?simGeralActive.questoes.length:0,
                  treino:!!(prova&&prova.treino),
                  refazendo:!!simGeralActive&&simGeralActive.refazendo};}""")
        print('   %s'%r)
        assert r['emExame'] and r['qtd']==3 and r['treino'] and r['refazendo']
        print('   OK\n')

        print('=== D.1) deck GRANDE leva TODAS as questoes — o numero do card e o numero que abre, sem teto escondido ===')
        r=await page.evaluate("""()=>{
          simGeralReset();
          db.acervo=[];db.provas=[];
          const qs=QS('kEnf','Enfermagem','💉','sE1','Choque septico',47,'B');
          qs.forEach(q=>{q._chaveForte=acervoChave2(q);Object.assign(q,acervoCamposNovos('ia'));});
          db.acervo=qs;
          renderSimGeralScreen();
          const cardNum=document.querySelector('.treinar-deck-num').textContent;
          treinarComDeck('nuncavistas');
          return {cardNum,qtdNaProva:simGeralActive.questoes.length};}""")
        print('   card: %s · prova abriu com: %s'%(r['cardNum'],r['qtdNaProva']))
        assert r['cardNum']=='47' and r['qtdNaProva']==47
        print('   OK\n')

        print('=== E) deck inexistente (sem edital em foco) nao quebra ao clicar ===')
        r=await page.evaluate("""()=>{
          simGeralReset();
          treinarComDeck('edital');
          return simGeralActive;}""")
        assert r is None
        print('   OK\n')

        print('=== F) montagem avancada continua existindo, so escondida por padrao ===')
        r=await page.evaluate("""()=>{
          renderSimGeralScreen();
          const escondidaAntes=document.getElementById('treinar-avancado').style.display==='none';
          treinarAbrirAvancado();
          const abriu=document.getElementById('treinar-avancado').style.display!=='none';
          const temArvore=!!document.getElementById('sg-picker');
          treinarAbrirAvancado();
          const fechouDeNovo=document.getElementById('treinar-avancado').style.display==='none';
          return {escondidaAntes,abriu,temArvore,fechouDeNovo};}""")
        print('   %s'%r)
        assert r['escondidaAntes'] and r['abriu'] and r['temArvore'] and r['fechouDeNovo']
        print('   OK\n')

        print('=== G) montar prova sob medida (Banco/Acervo) continua funcionando depois da refatoração ===')
        r=await page.evaluate("""()=>{
          db.provas=[];
          showScreen('banco');
          document.getElementById('montar-modo').value='todas';
          montarAgora();
          return {tela:document.getElementById('screen-provas').classList.contains('active'),
                  provas:db.provas.length,
                  treino:db.provas[0]?db.provas[0].treino:false};}""")
        print('   %s'%r)
        assert r['tela'] and r['provas']>=1 and r['treino']
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
