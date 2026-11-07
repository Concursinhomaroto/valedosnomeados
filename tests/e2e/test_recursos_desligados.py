# -*- coding: utf-8 -*-
# Sala de Estudo e Redacao desligadas: somem do menu, as telas nao abrem (voltam pro Painel), nada e apagado e da pra religar.
import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

async def main():
    async with async_playwright() as p:
        b,page,errs=await setup_page(p,make_seed({'studyNickname':'Leo'}))
        # os testes ligam os recursos; aqui o app volta ao padrao (desligado)
        await page.evaluate("()=>{window.__VDN_LIGAR=[];recursosAplicar();return true;}")

        print('=== A) menu: Sala e Redacao somem; o resto continua ===')
        r=await page.evaluate("""()=>{const vis=id=>{const e=document.getElementById(id);return !!e&&getComputedStyle(e).display!=='none';};
          return {sala:vis('nav-sala'),red:vis('nav-redacoes'),painel:vis('nav-dashboard'),agenda:vis('nav-agenda'),treinar:vis('nav-simgeral'),flash:vis('nav-flashcards'),mapa:vis('nav-map'),
            off:[recursoDesligado('sala'),recursoDesligado('redacoes')]};}""")
        print('   ',r)
        assert r['sala'] is False and r['red'] is False and r['painel'] and r['agenda'] and r['treinar'] and r['flash'] and r['mapa'] and r['off']==[True,True]
        print('   OK\n')

        print('=== B) as telas nao abrem: voltam para o Painel (inclusive Banco de Repertorio) ===')
        r=await page.evaluate("""()=>{const out={};
          for(const t of ['sala','redacoes','repertorio']){showScreen(t);out[t]=[...document.querySelectorAll('.screen.active')].map(s=>s.id);}
          showScreen('simgeral');out.simgeral=[...document.querySelectorAll('.screen.active')].map(s=>s.id);return out;}""")
        print('   ',r)
        assert r['sala']==['screen-dashboard'] and r['redacoes']==['screen-dashboard'] and r['repertorio']==['screen-dashboard'] and r['simgeral']==['screen-simgeral']
        print('   OK\n')

        print('=== C) nada foi apagado: as redacoes e os dados continuam no banco ===')
        r=await page.evaluate("""()=>{rdInit();db.redacoes.topics['rdt_x']={id:'rdt_x',name:'Tema guardado'};showScreen('redacoes');return {guardado:!!db.redacoes.topics['rdt_x'],tela:!!document.getElementById('screen-redacoes'),fn:typeof rdRenderTopics};}""")
        print('   ',r); assert r['guardado'] and r['tela'] and r['fn']=='function'
        print('   OK\n')

        print('=== D) religar: pela lista (?ligar=) ou pelo mecanismo de teste ===')
        r=await page.evaluate("""()=>{
          const antes=[recursoDesligado('sala'),recursoDesligado('redacoes')];
          history.replaceState(null,'',location.pathname+'?ligar=sala');
          const soSala=[recursoDesligado('sala'),recursoDesligado('redacoes')];recursosAplicar();
          const navSala=getComputedStyle(document.getElementById('nav-sala')).display!=='none',navRed=getComputedStyle(document.getElementById('nav-redacoes')).display!=='none';
          history.replaceState(null,'',location.pathname+'?ligar=sala,redacoes');const ambos=[recursoDesligado('sala'),recursoDesligado('redacoes')];
          history.replaceState(null,'',location.pathname+'?ligar=%3Cscript%3E');const lixo=[recursoDesligado('sala'),recursoDesligado('redacoes')];
          history.replaceState(null,'',location.pathname);
          window.__VDN_LIGAR=['redacoes'];recursosAplicar();showScreen('redacoes');const abre=document.getElementById('screen-redacoes').classList.contains('active');
          window.__VDN_LIGAR=[];recursosAplicar();showScreen('dashboard');
          return {antes,soSala,navSala,navRed,ambos,lixo,abre};}""")
        print('   ',r)
        assert r['antes']==[True,True] and r['soSala']==[False,True] and r['navSala'] is True and r['navRed'] is False and r['ambos']==[False,False] and r['lixo']==[True,True] and r['abre'] is True
        print('   OK\n')

        print('=== E) celular: o menu Mais tambem nao tem Sala nem Redacao ===')
        await page.set_viewport_size({'width':375,'height':800})
        r=await page.evaluate("""()=>{document.body.classList.add('nav-mais-aberto');const v=id=>getComputedStyle(document.getElementById(id)).display!=='none';
          const out={sala:v('nav-sala'),red:v('nav-redacoes'),flash:v('nav-flashcards'),w:document.documentElement.scrollWidth,iw:innerWidth};document.body.classList.remove('nav-mais-aberto');return out;}""")
        print('   ',r); assert r['sala'] is False and r['red'] is False and r['flash'] and r['w']<=r['iw']+1
        graves=real_errors(errs)
        print('erros de JS: %s'%(graves or 'nenhum'))
        assert not graves,graves
        await b.close()
        print('OK')
asyncio.run(main())
