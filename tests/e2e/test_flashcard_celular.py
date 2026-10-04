import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from medir_celular import seed

async def abrir_estudo(page):
    await page.evaluate("() => showScreen('flashcards')")
    await page.wait_for_timeout(600)
    await page.evaluate("() => document.querySelector('.fc-mb-item').click()")
    await page.wait_for_timeout(500)
    await page.evaluate("""() => {const b=[...document.querySelectorAll('button')]
        .find(e=>/^\\s*▶?\\s*Estudar\\s*$/i.test(e.textContent||'')); if(b)b.click();}""")
    await page.wait_for_timeout(700)

MEDE = """() => {
  const est=[...document.querySelectorAll('.screen.active *')].filter(e=>{
    const r=e.getBoundingClientRect(); return r.width>0 && r.right>window.innerWidth+1;}).length;
  const c=document.querySelector('.fc-study-wrap');
  const btns=[...document.querySelectorAll('.screen.active button')]
    .filter(b=>/errei|dif[íi]cil|bom|f[áa]cil|de novo|lembrei/i.test(b.textContent||''));
  const ult=btns.length?btns[btns.length-1].getBoundingClientRect():null;
  const vis=s=>{const e=document.querySelector(s);
    return !!e && getComputedStyle(e).display!=='none';};
  return {estourando:est, cardTopo:c?Math.round(c.getBoundingClientRect().top):null,
          fimBotoes:ult?Math.round(ult.bottom):null, janela:window.innerHeight,
          nBotoes:btns.length, classe:document.body.classList.contains('fc-estudando'),
          listaChefoes:vis('.fc-sidebar-col'), estatisticas:vis('.fc-boss-stats'),
          zonaPdf:vis('.fc-pdf-zone'), flutuantes:vis('.sidebar-bottom-row')};
}"""

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, seed())
        try:
            # ---- 1) celular: nada pode passar da borda ----
            for w,h,nome in [(393,852,'iPhone 15'),(360,800,'Android 360')]:
                await page.set_viewport_size({'width':w,'height':h})
                await page.evaluate("() => showScreen('flashcards')")
                await page.wait_for_timeout(600)
                n=await page.evaluate("""() => [...document.querySelectorAll('.screen.active *')]
                    .filter(e=>{const r=e.getBoundingClientRect();
                      return r.width>0&&r.right>window.innerWidth+1;}).length""")
                print(f'1) {nome}: {n} elementos passando da borda (antes eram dezenas)')
                assert n==0, f'{nome} ainda corta conteúdo'

            # ---- 2) celular, modo estudar: so o cartao ----
            await page.set_viewport_size({'width':393,'height':852})
            await abrir_estudo(page)
            r=await page.evaluate(MEDE)
            print('\n2) celular no modo Estudar:', {k:r[k] for k in
                  ('classe','listaChefoes','estatisticas','zonaPdf','flutuantes')})
            assert r['classe'], 'a classe de foco não foi aplicada'
            assert not r['listaChefoes'], 'a lista de chefões continua ocupando a tela'
            assert not r['estatisticas'] and not r['zonaPdf']
            assert not r['flutuantes'], 'os botões flutuantes continuam por cima do cartão'
            print('   cartão começa em', r['cardTopo'], 'px (antes: 1116)')
            assert r['cardTopo']<400, f"cartão ainda em {r['cardTopo']}px"

            # ---- 3) cartao + botoes de nota cabem sem rolar ----
            await page.evaluate("() => fcStudyFlip()")
            await page.wait_for_timeout(800)
            r=await page.evaluate(MEDE)
            util=r['janela']-72   # descontando a barra de navegação de baixo
            print(f'\n3) botões de nota terminam em {r["fimBotoes"]}px, área útil {util}px')
            assert r['nBotoes']>=4, f'só {r["nBotoes"]} botões de nota'
            assert r['fimBotoes']<=util, 'a nota ficou abaixo da dobra'

            # ---- 4) sair da tela desliga o foco ----
            await page.evaluate("() => showScreen('dashboard')")
            await page.wait_for_timeout(300)
            # rodada 2: no celular os botões redondos não flutuam mais — moram no "Mais"
            fora=await page.evaluate("() => {const v=()=>getComputedStyle(document.querySelector('.sidebar-bottom-row')).display!=='none';"
                                     "const out={classe:document.body.classList.contains('fc-estudando'),soltos:v()};"
                                     "navMaisAlternar(true);out.noMais=v();navMaisAlternar(false);return out;}")
            print('\n4) fora dos flashcards -> classe:',fora['classe'],'| soltos na tela:',fora['soltos'],'| no Mais:',fora['noMais'])
            assert not fora['classe'] and not fora['soltos'] and fora['noMais']

            # ---- 5) desktop nao pode mudar ----
            await page.set_viewport_size({'width':1440,'height':900})
            await abrir_estudo(page)
            d=await page.evaluate(MEDE)
            print('\n5) desktop no modo Estudar -> lista de chefões visível:',d['listaChefoes'],
                  '| estatísticas:',d['estatisticas'],'| flutuantes:',d['flutuantes'])
            assert d['listaChefoes'], 'o desktop perdeu a lista de chefões'
            assert d['estatisticas'], 'o desktop perdeu os cartões de estatística'

            assert not real_errors(errors), real_errors(errors)
            print('\nOK — celular sem corte, foco no cartão ao estudar, desktop intacto')
        finally:
            await browser.close()
asyncio.run(main())
