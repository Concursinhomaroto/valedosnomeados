# -*- coding: utf-8 -*-
# Redesign, fase A2 (menu lateral): os botoes mudaram de grupo e o Admin foi pro rodape,
# mas cada um continua com o mesmo id e o mesmo clique. No celular a barra de baixo tem
# 5 fixos e "Mais" mostra os outros 5 — nenhuma tela ficou sem caminho.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

TELAS = {'nav-dashboard':'dashboard','nav-revisions':'revisions','nav-simgeral':'simgeral',
         'nav-map':'map','nav-sala':'sala','nav-flashcards':'flashcards',
         'nav-editais':'editais','nav-conquistas':'conquistas','nav-redacoes':'redacoes'}

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,make_seed({'studyNickname':'Leo'}))

        print('=== A) grupos na ordem nova: Hoje / Estudar / Acompanhar ===')
        r=await page.evaluate("""()=>[...document.querySelectorAll('#nav-principal > *')]
          .filter(e=>getComputedStyle(e).display!=='none').map(e=>e.classList.contains('nav-group')?'#'+e.textContent.trim():e.id)""")
        print('   %s'%r)
        assert r==['#Hoje','nav-dashboard','nav-revisions','nav-simgeral','#Estudar','nav-map','nav-sala',
                   'nav-flashcards','#Acompanhar','nav-editais','nav-conquistas','nav-redacoes'], r
        print('   OK\n')

        print('=== B) cada botao abre a tela dele e fica marcado como ativo ===')
        for bid,tela in TELAS.items():
            r=await page.evaluate("""([bid,tela])=>{document.getElementById(bid).click();
              return {tela:document.getElementById('screen-'+tela).classList.contains('active'),
                      ativo:document.getElementById(bid).classList.contains('active'),
                      ativos:document.querySelectorAll('.nav-btn.active').length};}""",[bid,tela])
            assert r['tela'] and r['ativo'] and r['ativos']==1, (bid,r)
        await page.evaluate("()=>showScreen('dashboard')")
        print('   9 telas OK\n')

        print('=== C) Admin no rodape: escondido pra quem nao e admin, mesmo clique pra quem e ===')
        r=await page.evaluate("""()=>{const a=document.getElementById('nav-admin');
          const out={noRodape:!!a.closest('.sidebar-bottom-row'),visivel:getComputedStyle(a).display!=='none',admin:isAdmin()};
          if(out.visivel){a.click();out.abriu=document.getElementById('screen-admin').classList.contains('active');showScreen('dashboard');}
          return out;}""")
        print('   %s'%r)
        assert r['noRodape'] and r['visivel']==r['admin']
        if r['visivel']: assert r['abriu'], 'clique do Admin no rodape tem que abrir a tela'
        print('   OK\n')

        print('=== D) rodape com rotulo visivel e aria-label em cada botao ===')
        r=await page.evaluate("""()=>[...document.querySelectorAll('.sidebar-bottom-row > button')]
          .filter(e=>getComputedStyle(e).display!=='none')
          .map(e=>({id:e.id,rotulo:getComputedStyle(e,'::after').content,aria:e.getAttribute('aria-label')}))""")
        for x in r: print('   %s'%x)
        assert len(r)>=3 and all(x['rotulo'] not in ('none','normal','""') and x['aria'] for x in r)
        print('   OK\n')

        print('=== E) selo de Revisoes vermelho (atrasado), Treinar/Editais laranja (pendente) ===')
        r=await page.evaluate("""()=>{const c=id=>{const e=document.getElementById(id);e.style.display='inline';
            const v=getComputedStyle(e).backgroundColor;e.style.display='none';return v;};
          return {rev:c('rev-badge'),erros:c('erros-badge'),editais:c('editais-badge')};}""")
        print('   %s'%r)
        assert r['rev']=='rgb(220, 38, 38)' and r['erros']=='rgb(194, 65, 12)' and r['editais']=='rgb(194, 65, 12)'
        print('   OK\n')

        print('=== F) texto do menu nao corta mais ("MAPA DOS REIN...") ===')
        r=await page.evaluate("""()=>[...document.querySelectorAll('#nav-principal .nav-label')]
          .filter(e=>e.offsetWidth&&e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)""")
        print('   cortados: %s'%r)
        assert not r
        print('   OK\n')

        print('=== G) celular: 5 fixos; "Mais" abre os outros 5 e fecha depois de escolher ===')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_timeout(200)
        vis="""()=>[...document.querySelectorAll('#nav-principal .nav-btn')]
            .filter(e=>getComputedStyle(e).display!=='none').map(e=>e.id)"""
        fechado=await page.evaluate(vis)
        print('   fechado: %s'%fechado)
        assert fechado==['nav-dashboard','nav-revisions','nav-simgeral','nav-map','nav-mais'], fechado
        await page.click('#nav-mais')
        aberto=await page.evaluate(vis)
        print('   aberto: %s'%aberto)
        assert len(aberto)==10 and set(TELAS)<=set(aberto)
        assert await page.evaluate("()=>document.getElementById('nav-mais').getAttribute('aria-expanded')")=='true'
        await page.click('#nav-flashcards')
        r=await page.evaluate("""()=>({tela:document.getElementById('screen-flashcards').classList.contains('active'),
          fechou:!document.body.classList.contains('nav-mais-aberto')})""")
        print('   escolheu Flashcards: %s'%r)
        assert r['tela'] and r['fechou']
        r=await page.evaluate("()=>document.documentElement.scrollWidth-window.innerWidth")
        assert r<=0, 'rolagem lateral no celular: %s'%r
        await page.evaluate("()=>showScreen('dashboard')")
        await page.set_viewport_size({'width':1200,'height':900})
        print('   OK\n')

        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves, graves
        await b.close()
        print('OK')

asyncio.run(main())
