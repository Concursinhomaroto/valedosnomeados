import asyncio, sys
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, real_errors
from seed_painel import seed

MEDE = """() => {
  const larguraDe=(sel)=>{const e=document.querySelector(sel);
    return e?Math.round(e.getBoundingClientRect().width):null;};
  let vaza=0;
  document.querySelectorAll('#screen-dashboard .stat-card').forEach(c=>{
    const cr=c.getBoundingClientRect();
    c.querySelectorAll('*').forEach(e=>{const r=e.getBoundingClientRect();
      if(r.width>0&&(r.right>cr.right+1||r.left<cr.left-1))vaza++;});
  });
  const nomes=[...document.querySelectorAll('#screen-dashboard .next-step-name')]
    .map(e=>Math.round(e.getBoundingClientRect().width));
  const sem=[...document.querySelectorAll('#screen-dashboard .sem-info > div:first-child')]
    .map(e=>Math.round(e.getBoundingClientRect().width));
  return {vazaDoCartao:vaza, menorNomeFila:nomes.length?Math.min(...nomes):null,
          menorNomeSemana:sem.length?Math.min(...sem):null,
          rolagemLateral:document.documentElement.scrollWidth-window.innerWidth};
}"""

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, seed())
        try:
            casos=[(1080,810,'iPad 9 paisagem'),(810,1080,'iPad 9 retrato'),
                   (1024,768,'iPad antigo'),(1366,1024,'iPad Pro'),(1920,1080,'desktop')]
            for w,h,nome in casos:
                await page.set_viewport_size({'width':w,'height':h})
                await page.evaluate("() => showScreen('dashboard')")
                await page.wait_for_timeout(700)
                r=await page.evaluate(MEDE)
                print(f'{nome} ({w}x{h}): rótulo vazando do cartão={r["vazaDoCartao"]} | '
                      f'menor nome na Fila={r["menorNomeFila"]}px | na Semana={r["menorNomeSemana"]}px | '
                      f'rolagem lateral={r["rolagemLateral"]}px')
                assert r['vazaDoCartao']==0, f'{nome}: rótulo de estatística vazando do cartão'
                assert r['rolagemLateral']<=0, f'{nome}: página rolando pro lado'
                if r['menorNomeFila'] is not None:
                    assert r['menorNomeFila']>=110, \
                        f'{nome}: nome na Fila de hoje espremido em {r["menorNomeFila"]}px (era 36px no iPad)'
                if r['menorNomeSemana'] is not None:
                    assert r['menorNomeSemana']>=110, \
                        f'{nome}: nome em Assuntos da semana espremido em {r["menorNomeSemana"]}px'
            assert not real_errors(errors), real_errors(errors)
            print('\nOK — nome legível na Fila e na Semana, nenhum rótulo colidindo, do iPad ao desktop')
        finally:
            await browser.close()
asyncio.run(main())
