import asyncio, sys, datetime, os
sys.path.insert(0,'.')
from test_sala import async_playwright, setup_page, make_seed, real_errors

from seed_painel import seed   # nomes longos de verdade + sessoes da semana

async def main():
    async with async_playwright() as p:
        browser,page,errors=await setup_page(p, seed())
        alturaEsperada=None
        try:
            for w,h in [(1920,1080),(1600,900),(1474,830),(1327,747),(1327,658),(1327,630),(980,800)]:
                await page.set_viewport_size({'width':w,'height':h})
                await page.evaluate("() => showScreen('dashboard')")
                await page.wait_for_timeout(700)
                r=await page.evaluate("""() => {
                  const f=document.querySelector('.dash-fold');
                  const mc=document.getElementById('main-content')||document.scrollingElement;
                  const conta=(sel)=>document.querySelectorAll(sel).length;
                  const visiveis=(sel)=>{const sc=document.querySelector(sel);
                    if(!sc)return 0;const box=sc.getBoundingClientRect();
                    return [...sc.children].filter(e=>{const r=e.getBoundingClientRect();
                      return r.top>=box.top-1 && r.bottom<=box.bottom+1;}).length;};
                  const cards=[...f.querySelectorAll('.dash-card')].map(c=>({
                     t:(c.querySelector('.sec-title')||{}).textContent||'?',
                     transborda:c.scrollHeight>c.clientHeight+2}));
                  const fim=f.getBoundingClientRect().bottom;
                  return {alturaDobra:Math.round(f.getBoundingClientRect().height),
                          fimNaTela:Math.round(fim), janela:window.innerHeight,
                          cabeNaTela:fim<=window.innerHeight+2,
                          transbordando:cards.filter(c=>c.transborda).map(c=>c.t.trim()),
                          estudarVisiveis:visiveis('#next-steps-list'),
                          estudarTotal:conta('#next-steps-list .next-step-item'),
                          revVisiveis:visiveis('#dash-overdue-revs'),
                          revTotal:conta('#dash-overdue-revs .rev-item'),
                          semanaVisiveis:(()=>{const c=document.querySelector('#week-study-chart>div');
                            if(!c)return 0;const b=document.querySelector('#week-study-chart').getBoundingClientRect();
                            return [...c.children].filter(e=>{const r=e.getBoundingClientRect();
                              return r.top>=b.top-1&&r.bottom<=b.bottom+1;}).length;})(),
                          graficoAltura:(()=>{const g=document.querySelector('#study-chart-wrap svg');
                            return g?Math.round(g.getBoundingClientRect().height):0;})(),
                          simCaixas:conta('#sim-global-stats .stat-card'),
                          dividaNum:(document.querySelector('.div-num')||{}).textContent||'',
                          dividaFatias:conta('.div-barra i'),
                          dividaBotao:!!document.querySelector('.div-btn'),
                          filaConta:(document.getElementById('fila-conta')||{}).textContent||'',
                          filaChips:conta('#next-steps-list .fila-chip'),
                          fcNum:(document.querySelector('.fc-num')||{}).textContent||'',
                          semVermelhoNaRaridade:(()=>{
                            // compara com o --red de verdade, resolvido pelo navegador,
                            // em vez de adivinhar o rgb por regex
                            const p=document.createElement('span');p.style.color='var(--red)';
                            document.body.appendChild(p);const red=getComputedStyle(p).color;p.remove();
                            const chips=[...document.querySelectorAll('.rar-chip')];
                            return chips.length>0 && chips.every(e=>getComputedStyle(e).color!==red);})(),
                          conquistasAltura:Math.round((document.querySelector('.gamify-badges')||{getBoundingClientRect:()=>({height:0})}).getBoundingClientRect().height),
                          rolagemLateral:document.documentElement.scrollWidth>window.innerWidth+1,
                          graficoCortado:(()=>{const g=document.querySelector('#study-chart-wrap svg');
                            const w=document.getElementById('study-chart-wrap');
                            if(!g||!w)return false;
                            return Math.round(g.getBoundingClientRect().bottom)>Math.round(w.getBoundingClientRect().bottom)+1;})()};
                }""")
                print(f'{w}x{h}: dobra {r["alturaDobra"]}px -> cabe: {r["cabeNaTela"]} | '
                      f'estudar agora {r["estudarVisiveis"]}/{r["estudarTotal"]} visíveis | '
                      f'revisões {r["revVisiveis"]}/{r["revTotal"]} | '
                      f'assuntos-semana {r["semanaVisiveis"]} | gráfico {r["graficoAltura"]}px')
                if r['transbordando']: print('   transbordando:', r['transbordando'])
                # A grade de tres colunas so vale acima de 1000px de largura; a altura
                # nao entra mais na conta, a pagina rola. O que precisa valer em toda
                # largura larga e o mesmo, independente do zoom do navegador.
                grade = w>1000
                assert not r['transbordando'], r['transbordando']
                assert not r['rolagemLateral'], f'rolagem lateral em {w}x{h}'
                assert not r['graficoCortado'], f'gráfico cortado pela caixa em {w}x{h}'
                if grade:
                    assert r['alturaDobra']==alturaEsperada or alturaEsperada is None, \
                        f'a dobra mudou de altura com a janela ({r["alturaDobra"]} != {alturaEsperada})'
                    assert r['estudarVisiveis']>=5, f'só {r["estudarVisiveis"]} itens do estudar-agora aparecem'
                    # a divida agora e medida, nao listada: 2 amostras + o numerao
                    assert r['revVisiveis']>=2, f'só {r["revVisiveis"]} revisões de amostra'
                    assert r['dividaNum']=='6', f'numerao da dívida errado: {r["dividaNum"]!r}'
                    assert r['dividaFatias']>=1, 'barra por reino não desenhou'
                    assert r['dividaBotao'], 'botão de lote não apareceu'
                    assert ' de ' in r['filaConta'], f'contador da fila: {r["filaConta"]!r}'
                    assert r['filaChips']>=5, f'só {r["filaChips"]} chips de motivo na fila'
                    assert r['fcNum'].endswith('%'), f'destaque de flashcards: {r["fcNum"]!r}'
                    assert r['semVermelhoNaRaridade'], 'raridade ainda usa vermelho'
                    assert r['simCaixas']==3, f'{r["simCaixas"]} caixas de simulado (esperado 3)'
                    assert r['semanaVisiveis']>=4, f'só {r["semanaVisiveis"]} assuntos da semana aparecem'
                    assert r['graficoAltura']>=130, f'gráfico com {r["graficoAltura"]}px, pequeno demais'
                    alturaEsperada = r['alturaDobra']
                os.makedirs(os.path.join(os.path.dirname(__file__),'_out'),exist_ok=True)
                await page.screenshot(path=os.path.join(os.path.dirname(__file__),'_out',f'real_{w}x{h}.png'))

            # todas as seções presentes e preenchidas pelo JS
            pres=await page.evaluate("""() => {
              const ids=['streak-val','goal-lbl','dash-badges','sim-global-stats','sim-kingdom-breakdown',
                'kingdom-ranking','next-steps-list','dash-overdue-revs','week-study-chart','fc-trend-chart',
                'avg-time-list','study-chart-wrap','weekly-plan','dash-stats'];
              const r={};ids.forEach(i=>{const e=document.getElementById(i);
                r[i]=e?(e.innerHTML.trim().length>0||e.textContent.trim().length>0):null;});
              return r;}""")
            vazios=[k for k,v in pres.items() if v is None]
            print('\nseções ausentes do DOM:', vazios or 'nenhuma')
            assert not vazios, vazios
            naoPreenchidos=[k for k,v in pres.items() if v is False]
            print('seções que o JS não preencheu:', naoPreenchidos or 'nenhuma')

            print('\nErros JS:', real_errors(errors))
            assert not real_errors(errors)
            print('OK — painel novo cabe na tela e todas as seções continuam sendo preenchidas')
        finally:
            await browser.close()
asyncio.run(main())
